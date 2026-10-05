"""Regression for malformed context envelopes before any repository access."""
import json
from decimal import Decimal

import pytest

from harness.models import ModelClient
from harness.repo_context import ContextResponseError, RepoContext, contextual_answer
from test_context_manager import setup_manager


class Replies:
    def __init__(self, values):
        self.values = iter(values)
        self.bodies = []

    def do(self, *args, body):
        self.bodies.append(body)
        return {'choices': [{'message': {'content': json.dumps(next(self.values))},
                             'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20}}


def model(values):
    api = Replies(values)
    return ModelClient(api, {'explorer': 'sonnet'},
                       {'sonnet': (Decimal('.1'), Decimal('.2'))})


BAD = [
    {'context_request': [{'op': 'read_file', 'path': 'src/common/schema.py'},
                         {'op': 'list_tree', 'path': 'tests'},
                         {'op': 'search_text', 'path': 'src', 'query': 'detect_format'}]},
    {'context_request': None}, {'context_request': 'private-value'},
    {'context_request': {'op': 'list_tree'}, 'summary': 'mixed'},
    {'context_request': {'op': 'shell'}},
    {'context_request': {'op': []}},
    {'context_request': {'op': 'list_tree', 'path': 'private-value'}},
    {'context_request': {'op': 'search_text', 'query': 'ok', 'path': 'src'}},
    {'context_request': {'op': 'read_file', 'path': 12}},
    {'context_request': {'op': 'read_file', 'path': 'a' * 501}},
    {'context_request': {'op': 'search_text', 'query': ''}},
    {'context_request': {'op': 'search_text', 'query': 'a' * 201}},
]


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('value', BAD)
def test_malformed_context_is_recoverable_without_read_or_repair(tmp_path, enabled, value):
    manager, profile = setup_manager(tmp_path)
    context = RepoContext(tmp_path, profile)
    invoked = []
    context.request = lambda request: invoked.append(request)
    client = model([value])
    with pytest.raises(ContextResponseError) as failure:
        contextual_answer(client, 'explorer', {}, context,
                          context_manager=manager if enabled else None, phase='explore')
    assert failure.value.category == 'invalid_contract'
    assert 'private-value' not in str(failure.value)
    assert invoked == []
    assert len(client.calls) == len(client.api.bodies) == 1
    call = client.calls[0]
    assert call.status == 'complete' and call.finish_reason == 'stop'
    assert call.acceptance == 'invalid_contract'
    assert call.input_tokens == 10 and call.output_tokens == 20
    assert call.cost_usd == Decimal('5')


@pytest.mark.parametrize('enabled', [False, True])
def test_successive_requests_and_contract_are_identical(tmp_path, enabled):
    from harness.prompt_contracts import TOOLS, context_contract
    manager, profile = setup_manager(tmp_path)
    (tmp_path / 'source.txt').write_text('synthetic marker', encoding='utf-8')
    context = RepoContext(tmp_path, profile)
    client = model([{'context_request': {'op': 'read_file', 'path': 'source.txt'}},
                    {'context_request': {'op': 'search_text', 'query': 'marker'}},
                    {'summary': 'ok', 'questions': []}])
    value = contextual_answer(client, 'explorer', {}, context,
                              context_manager=manager if enabled else None, phase='explore')
    assert value == {'summary': 'ok', 'questions': []}
    assert len(client.calls) == 3 and context.requests == 2
    for body in client.api.bodies:
        payload = json.loads(body['messages'][1]['content'])
        assert payload['context_tools'] == TOOLS
        assert payload['context_contract'] == context_contract()


@pytest.mark.parametrize('enabled', [False, True])
def test_denied_read_still_returns_controlled_feedback(tmp_path, enabled):
    manager, profile = setup_manager(tmp_path)
    context = RepoContext(tmp_path, profile)
    client = model([{'context_request': {'op': 'read_file', 'path': '.env'}},
                    {'summary': 'No se accedio al archivo', 'questions': []}])
    contextual_answer(client, 'explorer', {}, context,
                      context_manager=manager if enabled else None, phase='explore')
    payload = json.loads(client.api.bodies[1]['messages'][1]['content'])
    assert payload['context_history'][0]['result']['error']
    assert client.calls[0].acceptance != 'invalid_contract'


def test_retrieval_disabled_rejects_request(tmp_path):
    client = model([{'context_request': {'op': 'list_tree'}}])
    with pytest.raises(ContextResponseError, match='habilitado'):
        contextual_answer(client, 'explorer', {})
    assert client.calls[0].acceptance == 'invalid_contract'


@pytest.mark.parametrize('stage', ['exploring', 'proposing', 'updating'])
def test_new_context_format_failure_persists_and_human_retry_restores_stage(tmp_path, stage):
    from types import SimpleNamespace
    from harness.contracts import StoryRequest
    from test_conversation import make_engine
    engine, github, models, store, coord, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-context-format', description='Salida sintetica'), actor='ana')
    original = models.complete
    if stage != 'exploring':
        engine.advance(run_id)
    if stage == 'updating':
        engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    def malformed(role, *args, **kwargs):
        if role == ('explorer' if stage == 'exploring' else 'planner'):
            return SimpleNamespace(text=json.dumps(BAD[0]), finish_reason='stop')
        return original(role, *args, **kwargs)
    models.complete = malformed
    if stage == 'exploring':
        engine.advance(run_id)
    else:
        attempt = engine.get(run_id)['attempts'][-1]
        engine.act(run_id, 'changes' if stage == 'updating' else 'answer', actor='ana',
                   text='Salida 2', expected_revision=attempt['revision'], key='trigger')
    attempt = engine.get(run_id)['attempts'][-1]
    assert attempt['failure']['category'] == 'invalid_contract'
    assert attempt['failure']['retryable'] is True
    assert attempt['failure']['failed_stage'] == stage
    assert coord.get(run_id, attempt['attempt_id'])['stage'] == 'failed'
    checkpoint = store.load_checkpoint(run_id, attempt['attempt_id'], attempt['checkpoint_id'])
    assert checkpoint['metadata']['attempt']['failure']['id'] == attempt['failure']['id']
    before = len(models.calls)
    engine.advance(run_id)
    assert len(models.calls) == before and github.published == []
    models.complete = original
    engine.retry(run_id, expected_revision=attempt['revision'], actor='ana',
                 failure_id=attempt['failure']['id'])
    assert engine.get(run_id)['state'] == ('awaiting_clarification' if stage == 'exploring' else 'awaiting_plan_review')
    assert github.published == []


def test_historical_nonretryable_error_is_not_migrated(tmp_path):
    from harness.contracts import StoryRequest
    from test_conversation import make_engine
    engine, _, models, store, _, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-history', description='Sintetica'), actor='ana')
    def historical_failure(*args, **kwargs):
        raise ValueError('Solicitud de contexto inválida')
    models.complete = historical_failure
    with pytest.raises(ValueError, match='Solicitud de contexto'):
        engine.advance(run_id)
    attempt = engine.get(run_id)['attempts'][-1]
    assert attempt['failure']['retryable'] is False
    before = store.load(run_id)
    engine.advance(run_id)
    assert store.load(run_id) == before and models.calls == []
    with pytest.raises(ValueError, match='vigente'):
        engine.retry(run_id, expected_revision=0, actor='ana', failure_id=attempt['failure']['id'])
