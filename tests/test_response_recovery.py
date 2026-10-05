import json
from decimal import Decimal
from pathlib import Path

import pytest

from harness.models import ModelClient
from harness.repo_context import ContextResponseError, contextual_answer
from harness.contracts import StoryRequest
from test_integrations import FakeWorkspaceAPI
from test_conversation import make_engine


def client(text, **options):
    api = FakeWorkspaceAPI({'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]})
    return ModelClient(api, {'planner': 'sonnet'}, {'sonnet': (Decimal('.1'), Decimal('.2'))}, **options)


def test_role_budget_is_effective_and_rejects_incompatible_endpoint():
    model = client('{"content":"ok"}', max_tokens=12000, role_max_tokens={'planner': 64000},
                   endpoint_capabilities={'sonnet': {'max_output_tokens': 64000}})
    contextual_answer(model, 'planner', {'artifact': 'proposal'})
    assert model.api.calls[0][2]['max_tokens'] == 64000
    assert model.calls[0].effective_max_tokens == 64000
    model.endpoint_capabilities['sonnet']['max_output_tokens'] = 10000
    with pytest.raises(ValueError, match='límite'):
        model.complete('planner', 'prompt')
    assert len(model.api.calls) == 1


def test_literal_newlines_are_normalized_with_evidence_without_new_call():
    model = client('{"content":"line one\nline two\r\nlast\titem"}')
    result = contextual_answer(model, 'planner', {'artifact': 'design'})
    assert result['content'] == 'line one\nline two\r\nlast\titem'
    assert len(model.calls) == 1
    assert model.calls[0].acceptance == 'normalized'
    assert model.calls[0].normalized_sha256


def test_truncation_is_classified_before_json_parse_without_repair():
    model = client('{"content":"cut')
    model.api.response['choices'][0]['finish_reason'] = 'length'
    with pytest.raises(ContextResponseError, match='output_truncated'):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 1
    assert model.calls[0].acceptance == 'output_truncated'


def test_duplicate_keys_rejected_without_repair():
    model = client('{"content":"one","content":"two"}')
    with pytest.raises(ContextResponseError, match='invalid_contract'):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 1


def test_repair_has_one_call_and_preserves_link_and_cost():
    model = client('{"content": "ok",}')
    original = model.api.do
    def sequence(method, path, body=None):
        if len(model.api.calls):
            model.api.response['choices'][0]['message']['content'] = '{"content":"fixed"}'
        model.api.response['usage'] = {'prompt_tokens': 2, 'completion_tokens': 3}
        return original(method, path, body)
    model.api.do = sequence
    assert contextual_answer(model, 'planner', {'artifact': 'design'})['content'] == 'fixed'
    assert len(model.calls) == 2
    assert model.calls[1].parent_call_id == model.calls[0].call_id
    assert model.calls[1].recovery_index == 1
    assert all(call.cost_usd == Decimal('.8') for call in model.calls)


def test_repair_exhaustion_is_finite():
    model = client('{"content": "ok",}')
    with pytest.raises(ContextResponseError, match='malformed_json'):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 2


@pytest.mark.parametrize('value', [0, -1, True, 6.5, '64000'])
def test_invalid_role_budgets_rejected(value):
    with pytest.raises(ValueError):
        client('{}', role_max_tokens={'planner': value})


def test_budget_and_schema_requests_with_historical_fallback():
    model = client('{"content":"a"}', max_tokens=12000,
        endpoint_capabilities={'sonnet': {'json_schema': True}})
    contextual_answer(model, 'planner', {'artifact': 'design'})
    request = model.api.calls[0][2]
    assert request['max_tokens'] == 12000
    assert request['response_format']['type'] == 'json_schema'
    assert request['stream'] is False
    model.max_context_tokens = 12001
    with pytest.raises(ValueError, match='presupuesto'):
        model.complete('planner', 'too long')
    assert len(model.api.calls) == 1


def test_no_silent_schema_fallback_on_http_failure():
    model = client('{}', endpoint_capabilities={'sonnet': {'json_schema': True}})
    def failure(*args, **kwargs):
        raise RuntimeError('unsupported schema')
    model.api.do = failure
    with pytest.raises(RuntimeError, match='unsupported schema'):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 1 and model.calls[0].status == 'failed'


@pytest.mark.parametrize('body,want', [
    ('{"content":"quote \\" and slash \\\\"}', 'quote " and slash \\'),
    ('{"content":"\\n is escaped"}', '\n is escaped'),
])
def test_escaping_preserved(body, want):
    model = client(body)
    assert contextual_answer(model, 'planner', {'artifact': 'design'})['content'] == want
    assert len(model.calls) == 1


def test_incomplete_string_not_invented_and_no_repair():
    model = client('{"content":"unfinished\n')
    with pytest.raises(ContextResponseError):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 1


def test_repair_cannot_request_context():
    model = client('{"content":"x",}')
    original = model.api.do
    def sequence(*args, **kwargs):
        if model.api.calls:
            model.api.response['choices'][0]['message']['content'] = '{"context_request":{"op":"list_tree"}}'
        return original(*args, **kwargs)
    model.api.do = sequence
    with pytest.raises(ContextResponseError, match='invalid_contract'):
        contextual_answer(model, 'planner', {'artifact': 'design'})
    assert len(model.calls) == 2


def test_full_response_log_cut_does_not_mean_model_truncated():
    model = client(json.dumps({'content': 'x' * 1000}), log_text_limit=40)
    assert contextual_answer(model, 'planner', {'artifact': 'design'})['content'] == 'x' * 1000
    assert model.calls[0].finish_reason == 'stop'
    assert model.calls[0].acceptance == 'parsed'
    assert '[TRUNCATED]' in model.calls[0].output_text


def test_empty_truncation_preserves_finish_reason_and_request_identity():
    model = client('')
    model.api.response['choices'][0]['finish_reason'] = 'length'
    model.api.response['databricks_request_id'] = 'request-empty'
    with pytest.raises(ValueError):
        model.complete('planner', 'prompt')
    assert model.calls[0].finish_reason == 'length'
    assert model.calls[0].databricks_request_id == 'request-empty'
    assert model.calls[0].acceptance == 'output_truncated'


def test_stale_response_marking_preserves_normalized_evidence():
    model = client('{"content":"a\nb"}')
    response = model.complete('planner', 'prompt')
    model.mark_response('planner', response, 'normalized', '{"content":"a\\nb"}')
    model.mark_response('planner', response, 'invalid_contract')
    assert model.calls[0].normalized_text == '{"content":"a\\nb"}'
    assert model.calls[0].normalized_sha256


def test_failure_is_durable_and_retry_preserves_clarification(tmp_path: Path):
    engine, github, models, store, coord, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-failure', description='Cambiar salida'), actor='ana')
    engine.advance(run_id)
    original = models.complete
    def failing(role, prompt, **kwargs):
        if role == 'planner' and json.loads(prompt).get('artifact') == 'specs':
            raise ContextResponseError('output_truncated')
        return original(role, prompt, **kwargs)
    models.complete = failing
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    record = engine.get(run_id)
    attempt = record['attempts'][-1]
    assert record['state'] == attempt['stage'] == 'failed'
    assert coord.get(run_id, attempt['attempt_id'])['stage'] == 'failed'
    assert attempt['failure']['failed_stage'] == 'proposing'
    assert attempt['failure']['retryable']
    checkpoint = store.load_checkpoint(run_id, attempt['attempt_id'], attempt['checkpoint_id'])
    assert any(path.endswith('proposal.md') for path in checkpoint['files'])
    assert engine.advance(run_id)['state'] == 'failed'
    models.complete = original
    engine.retry(run_id, expected_revision=attempt['revision'], actor='ana', failure_id=attempt['failure']['id'])
    assert engine.get(run_id)['state'] == 'awaiting_plan_review'
    assert any(m.get('text') == 'Salida 2' for m in engine.get(run_id)['attempts'][-1]['messages'])
    with pytest.raises(ValueError):
        engine.retry(run_id, expected_revision=attempt['revision'], actor='ana', failure_id=attempt['failure']['id'])
    assert github.published == []


def test_stale_retry_cannot_roll_back_newer_coordinator_stage(tmp_path, monkeypatch):
    import copy
    engine, _, models, _, coord, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-race', description='Salida nueva'), actor='ana')
    original_complete = models.complete
    def fail(role, *args, **kwargs):
        if role == 'planner':
            raise ContextResponseError('malformed_json')
        return original_complete(role, *args, **kwargs)
    engine.advance(run_id)
    models.complete = fail
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    stale = copy.deepcopy(engine.get(run_id))
    attempt = stale['attempts'][-1]
    models.complete = original_complete
    engine.retry(run_id, expected_revision=attempt['revision'], actor='ana', failure_id=attempt['failure']['id'])
    before = coord.get(run_id, attempt['attempt_id'])
    monkeypatch.setattr(engine, 'get', lambda _: copy.deepcopy(stale))
    with pytest.raises(ValueError):
        engine.retry(run_id, expected_revision=attempt['revision'], actor='ana', failure_id=attempt['failure']['id'])
    after = coord.get(run_id, attempt['attempt_id'])
    assert after == before


def test_updating_failure_keeps_human_feedback_for_retry(tmp_path):
    engine, _, models, _, _, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-update', description='Salida nueva'), actor='ana')
    engine.advance(run_id)
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    attempt = engine.get(run_id)['attempts'][-1]
    original = models.complete
    def failure(role, *args, **kwargs):
        if role == 'planner':
            raise ContextResponseError('malformed_json')
        return original(role, *args, **kwargs)
    models.complete = failure
    engine.act(run_id, 'changes', actor='ana', text='Añadir criterio adicional', expected_revision=attempt['revision'], key='change')
    assert engine.get(run_id)['attempts'][-1]['context'].get('feedback') == 'Añadir criterio adicional'


def test_checkout_failure_is_visible_and_durable(tmp_path):
    engine, github, _, _, coord, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-checkout', description='Salida'), actor='ana')
    def failure(*args):
        raise RuntimeError('checkout unavailable')
    github.checkout = failure
    with pytest.raises(RuntimeError, match='checkout unavailable'):
        engine.advance(run_id)
    record = engine.get(run_id)
    attempt = record['attempts'][-1]
    assert record['state'] == 'failed'
    assert attempt['failure']['failed_stage'] == 'exploring'
    assert coord.get(run_id, attempt['attempt_id'])['stage'] == 'failed'


@pytest.mark.parametrize('changed_profile', [False, True])
def test_retry_api_checks_identity_revision_and_profile_then_preserves_history(tmp_path, changed_profile):
    from fastapi.testclient import TestClient
    from harness.conversation_webapp import create_conversation_app
    engine, _, models, _, _, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-api-failed', description='Salida'), actor='ana@example.com')
    engine.advance(run_id)
    original = models.complete
    def failure(role, *args, **kwargs):
        if role == 'planner':
            raise ContextResponseError('malformed_json')
        return original(role, *args, **kwargs)
    models.complete = failure
    engine.act(run_id, 'answer', actor='ana@example.com', text='Salida 2', expected_revision=0, key='answer')
    failed = engine.get(run_id)['attempts'][-1]
    models.complete = original
    calls = len(models.calls)
    if changed_profile:
        profile.version = '2'
    with TestClient(create_conversation_app(engine, profile)) as http:
        assert engine.get(run_id)['state'] == 'failed'
        assert len(models.calls) == calls  # Restart never retries a failed HU.
        url = f'/runs/{run_id}/retry'
        request = {'expected_revision': failed['revision'], 'failure_id': failed['failure']['id']}
        assert http.post(url, json=request, headers={'x-forwarded-user': 'otro@example.com'}).status_code == 403
        owner = {'x-forwarded-user': 'ana@example.com'}
        assert http.post(url, json={**request, 'expected_revision': 50}, headers=owner).status_code == 409
        if not changed_profile:
            assert http.post(url, json={**request, 'failure_id': '0'*32}, headers=owner).status_code == 409
        assert http.post(url, json=request, headers=owner).status_code == 202
    record = engine.get(run_id)
    assert record['state'] == 'awaiting_plan_review'
    assert any(message['text'] == 'Salida 2' for message in record['attempts'][-1]['messages'])
    assert len(record['attempts']) == (2 if changed_profile else 1)


def test_new_call_fields_round_trip_without_fabricated_usage():
    from harness.contracts import AgentCallContract
    call = AgentCallContract(call_id='c', run_id='r', attempt_id='a', story_id='s', role='planner',
        model='sonnet', pricing_source='configured', finish_reason='length', effective_max_tokens=64000,
        acceptance='output_truncated', parent_call_id='original', recovery_index=1)
    loaded = AgentCallContract.model_validate(call.model_dump(mode='json'))
    assert loaded.finish_reason == 'length' and loaded.effective_max_tokens == 64000
    assert loaded.estimated_cost_usd is None
    historical = AgentCallContract(call_id='old', run_id='r', attempt_id='a', story_id='s',
        role='planner', model='sonnet', pricing_source='configured')
    assert historical.finish_reason is None and historical.acceptance is None
