from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from harness.contracts import AgentCallContract
from harness.models import ModelClient, load_model_config


CONFIG = Path(__file__).resolve().parents[1] / 'src/agents/harness/config/defaults/models.yaml'


class UsageAPI:
    def __init__(self, usage):
        self.usage = usage

    def do(self, *args, **kwargs):
        return {'choices': [{'message': {'content': 'ok'}}], 'usage': self.usage}


def test_verified_prices_produce_independent_decimal_costs():
    routing, prices, _ = load_model_config(CONFIG)
    api = UsageAPI({'prompt_tokens': 1000000, 'completion_tokens': 1000000})
    client = ModelClient(api, routing, prices)
    assert client.complete('developer', 'synthetic').cost_usd == Decimal('17.999940')
    assert client.complete('verifier', 'synthetic').cost_usd == Decimal('9.000075')


@pytest.mark.parametrize('rate', ['-0.1', 'NaN', 'Infinity', '0', 'not-money'])
def test_invalid_config_rate_fails_before_invocation(tmp_path, rate):
    config = yaml.safe_load(CONFIG.read_text())
    config['pricing']['endpoints']['databricks-claude-sonnet-5-5']['input_usd_per_token'] = rate
    path = tmp_path / 'models.yaml'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='tarifa'):
        load_model_config(path)


def test_invalid_direct_rate_is_rejected_without_endpoint_invocation():
    with pytest.raises(ValueError, match='tarifa'):
        ModelClient(UsageAPI({}), {'developer': 'endpoint'},
                    {'endpoint': (Decimal('-1'), Decimal('1'))})


def test_snapshot_reproduces_cost_and_survives_response_marking():
    from harness.models import load_pricing_snapshots
    routing, prices, _ = load_model_config(CONFIG)
    snapshots = load_pricing_snapshots(CONFIG)
    client = ModelClient(UsageAPI({'prompt_tokens': 1000, 'completion_tokens': 200}), routing,
                         prices, pricing_snapshots=snapshots)
    response = client.complete('developer', 'synthetic')
    snapshot = response.pricing_snapshot
    assert snapshot['version'] == 'harness-costops-2026-10-07'
    assert snapshot['input_usd_per_token'] == '0.000002999955'
    assert response.cost_usd == Decimal('0.005999952')
    marked = client.mark_response('developer', response, 'accepted')
    assert marked.pricing_snapshot == snapshot
    # Mutating the caller's configuration cannot rewrite recorded snapshots.
    snapshots[response.model]['input_usd_per_token'] = '99'
    assert response.pricing_snapshot['input_usd_per_token'] == '0.000002999955'


def test_snapshot_kept_without_usage_and_previous_records_not_reestimated():
    from harness.models import load_pricing_snapshots
    routing, prices, source = load_model_config(CONFIG)
    client = ModelClient(UsageAPI({}), routing, prices,
                         pricing_snapshots=load_pricing_snapshots(CONFIG))
    response = client.complete('developer', 'synthetic')
    assert response.cost_usd is None
    call = AgentCallContract(call_id=response.call_id, run_id='r', attempt_id='a', story_id='HU',
        role='developer', model=response.model, pricing_source=source,
        pricing_snapshot=response.pricing_snapshot)
    assert call.schema_version == 4
    assert call.model_dump(mode='json')['pricing_snapshot']['currency'] == 'USD'
    for version in (2, 3):
        old = AgentCallContract.model_validate(dict(schema_version=version, call_id='c', run_id='r',
            attempt_id='a', story_id='HU', role='developer', model='historical',
            pricing_source='historical', estimated_cost_usd='0.002'))
        assert old.pricing_snapshot is None
        assert old.estimated_cost_usd == Decimal('0.002')


def test_snapshot_disagreement_with_cost_rates_fails_before_endpoint():
    from harness.models import load_pricing_snapshots
    routing, prices, _ = load_model_config(CONFIG)
    snapshots = load_pricing_snapshots(CONFIG)
    snapshots[routing['developer']]['output_usd_per_token'] = '100'
    with pytest.raises(ValueError, match='snapshot'):
        ModelClient(UsageAPI({}), routing, prices, pricing_snapshots=snapshots)
