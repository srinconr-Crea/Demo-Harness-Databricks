"""Local approved-plan workflows with typed findings and real Git checkpoints."""
import hashlib
import json

import pytest

from harness.contracts import StoryRequest
from harness.conversation import ConversationEngine
from harness.failure_routing import WORKFLOW_VERSION
from test_conversation import FakeModels, git, make_engine


def finding(category='implementation', code='wrong_value', evidence='Synthetic assertion VALUE != expected'):
    return {'category': category, 'code': code, 'criterion': 'Salida', 'evidence': evidence,
            'paths': ['src/value.py'], 'operations': ['modify'], 'recommendation': 'Revisar salida aprobada'}


class RepairModels(FakeModels):
    def __init__(self, *, semantic=None, noop=False, fail_correction=False):
        super().__init__()
        self.semantic = list(semantic or [])
        self.noop = noop
        self.fail_correction = fail_correction
        self.developer_count = 0

    def complete(self, role, prompt, **kwargs):
        response = super().complete(role, prompt, **kwargs)
        payload = json.loads(prompt)
        if role == 'developer':
            self.developer_count += 1
            if kwargs.get('stage') == 'correcting' and self.fail_correction:
                self.fail_correction = False
                raise RuntimeError('Synthetic transient developer transport failure')
            sources = payload.get('evidence_bundle', {}).get('current_sources', [])
            source = next((s for s in sources if s['path'] == 'src/value.py'), None)
            if source:
                if self.noop and kwargs.get('stage') == 'correcting':
                    value = {'operations': [], 'coverage': [{'path': 'src/value.py',
                             'status': 'already_conformant', 'sha256': source['sha256']}], 'notes': 'Bytes vigentes conformes'}
                else:
                    value = {'operations': [{'op': 'modify', 'path': 'src/value.py',
                             'content': f'VALUE = {self.developer_count + 1}\n', 'expected_sha256': source['sha256']}],
                             'coverage': [{'path': 'src/value.py', 'status': 'applied'}], 'notes': 'Reparación acotada'}
                response.text = json.dumps(value)
        if role == 'openspec_verifier' and self.semantic:
            response.text = json.dumps({'approved': False, 'findings': self.semantic.pop(0)})
        return response


def prepare(tmp_path, models=None, *, managed=False):
    engine, github, _, store, coordinator, profile = make_engine(tmp_path)
    engine.publication_mode = 'approved_plan'
    engine.context_policy = engine.context_policy.model_copy(update={'enabled': managed})
    models = models or RepairModels()
    engine.models_factory = lambda *_: models
    run_id = engine.submit(StoryRequest(hu='HU-CLASSIFIED', description='Cambiar salida aprobada'), actor='ana@example.com')
    assert store.load(run_id)['attempts'][-1]['context']['workflow_version'] == WORKFLOW_VERSION
    engine.advance(run_id)
    engine.act(run_id, 'answer', actor='ana@example.com', text='Salida nueva', expected_revision=0, key='answer')
    plan = store.load(run_id)['attempts'][-1]
    assert plan['stage'] == 'awaiting_plan_review'
    return engine, github, models, store, coordinator, profile, run_id, plan


def approve(prepared):
    engine, _, _, _, _, _, run_id, plan = prepared
    return engine.act(run_id, 'approve', actor='ana@example.com', expected_revision=plan['revision'],
                      expected_hash=plan['context']['plan_hash'], key='approve-plan')


@pytest.mark.parametrize('managed', [False, True])
def test_technical_failure_repairs_without_replanning_and_publishes(tmp_path, managed):
    prepared = prepare(tmp_path, managed=managed)
    engine, github, models, store, _, _, run_id, plan = prepared
    observed = []

    def runner(root, profile, paths, record, attempt):
        observed.append((root.joinpath('src/value.py').read_bytes(), list(paths), attempt['revision']))
        return {'passed': len(observed) > 1, 'evidence': ['Synthetic real byte assertion'],
                **({'findings': [finding()]} if len(observed) == 1 else {})}

    engine.test_runner = runner
    approve(prepared)
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['revision'] == plan['revision']
    assert final['context']['implementation_correction_count'] == 1
    assert final['context']['candidate_revision'] == 2
    assert [a['kind'] for a in final['approvals']] == ['plan']
    assert [(v, p, r) for v, p, r in observed] == [(b'VALUE = 2\n', ['src/value.py'], 1), (b'VALUE = 3\n', ['src/value.py'], 1)]
    assert len([c for c in models.calls if c[0] == 'planner']) == 4
    assert ('developer', 'correcting') in models.calls
    assert ('verifier', 'verifying') in models.calls
    developer_prompts = [p for role, p, kwargs in models.prompts if role == 'developer']
    assert 'proposal.md' in developer_prompts[-1]['artifacts']
    assert developer_prompts[-1]['evidence_bundle']['pending_findings'][0]['code'] == 'wrong_value'


def test_semantic_failure_repairs_under_original_plan(tmp_path):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding()]]))
    approve(prepared)
    _, github, models, store, _, _, run_id, plan = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['revision'] == plan['revision']
    assert final['context']['implementation_correction_count'] == 1
    assert len([c for c in models.calls if c[0] == 'planner']) == 4
    assert len([c for c in models.calls if c[0] == 'openspec_verifier']) == 2


def test_scope_findings_request_new_approval_before_any_repair(tmp_path):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding('scope_spec')]]))
    approve(prepared)
    _, github, models, store, _, _, run_id, _ = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'awaiting_plan_review' and final['revision'] == 2
    assert not github.published
    assert ('developer', 'correcting') not in models.calls
    assert final['context']['implementation_correction_count'] == 0


