"""Context correctness across cache, source revisions, decisions and public boundaries."""
import copy
import hashlib
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from harness.context_manager import (
    ContextBudgetError,
    ContextManager,
    DecisionConflict,
    SourceCache,
    rebuild_decisions,
)
from harness.contracts import ContextPolicy, DecisionRecord, StoryRequest
from harness.conversation import ConversationEngine
from harness.conversation_webapp import create_conversation_app
from harness.models import ModelClient
from harness.prompt_contracts import PromptContracts, validate_output, validate_request
from harness.repo_context import RepoContext, contextual_answer
from harness.skills import digest
from pydantic import ValidationError
from test_conversation import make_engine


def setup_manager(tmp_path, *, policy=None, messages=None, **kwargs):
    from harness.contracts import ClientProfile
    profile = ClientProfile(repository='example/client', base_branch='develop', openspec_root='openspec')
    identity = {'run_id': 'a' * 32, 'attempt_id': 'b' * 32, 'repository': profile.repository,
                    'profile_sha256': 'c' * 64, 'base_sha': 'd' * 40, 'revision': 0, 'stage': 'exploring', 'checkpoint_id': None}
    manager = ContextManager(tmp_path, profile, policy or ContextPolicy(enabled=True), identity,
                             messages or [], **kwargs)
    return manager, profile


@pytest.mark.parametrize('values', [{'max_input_tokens': 1024, 'output_reserve_tokens': 1024},
    {'cache_ttl_seconds': 0}, {'enabled': 'yes'}, {'compactor': True}, {'max_prompt_bytes': 2}])
def test_invalid_policy(values):
    with pytest.raises(ValidationError):
        ContextPolicy(**values)


def test_policy_is_frozen_and_defaults_disabled():
    from harness.context_manager import load_context_policy
    assert not load_context_policy().enabled
    with pytest.raises(ValidationError):
        ContextPolicy().enabled = True


@pytest.mark.parametrize('tool_request', [{'op': 'shell'}, {'op': 'read_file', 'path': '../secret'},
    {'op': 'read_file', 'path': 'a', 'unused': True}, {'op': 'search_text', 'query': 2}, {'op': 'list_tree', 'path': 'src'}])
def test_invalid_tool_contract(tool_request):
    with pytest.raises(ValueError):
        validate_request(tool_request)


def test_catalog_roles_phases_and_stable_hashes():
    catalog = PromptContracts()
    assert catalog.sha256 == PromptContracts().sha256
    for role, phase in [('explorer', 'explore'), ('planner', 'propose'), ('planner', 'update'),
                        ('developer', 'apply'), ('openspec_verifier', 'verify'), ('verifier', 'verify')]:
        system, ref = catalog.compose(role, phase)
        assert role in system and ref['prompt_sha256'] == digest(system)
        assert 'No ejecutes shell' in system
    with pytest.raises(ValueError):
        catalog.compose('context_compactor', 'verify')
    with pytest.raises(ValueError):
        catalog.compose('developer', 'explore')


def test_cache_ttl_lru_bytes_and_integrity():
    now = [0]
    cache = SourceCache(ContextPolicy(cache_max_entries=1, cache_max_bytes=1024, cache_ttl_seconds=1), lambda: now[0])
    cache.put('a', {'content': 'ok'})
    assert cache.get('a')['content'] == 'ok'
    cache.entries['a'][3]['content'] = 'corrupt'
    assert cache.get('a') is None
    cache.put('a', {'content': 'ok'})
    cache.put('b', {'content': 'other'})
    assert cache.get('a') is None
    now[0] = 2
    assert cache.get('b') is None
    cache.put('large', {'content': 'x' * 2000})
    cache.put('truncated', {'truncated': True})
    assert not cache.entries


