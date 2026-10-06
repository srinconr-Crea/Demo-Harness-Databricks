"""Presentation regressions using synthetic model responses and client repositories."""
import copy
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from harness.contracts import ContextPolicy, StoryRequest
from harness.models import ModelClient
from harness.prompt_contracts import validate_artifact_content
from harness.repo_context import ContextResponseError, RepoContext, contextual_answer
from harness.conversation_webapp import create_conversation_app
from test_context_manager import setup_manager
from test_conversation import make_engine


PAYLOAD = {'artifact': 'design', 'template': '# Design\n\n## Context\n\n## Decisions'}
FINAL = {'content': '# Design\n\n## Context\nEjemplo: {"x": "quote"}.\n\n## Decisions\nConservar contenido.'}


def sequence(values, *, usage=True, finish='stop', on_call=None):
    replies = iter(values)
    class API:
        def __init__(self):
            self.calls = []
        def do(self, method, path, body=None):
            self.calls.append(body)
            text = next(replies)
            if isinstance(text, Exception):
                raise text
            result = {'choices': [{'message': {'content': text}, 'finish_reason': finish}]}
            if usage:
                result['usage'] = {'prompt_tokens': 10, 'completion_tokens': 20}
            return result
    return ModelClient(API(), {'planner': 'sonnet', 'explorer': 'sonnet'},
                       {'sonnet': (Decimal('.1'), Decimal('.2'))}, on_call=on_call)


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('phase', ['propose', 'update'])
def test_canonical_contract_is_sent_in_both_prompt_routes(tmp_path, enabled, phase):
    manager, profile = setup_manager(tmp_path)
    model = sequence([json.dumps(FINAL)])
    contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile),
                      context_manager=manager if enabled else None, phase=phase)
    prompt = json.loads(model.api.calls[0]['messages'][1]['content'])
    assert prompt['artifact_structure']['required_headings'] == ['Context', 'Decisions']
    assert 'literalmente' in prompt['artifact_structure']['instruction']
    assert 'español' in prompt['artifact_structure']['instruction']


def test_heading_translation_reports_missing_canonical_title():
    content = '# Proposal\n\n## Why\nMotivo.\n\n## Qué cambia\nCambio.\n\n## Impact\nCódigo.'
    with pytest.raises(ValueError, match='What Changes') as error:
        validate_artifact_content(content, {'artifact': 'proposal', 'template': '## Why\n## What Changes\n## Impact'})
    assert type(error.value).__name__ == 'ArtifactPresentationError'
    assert error.value.category == 'invalid_contract'


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('usage', [False, True])
@pytest.mark.parametrize('wrapper', ['Antes\n{}\nDespués', '<invoke name="x"></invoke>\n{}'])
def test_wrapped_final_has_one_linked_repair_and_preserves_value(tmp_path, enabled, usage, wrapper):
    manager, profile = setup_manager(tmp_path)
    saved = []
    model = sequence([wrapper.format(json.dumps(FINAL)), json.dumps(FINAL)], usage=usage,
                     on_call=lambda role, response: saved.append(response))
    result = contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile),
                               context_manager=manager if enabled else None, phase='propose')
    assert result == FINAL
    assert len(model.api.calls) == 2
    first, fixed = model.calls
    assert first.acceptance == 'malformed_json'
    assert fixed.parent_call_id == first.call_id and fixed.recovery_index == 1
    assert first.output_sha256 and fixed.output_sha256
    assert first.cost_usd == fixed.cost_usd == (Decimal('5') if usage else None)
    assert any(item.call_id == first.call_id and item.acceptance == 'malformed_json' for item in saved)


@pytest.mark.parametrize('bad', [
    'prefix {"content":"unfinished',
    'prefix ' + json.dumps(FINAL) + ' ' + json.dumps(FINAL),
    json.dumps(FINAL) + ' ' + json.dumps(FINAL),
    'prefix {"content":"first","content":"second"}',
    'prefix {"context_request":{"op":"list_tree"}}',
    'prefix {"content":"# Design\\n\\n## Context\\nMissing decisions."}',
])
def test_ambiguous_or_invalid_wrapper_has_no_repair(tmp_path, bad):
    manager, profile = setup_manager(tmp_path)
    model = sequence([bad])
    with pytest.raises(ValueError):
        contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile))
    assert len(model.api.calls) == 1


