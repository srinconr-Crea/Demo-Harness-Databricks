import pytest
from harness.contracts import AgentCallContract
from harness.models import ModelClient
from test_integrations import FakeWorkspaceAPI


@pytest.mark.parametrize('fail', [False, True])
def test_model_call_preserves_candidate_identity_in_sink_and_contract(fail):
    class API(FakeWorkspaceAPI):
        def do(self, *args, **kwargs):
            if fail:
                raise RuntimeError('unavailable')
            return super().do(*args, **kwargs)

    saved = []
    api = API({'choices': [{'message': {'content': '{"ok":true}'}}]})
    models = ModelClient(api, {'developer': 'sonnet'}, {}, on_call=lambda role, call: saved.append(call))
    if fail:
        with pytest.raises(RuntimeError):
            models.complete('developer', 'apply', candidate_revision=2, candidate_hash='c' * 64)
    else:
        models.complete('developer', 'apply', candidate_revision=2, candidate_hash='c' * 64)
    assert saved[0].candidate_revision == 2 and saved[0].candidate_hash == 'c' * 64
    contract = AgentCallContract(call_id='call', run_id='run', attempt_id='attempt', story_id='HU', role='developer', model='sonnet', pricing_source='assumed', candidate_revision=saved[0].candidate_revision, candidate_hash=saved[0].candidate_hash)
    assert contract.model_dump()['candidate_hash'] == 'c' * 64


def test_historical_call_keeps_candidate_identity_absent():
    old = AgentCallContract(call_id='call', run_id='run', attempt_id='attempt', story_id='HU', role='developer', model='sonnet', pricing_source='assumed')
    assert old.candidate_revision is None and old.candidate_hash is None