def test_cache_source_candidate_inventory_and_revoked_access(tmp_path):
    manager, profile = setup_manager(tmp_path)
    target = tmp_path / 'file.txt'
    target.write_text('old')
    context = RepoContext(tmp_path, profile, cache=manager.cache, identity=manager.identity)
    read = {'op': 'read_file', 'path': 'file.txt'}
    assert context.request(read)['content'] == context.request(read)['content'] == 'old'
    assert manager.cache.metrics['hits'] == 1
    target.write_text('new')
    assert context.request(read)['content'] == 'new'
    assert manager.cache.metrics['invalidations'] == 1
    search = {'op': 'search_text', 'query': 'new'}
    assert len(context.request(search)['matches']) == 1
    (tmp_path / 'second.txt').write_text('new')
    assert len(context.request(search)['matches']) == 2
    target.unlink()
    assert len(context.request(search)['matches']) == 1
    profile.repository_policy.denied_paths.append('second.txt')
    with pytest.raises(ValueError):
        context.request({'op': 'read_file', 'path': 'second.txt'})
    assert context.request(search)['matches'] == []
    other = RepoContext(tmp_path, profile, cache=manager.cache, identity={**manager.identity, 'repository': 'other/client'})
    before = manager.cache.metrics['misses']
    other.request({'op': 'list_tree'})
    assert manager.cache.metrics['misses'] == before + 1