@pytest.mark.parametrize('category', ['infrastructure_evidence', 'harness_defect'])
def test_nonimplementation_failure_stops_without_planner_or_repair(tmp_path, category):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding(category)]]))
    approve(prepared)
    _, github, models, store, _, _, run_id, _ = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'failed' and not github.published
    assert final['failure']['category'] == category
    assert len([c for c in models.calls if c[0] == 'planner']) == 4
    assert ('developer', 'correcting') not in models.calls


def test_noop_full_coverage_verifies_once_and_can_resolve_evidence(tmp_path):
    prepared = prepare(tmp_path, RepairModels(noop=True, semantic=[[finding()]]))
    approve(prepared)
    _, github, models, store, _, _, run_id, _ = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['context']['candidate_revision'] == 1
    assert len([c for c in models.calls if c[0] == 'openspec_verifier']) == 2
    assert not any(e['kind'] == 'scope_changed' for e in final['timeline'])


def test_repeated_noop_blocker_stops_before_second_equivalent_repair(tmp_path):
    prepared = prepare(tmp_path, RepairModels(noop=True, semantic=[[finding()], [finding(evidence='Different prose, same blocker')]]))
    approve(prepared)
    _, github, models, store, _, _, run_id, _ = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'failed' and not github.published
    assert final['failure']['category'] == 'no_progress'
    assert final['context']['implementation_correction_count'] == 1
    assert len([c for c in models.calls if c == ('developer', 'correcting')]) == 1


def test_two_corrections_share_technical_and_semantic_budget(tmp_path):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding(code='semantic_first')], [finding(code='semantic_second')]]))
    engine, github, models, store, _, _, run_id, _ = prepared
    calls = []

    def runner(*args):
        calls.append(1)
        return {'passed': len(calls) > 1, 'evidence': ['Synthetic byte check'],
                **({'findings': [finding(code='technical_first')]} if len(calls) == 1 else {})}

    engine.test_runner = runner
    approve(prepared)
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'failed' and not github.published
    assert final['failure']['category'] == 'correction_limit'
    assert final['context']['implementation_correction_count'] == 2
    assert len([c for c in models.calls if c == ('developer', 'correcting')]) == 2


def test_restart_retry_correcting_preserves_reserved_budget(tmp_path):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding()]], fail_correction=True))
    engine, github, models, store, coordinator, profile, run_id, _ = prepared
    with pytest.raises(RuntimeError, match='transport'):
        approve(prepared)
    saved = store.load(run_id)['attempts'][-1]
    assert saved['failure']['failed_stage'] == 'correcting'
    assert saved['context']['implementation_correction_count'] == 1
    restarted = ConversationEngine(profile, store, coordinator, lambda: github, lambda *_: models, engine.cli, engine.test_runner)
    restarted.retry(run_id, expected_revision=saved['revision'], actor='ana@example.com', failure_id=saved['failure']['id'])
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['context']['implementation_correction_count'] == 1
    assert final['context']['correction_id'] == saved['context']['correction_id']


def test_base_advance_keeps_corrections_consumed_before_replanning(tmp_path):
    prepared = prepare(tmp_path, RepairModels(semantic=[[finding()]]))
    engine, github, _, store, _, _, run_id, _ = prepared
    original_base = github.base_sha

    def advance_on_publish(branch):
        if store.load(run_id)['attempts'][-1]['stage'] == 'publishing':
            (github.source / 'README.md').write_bytes(b'Synthetic advanced base\n')
            git('add', '.', cwd=github.source)
            git('commit', '-m', 'Synthetic base advance', cwd=github.source)
            github.sha = git('rev-parse', 'HEAD', cwd=github.source)
        return original_base(branch)

    github.base_sha = advance_on_publish
    approve(prepared)
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'awaiting_clarification' and not github.published
    assert final['base_sha'] == github.sha
    assert final['context']['implementation_correction_count'] == 1


@pytest.mark.parametrize('managed', [False, True])
def test_developer_read_is_transferred_to_verifier_with_current_hash(tmp_path, managed, monkeypatch):
    original_engine = make_engine
    def with_consumer(path):
        result = original_engine(path)
        github = result[1]
        (github.source / 'src/io.py').write_text('CONSUMER = "value"\n', encoding='utf-8')
        git('add', '.', cwd=github.source)
        git('commit', '-m', 'Synthetic consumer', cwd=github.source)
        github.sha = git('rev-parse', 'HEAD', cwd=github.source)
        return result
    monkeypatch.setattr(__import__(__name__), 'make_engine', with_consumer)
    class ReadingModels(RepairModels):
        requested = False
        def complete(self, role, prompt, **kwargs):
            if role == 'developer' and not self.requested:
                self.requested = True
                return type('Response', (), {'text': json.dumps({'context_request': {
                    'op': 'read_file', 'path': 'src/io.py'}})})()
            return super().complete(role, prompt, **kwargs)

    models = ReadingModels()
    prepared = prepare(tmp_path, models, managed=managed)
    approve(prepared)
    _, github, _, store, _, _, run_id, _ = prepared
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    verifier = next(prompt for role, prompt, _ in models.prompts if role == 'openspec_verifier')
    sources = verifier['evidence_bundle']['observed_sources']
    assert any(item['path'] == 'src/value.py' and item['sha256'] == hashlib.sha256(b'VALUE = 2\n').hexdigest()
               for item in sources)
    assert any(item['path'] == 'src/io.py' and item['sha256'] == hashlib.sha256(b'CONSUMER = "value"\n').hexdigest()
               for item in sources)
    assert not any(item['sha256'] == hashlib.sha256(b'VALUE = 1\n').hexdigest() for item in sources)
