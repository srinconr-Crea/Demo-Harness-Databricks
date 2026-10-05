import json

import pytest
from harness.contracts import StoryRequest
from harness.openspec import OpenSpecCLI
from openspec_helpers import prepare_manual
from test_conversation import FakeModels, git, make_engine


def test_missing_skill_blocks_before_model_and_can_cancel(tmp_path):
    engine, github, models, _store, _, _ = make_engine(tmp_path)
    (github.source / '.agents/skills/openspec-explore/SKILL.md').unlink()
    git('add', '.', cwd=github.source); git('commit', '-m', 'incomplete', cwd=github.source)
    github.sha = git('rev-parse', 'HEAD', cwd=github.source)
    run_id = engine.submit(StoryRequest(hu='HU', description='Change'), actor='ana')
    with pytest.raises(ValueError, match='Preparación manual'):
        engine.advance(run_id)
    assert models.calls == [] and github.published == []

def test_recovery_blocks_tampered_skill_and_legacy_can_restart(tmp_path):
    engine, _github, _models, store, _, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU', description='Change'), actor='ana')
    engine.advance(run_id)
    record = store.load(run_id)
    record['attempts'][-1]['context']['instruction_catalog']['cli_version'] = 'wrong'
    store.save(run_id, record)
    with pytest.raises(ValueError, match='cambiaron'):
        engine.act(run_id, 'answer', actor='ana', text='2', expected_revision=0, key='answer')
    record = store.load(run_id)
    record['attempts'][-1]['context'].pop('instruction_engine')
    store.save(run_id, record)
    failed = engine.advance(run_id, action={'kind': 'answer', 'actor': 'ana', 'key': 'legacy', 'text': '2'})
    assert failed['state'] == 'failed'
    assert failed['attempts'][-1]['failure']['category'] == 'preparation_error'
    previous = record['attempts'][-1]['attempt_id']
    engine.retry_legacy(run_id)
    current = store.load(run_id)['attempts'][-1]
    assert current['attempt_id'] != previous
    assert current['context']['previous_attempt_id'] == previous
    assert current['publication_mode'] == 'diff_review'
    engine.advance(run_id)
    assert store.load(run_id)['state'] == 'awaiting_clarification'
    legacy = store.load(run_id)
    legacy['attempts'][-1]['context'].pop('instruction_engine')
    store.save(run_id, legacy)
    engine.act(run_id, 'cancel', actor='ana', expected_revision=0, key='cancel-legacy')
    assert store.load(run_id)['state'] == 'cancelled'

@pytest.mark.parametrize('context_enabled', [False, True])
def test_real_cli_skills_complete_automatic_conversation(tmp_path, context_enabled):
    engine, github, _, store, _, _ = make_engine(tmp_path)
    from harness.contracts import ContextPolicy
    engine.context_policy = ContextPolicy(enabled=context_enabled)
    prepare_manual(github.source)
    git('add', '.', cwd=github.source); git('commit', '-m', 'manual skills preparation', cwd=github.source)
    github.sha = git('rev-parse', 'HEAD', cwd=github.source)
    engine.cli = OpenSpecCLI()
    engine.publication_mode = 'approved_plan'
    class Models(FakeModels):
        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            payload = json.loads(prompt)
            if role == 'planner':
                value = json.loads(response.text)
                if payload['artifact'] == 'proposal':
                    change = payload['openspec_instructions']['changeName']
                    value['content'] += f'\n## Capabilities\n\n### New Capabilities\n- `{change}`: salida nueva.\n\n### Modified Capabilities\n\n## Impact\nCódigo sintético.\n'
                if payload['artifact'] == 'specs':
                    value['content'] = value['content'].replace('## ADDED Requirements',
                        '## Purpose\n\nProporcionar una salida sintética verificable para el consumidor del cliente.\n\n## ADDED Requirements')
                if payload['artifact'] == 'design':
                    value['content'] += '\n## Goals / Non-Goals\nSalida 2 dentro del perfil.\n\n## Risks / Trade-offs\nPruebas sintéticas.\n'
                response.text = json.dumps(value)
            return response
    models = Models()
    engine.models_factory = lambda *_args: models
    advanced = []
    def tests(*_args):
        if not advanced:
            (github.source / 'README.md').write_text('Nueva base sintética\n', encoding='utf-8')
            git('add', '.', cwd=github.source)
            git('commit', '-m', 'advance synthetic base', cwd=github.source)
            github.sha = git('rev-parse', 'HEAD', cwd=github.source)
            advanced.append(True)
        return {'passed': True, 'evidence': ['synthetic client test']}
    engine.test_runner = tests
    run_id = engine.submit(StoryRequest(hu='HU-REAL', description='Cambiar VALUE a 2'), actor='ana')
    engine.advance(run_id)
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    plan = store.load(run_id)['attempts'][-1]
    from harness.conversation import ConversationEngine
    engine = ConversationEngine(engine.profile, store, engine.coordinator, engine.github_factory,
                                engine.models_factory, engine.cli, tests, context_policy=engine.context_policy)
    engine.act(run_id, 'approve', actor='ana', expected_revision=plan['revision'],
               expected_hash=plan['context']['plan_hash'], key='approve')
    invalidated = store.load(run_id)['attempts'][-1]
    assert invalidated['stage'] == 'awaiting_clarification' and not github.published
    assert any(e['kind'] == 'base_advanced' for e in invalidated['timeline'])
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=invalidated['revision'], key='answer-new-base')
    updated = store.load(run_id)['attempts'][-1]
    engine.act(run_id, 'approve', actor='ana', expected_revision=updated['revision'],
               expected_hash=updated['context']['plan_hash'], key='approve-new-base')
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert all(not path.startswith('.agents/') for path in github.published[0])
    assert all('openspec_skill' in payload for role, payload, _ in models.prompts if role != 'verifier')
    assert {kwargs['instruction_provenance']['phase'] for role, _, kwargs in models.prompts if role != 'verifier'} == {'explore', 'propose', 'apply', 'verify'}
    for _, _, kwargs in models.prompts:
        if 'instruction_provenance' in kwargs:
            ref = kwargs['instruction_provenance']['snapshot_sha256']
            assert store.load_instruction_snapshot(run_id, final['attempt_id'], ref)
    assert {'sync', 'archive'} <= {e['details']['phase'] for e in final['timeline'] if e['kind'] == 'instructions'}