def test_decisions_do_not_expire_and_preserve_ambiguous_original(tmp_path):
    messages = [{'kind': 'clarification', 'actor': 'human', 'text': 'Cero está permitido en compras. Negativos rechazados.', 'at': 'old'},
                {'kind': 'clarification', 'actor': 'human', 'text': 'Quizás algo diferente en otro caso.'}]
    manager, _ = setup_manager(tmp_path, messages=messages)
    payload, _, _ = manager.prepare('explorer', 'explore', {}, [], None)
    records = json.loads(payload)['confirmed_decisions']
    assert [r['text'] for r in records] == [m['text'] for m in messages]
    assert all(r['status'] == 'confirmed' for r in records)
    assert manager.questions == []
    assert manager.memory_snapshot()['decisions'] == records
    for r in records:
        DecisionRecord.model_validate(r)
    with pytest.raises(ValueError):
        manager.verify_view(records[:1])
    tampered = copy.deepcopy(records)
    tampered[0]['evidence_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        manager.verify_view(tampered)
    manager.decisions[0]['text'] = 'Altered without changing the original hash'
    with pytest.raises(ValueError, match='alterado'):
        manager._memory()


def test_conflict_explicit_replacement_and_fact_staleness(tmp_path):
    messages = [{'kind': 'clarification', 'actor': 'human', 'text': 'Cero permitido en compras.'},
                {'kind': 'clarification', 'actor': 'human', 'text': 'Cero rechazado en compras.'}]
    manager, _ = setup_manager(tmp_path, messages=messages)
    with pytest.raises(DecisionConflict):
        manager.prepare('developer', 'apply', {}, [], None)
    messages.append({'kind': 'clarification', 'actor': 'human', 'text': 'Corrijo: cero permitido en compras ahora.'})
    fixed, _ = setup_manager(tmp_path, messages=messages)
    assert len(fixed._memory()) == 1
    assert sum(r['status'] == 'superseded' for r in fixed.decisions) == 2
    target = tmp_path / 'rule.txt'
    target.write_text('Cero permitido en compras.')
    fixed.observe_fact('rule.txt', target.read_text(), hashlib.sha256(target.read_bytes()).hexdigest())
    assert fixed._memory()[-1]['kind'] == 'fact'
    target.write_text('Cero rechazado en compras.')
    assert all(r['kind'] != 'fact' for r in fixed._memory())
    assert fixed.decisions[-1]['status'] == 'stale'
    fixed.observe_fact('rule.txt', target.read_text(), hashlib.sha256(target.read_bytes()).hexdigest())
    with pytest.raises(DecisionConflict):
        fixed._memory()  # A recent repository note does not supersede an authorized rule.


def test_model_interpretation_never_confirms(tmp_path):
    manager, _ = setup_manager(tmp_path)
    data = DecisionRecord(id='proposed', kind='interpretation', text='assumption', scope='hu',
        run_id='a' * 32, attempt_id='b' * 32, revision=0, origin_ref='model:call',
        evidence_sha256='0' * 64, status='proposed').model_dump()
    assert rebuild_decisions([], manager.identity, [data])[0]['status'] == 'proposed'
    manager.decisions = [data]
    assert manager._memory() == []


def test_budget_includes_system_and_never_compacts(tmp_path):
    manager, _ = setup_manager(tmp_path, policy=ContextPolicy(enabled=True, max_prompt_bytes=1024))
    with pytest.raises(ContextBudgetError):
        manager.prepare('explorer', 'explore', {'source': 'x' * 900}, [], None)
    assert manager.last_envelope['envelope']['selection']['bytes_after'] > 1024


def test_dedup_refresh_and_forty_rounds(tmp_path):
    manager, profile = setup_manager(tmp_path)
    (tmp_path / 'f.txt').write_text('required bytes')
    context = RepoContext(tmp_path, profile, cache=manager.cache, identity=manager.identity)
    request = {'op': 'read_file', 'path': 'f.txt'}
    result = context.request(request)
    history = [{'request': request, 'result': result, 'fingerprint': context.fingerprint(request)}] * 40
    payload, _, metadata = manager.prepare('developer', 'apply', {'approved_manifest': ['f.txt']}, history, context)
    assert len(json.loads(payload)['context_history']) == 1
    assert len(metadata['selection']['excluded']) == 39
    assert metadata['selection']['bytes_after'] < metadata['selection']['bytes_before']
    (tmp_path / 'f.txt').write_text('candidate bytes')
    payload, _, metadata = manager.prepare('developer', 'apply', {}, history[:1], context)
    assert json.loads(payload)['context_history'][0]['result']['content'] == 'candidate bytes'
    assert metadata['selection']['excluded'][0]['reason'] == 'source_changed'


def test_real_model_calls_have_trusted_system_usage_and_protected_snapshot(tmp_path):
    snapshots, events, bodies = [], [], []
    manager, _profile = setup_manager(tmp_path, on_snapshot=lambda data: snapshots.append(data) or digest(data),
                                     on_event=events.append)
    class API:
        def do(self, *_args, body):
            bodies.append(body)
            return {'choices': [{'message': {'content': json.dumps({'approved': False, 'findings': []})}}]}
    model = ModelClient(API(), {'verifier': 'haiku'}, {'haiku': (Decimal(1), Decimal(1))})
    value = contextual_answer(model, 'verifier', {'test_evidence': {'passed': True}}, context_manager=manager, phase='verify')
    assert value['approved'] is False
    assert 'ROLE: verifier' in bodies[0]['messages'][0]['content']
    assert model.calls[0].context_provenance['catalog_sha256'] == manager.prompts.sha256
    assert model.calls[0].cost_usd is None
    assert len(model.calls) == len(events) == len(snapshots) == 1
    assert snapshots[0]['payload']['test_evidence']['passed']


def test_invalid_output_and_no_tool_for_advisor(tmp_path):
    manager, profile = setup_manager(tmp_path)
    with pytest.raises(ValueError):
        validate_output('explorer', {'summary': 'ok', 'questions': [2]}, {}, profile)
    with pytest.raises(ValueError):
        validate_output('openspec_verifier', {'approved': 'true', 'findings': []}, {}, profile)
    class Model:
        def complete(self, *args, **kwargs):
            return type('Reply', (), {'text': '{"context_request":{"op":"list_tree"}}'})()
    with pytest.raises(ValueError):
        contextual_answer(Model(), 'verifier', {}, context_manager=manager, phase='verify')


def enabled_engine(tmp_path):
    engine, github, models, store, coord, profile = make_engine(tmp_path)
    engine.context_policy = ContextPolicy(enabled=True)
    return engine, github, models, store, coord, profile


def test_enabled_flow_restart_corruption_and_public_api(tmp_path):
    engine, github, models, store, coord, profile = enabled_engine(tmp_path)
    engine.publication_mode = 'approved_plan'
    run = engine.submit(StoryRequest(hu='HU-ctx', description='VALUE a 2'), actor='human')
    engine.advance(run)
    engine.act(run, 'answer', actor='human', text='Salida 2', expected_revision=0, key='answer')
    pending = engine.get(run)['attempts'][-1]
    memory_ref = pending['context']['memory_sha256']
    store._write_checkpoint_file(f'context/{run}/{pending["attempt_id"]}/{memory_ref}.json', b'corrupt')
    restarted = ConversationEngine(profile, store, coord, lambda: github, lambda *_: models,
                                   engine.cli, engine.test_runner, context_policy=engine.context_policy)
    assert restarted.get(run)['state'] == 'awaiting_plan_review'
    with TestClient(create_conversation_app(restarted, profile)) as client:
        assert client.get(f'/runs/{run}', headers={'x-forwarded-user': 'other'}).status_code == 403
        body = client.get(f'/runs/{run}', headers={'x-forwarded-user': 'human'}).json()
        assert 'confirmed_decisions' not in body['attempts'][-1]['context']
        assert 'contracts' not in body['attempts'][-1]['context']
    restarted.act(run, 'approve', actor='human', expected_revision=pending['revision'],
                  expected_hash=pending['context']['plan_hash'], key='approve')
    completed = restarted.get(run)['attempts'][-1]
    assert completed['stage'] == 'complete' and len(github.published) == 1
    assert any(e['kind'] == 'context_rebuilt' for e in completed['timeline'])
    assert all('context_provenance' in kwargs for _, _, kwargs in models.prompts)
    assert all('compactor' not in role for role, _ in models.calls)
    assert completed['approvals'][0]['sha256'] == pending['context']['plan_hash']


def test_policy_change_blocks_actions_retry_does_not_inherit_approval(tmp_path):
    engine, github, models, store, coord, profile = enabled_engine(tmp_path)
    run = engine.submit(StoryRequest(hu='HU', description='VALUE a 2'), actor='human')
    engine.advance(run)
    old = engine.get(run)['attempts'][-1]
    old['approvals'].append({'kind': 'plan', 'revision': 1, 'sha256': 'e' * 64, 'actor': 'human', 'at': '2026-10-02T00:00:00Z'})
    record = store.load(run)
    record['attempts'][-1] = old
    store.save(run, record)
    changed = ConversationEngine(profile, store, coord, lambda: github, lambda *_: models,
        engine.cli, engine.test_runner, context_policy=ContextPolicy(enabled=True, cache_max_entries=2))
    with pytest.raises(ValueError, match='incompatibles'):
        changed.act(run, 'answer', actor='human', expected_revision=0, text='Salida 2', key='answer')
    changed.retry_legacy(run)
    new = changed.get(run)['attempts'][-1]
    assert new['attempt_id'] != old['attempt_id'] and new['approvals'] == []
    assert new['context']['context_management'] == changed._context_settings()


def test_legacy_does_not_get_fabricated_management(tmp_path):
    engine, *_ = make_engine(tmp_path)
    run = engine.submit(StoryRequest(hu='HU', description='VALUE a 2'), actor='human')
    assert 'context_management' not in engine.get(run)['attempts'][-1]['context']


def test_context_snapshot_integrity_is_independent_of_checkpoint_commit(tmp_path):
    from harness.store import LocalRunStore
    store = LocalRunStore(tmp_path)
    data = {'decisions': [], 'questions': ['original']}
    ref = store.save_context_snapshot('a' * 32, 'b' * 32, data)
    assert store.load_context_snapshot('a' * 32, 'b' * 32, ref) == data
    checkpoint = store.save_checkpoint('a' * 32, 'b' * 32, 1, 'c' * 40, {}, metadata={'memory_ref': ref})
    store.save_context_snapshot('a' * 32, 'b' * 32, {'questions': ['uncommitted']})
    assert store.load_checkpoint('a' * 32, 'b' * 32, checkpoint)['metadata']['memory_ref'] == ref