@pytest.mark.parametrize('fixed', [json.dumps({**FINAL, 'content': FINAL['content'] + ' changed'}),
                                  '{"context_request":{"op":"list_tree"}}', '', 'again ' + json.dumps(FINAL)])
def test_repair_cannot_change_contract_or_repeat(tmp_path, fixed):
    _, profile = setup_manager(tmp_path)
    model = sequence(['prefix ' + json.dumps(FINAL), fixed])
    with pytest.raises(ValueError):
        contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile))
    assert len(model.api.calls) == 2


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('role', ['explorer', 'planner'])
def test_xml_context_request_never_reads_or_repairs(tmp_path, enabled, role):
    manager, profile = setup_manager(tmp_path)
    context = RepoContext(tmp_path, profile)
    reads = []
    context.request = lambda value: reads.append(value)
    model = sequence(['<invoke name="x">\n</invoke>\n\n{"context_request":{"op":"read_file","path":"src/common/schema.py"}}'])
    with pytest.raises(ContextResponseError, match='malformed_json'):
        contextual_answer(model, role, PAYLOAD if role == 'planner' else {}, context,
                          context_manager=manager if enabled else None,
                          phase='propose' if role == 'planner' else 'explore')
    assert reads == [] and len(model.api.calls) == 1


@pytest.mark.parametrize('enabled', [False, True])
def test_presentation_retry_is_durable_authorized_and_waits_for_plan(tmp_path, enabled):
    engine, github, models, store, coordinator, profile = make_engine(tmp_path)
    engine.context_policy = ContextPolicy(enabled=enabled)
    run_id = engine.submit(StoryRequest(hu='HU-format', description='Salida sintética'), actor='ana@example.com')
    engine.advance(run_id)
    original = models.complete
    def bad(role, prompt, **kwargs):
        response = original(role, prompt, **kwargs)
        if role == 'planner' and json.loads(prompt)['artifact'] == 'design':
            value = json.loads(response.text)
            value['content'] = value['content'].replace('\n', '\\n')
            response.text = json.dumps(value)
        return response
    models.complete = bad
    engine.act(run_id, 'answer', actor='ana@example.com', text='Salida 2', expected_revision=0, key='answer')
    failed = copy.deepcopy(engine.get(run_id)['attempts'][-1])
    assert failed['failure']['retryable'] and failed['failure']['category'] == 'invalid_contract'
    checkpoint = store.load_checkpoint(run_id, failed['attempt_id'], failed['checkpoint_id'])
    assert any(path.endswith('proposal.md') for path in checkpoint['files'])
    calls = len(models.calls)
    models.complete = original
    with TestClient(create_conversation_app(engine, profile)) as http:
        assert engine.get(run_id)['state'] == 'failed' and len(models.calls) == calls
        url = f'/runs/{run_id}/retry'
        request = {'expected_revision': failed['revision'], 'failure_id': failed['failure']['id']}
        assert http.post(url, json=request, headers={'x-forwarded-user': 'otro'}).status_code == 403
        owner = {'x-forwarded-user': 'ana@example.com'}
        assert http.post(url, json={**request, 'failure_id': '0' * 32}, headers=owner).status_code == 409
        assert http.post(url, json={**request, 'expected_revision': 100}, headers=owner).status_code == 409
        assert len(models.calls) == calls
        assert http.post(url, json=request, headers=owner).status_code == 202
    assert engine.get(run_id)['state'] == 'awaiting_plan_review'
    assert not github.published and not any(role == 'developer' for role, _ in models.calls)


@pytest.mark.parametrize('enabled', [False, True])
def test_bad_manifest_is_not_reclassified_as_presentation(tmp_path, enabled):
    engine, _, models, _, _, _ = make_engine(tmp_path)
    engine.context_policy = ContextPolicy(enabled=enabled)
    run_id = engine.submit(StoryRequest(hu='HU-policy', description='Salida'), actor='ana')
    engine.advance(run_id)
    original = models.complete
    def bad(role, prompt, **kwargs):
        response = original(role, prompt, **kwargs)
        if role == 'planner':
            value = json.loads(response.text)
            value['content'] = value['content'].replace('\n', '\\n')
            value['manifest'] = [{'op': 'modify', 'path': '../private.py'}]
            response.text = json.dumps(value)
        return response
    models.complete = bad
    try:
        engine.act(run_id, 'answer', actor='ana', text='2', expected_revision=0, key='answer')
    except ValueError:
        pass
    failure = engine.get(run_id)['attempts'][-1]['failure']
    assert not failure['retryable']


@pytest.mark.parametrize('enabled', [False, True])
def test_wrapper_cannot_repair_policy_denial(tmp_path, enabled):
    engine, _, _, _, _, profile = make_engine(tmp_path)
    manager, _ = setup_manager(tmp_path)
    manager.profile = profile
    candidate = {'content': '# Proposal\n\n## Why\nMotivo.\n\n## What Changes\nCambio.',
                 'summary': 'Salida', 'manifest': [{'op': 'modify', 'path': '../private.py'}]}
    model = sequence(['prefix ' + json.dumps(candidate)])
    with pytest.raises(ValueError, match='política'):
        contextual_answer(model, 'planner', {'artifact': 'proposal', 'template': '## Why\n## What Changes'},
                          RepoContext(tmp_path, profile), context_manager=manager if enabled else None, phase='propose')
    assert len(model.api.calls) == 1 and model.calls[0].acceptance == 'invalid_contract'


def test_wrapped_silver_output_uses_exact_bounded_contract(tmp_path):
    from harness.contracts import ClientProfile
    from test_notebook_edit import strategy
    bounded = strategy()
    profile = ClientProfile(repository='example/client', base_branch='develop', allowed_paths=[bounded.notebook],
                            strategy=bounded, openspec_root='openspec')
    value = {**FINAL, 'strategy': 'silver_safe_ratio', 'code_path': bounded.notebook, 'expression': 'a / b'}
    payload = {**PAYLOAD, 'expected_expression': 'a / b'}
    model = sequence(['prefix ' + json.dumps(value), json.dumps(value)])
    assert contextual_answer(model, 'planner', payload, profile=profile) == value
    assert len(model.api.calls) == 2
    changed = {**value, 'expression': 'unapproved'}
    model = sequence(['prefix ' + json.dumps(changed)])
    with pytest.raises(ValueError, match='política'):
        contextual_answer(model, 'planner', payload, profile=profile)
    assert len(model.api.calls) == 1


@pytest.mark.parametrize('finish', ['length', 'max_tokens', 'max_output_tokens'])
def test_wrapped_truncation_is_rejected_without_repair(tmp_path, finish):
    _, profile = setup_manager(tmp_path)
    model = sequence(['prefix ' + json.dumps(FINAL)], finish=finish)
    with pytest.raises(ContextResponseError, match='output_truncated'):
        contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile))
    assert len(model.api.calls) == 1 and model.calls[0].acceptance == 'output_truncated'


def test_repair_invocation_failure_is_recorded(tmp_path):
    _, profile = setup_manager(tmp_path)
    model = sequence(['prefix ' + json.dumps(FINAL), RuntimeError('endpoint unavailable')])
    with pytest.raises(ValueError, match='endpoint unavailable'):
        contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile))
    assert len(model.calls) == 2 and model.calls[1].status == 'failed'
    assert model.calls[1].parent_call_id == model.calls[0].call_id
    assert model.calls[1].cost_usd is None


def test_snapshot_failure_stops_before_repair(tmp_path):
    _, profile = setup_manager(tmp_path)
    def storage_error(role, response):
        raise OSError('snapshot unavailable')
    model = sequence(['prefix ' + json.dumps(FINAL)], on_call=storage_error)
    with pytest.raises(OSError, match='snapshot unavailable'):
        contextual_answer(model, 'planner', PAYLOAD, RepoContext(tmp_path, profile))
    assert len(model.api.calls) == 1


def test_json_equality_rejects_boolean_number_substitution():
    from harness.repo_context import _same_json
    assert not _same_json({'x': [True]}, {'x': [1]})
    assert _same_json({'x': [True, 'é']}, {'x': [True, 'é']})
