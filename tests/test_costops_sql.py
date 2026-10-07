"""Report delivery checks; behavioral warehouse tests are opt-in and read-only."""
import json
import os
from pathlib import Path
import re
import importlib.util
import time
from decimal import Decimal

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / 'docs/sql'
REPORTS = ['harness_costs_by_call', 'harness_endpoint_usage_join',
           'harness_costs_summary', 'harness_billing_reconciliation', 'harness_costops_quality']


@pytest.mark.parametrize('report', REPORTS)
def test_report_has_no_manual_dependencies_or_sensitive_outputs(report):
    text = (SQL / (report + '.sql')).read_text(encoding='utf-8')
    executable = re.sub(r'--[^\n]*', '', text)
    assert not re.search(r'\b(?:CREATE|INSERT|UPDATE|DELETE|MERGE|USE|DROP|ALTER|GRANT)\b', executable, re.I)
    assert not re.search(r':(?:runs_path|calls_path)\b', executable)
    assert not re.search(r'\bFROM\s+harness_costs_by_call\b', executable, re.I)
    assert 'input_text' not in executable and 'output_text' not in executable
    for key in ['fecha_desde', 'fecha_hasta', 'hu_id', 'run_id', 'attempt_id', 'model', 'call_id']:
        assert key in executable
    assert 'America/Bogota' in executable
    assert '/Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/artifacts/runs' in executable


def test_report_rates_follow_verified_runtime_configuration():
    from decimal import Decimal
    config = yaml.safe_load((ROOT / 'src/agents/harness/config/defaults/models.yaml').read_text(encoding='utf-8'))
    for report in REPORTS:
        text = (SQL / (report + '.sql')).read_text(encoding='utf-8')
        for endpoint, rates in config['pricing']['endpoints'].items():
            assert endpoint in text
            for field in ['input_usd_per_token', 'output_usd_per_token']:
                # Decimal, including config values parsed by YAML as floats.
                amount = format(Decimal(str(rates[field])), 'f')
                assert amount in text, (report, endpoint, field, amount)


def warehouse_query(sql, expected_failure=None, failure_case='inverted_date_range'):
    """Use the delivered SDK runner's explicit CLI profile authentication."""
    from databricks.sdk import WorkspaceClient
    spec = importlib.util.spec_from_file_location('costops_runner', SQL / 'run_costops.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    workspace = WorkspaceClient(profile='CREA_DEV', credentials_strategy=runner.cli_credentials)
    result = workspace.statement_execution.execute_statement(
        warehouse_id='9e696889dea65361', statement=sql, wait_timeout='50s')
    deadline = time.monotonic() + 600
    while result.status.state.value in {'PENDING', 'RUNNING'}:
        assert time.monotonic() < deadline, result.statement_id
        time.sleep(2)
        result = workspace.statement_execution.get_statement(result.statement_id)
    if expected_failure:
        assert result.status.state.value == 'FAILED', (result.statement_id, result.status.as_dict())
        assert expected_failure in json.dumps(result.status.as_dict()), result.status.as_dict()
        FIXTURE_EVIDENCE.append({'case': failure_case, 'statement_id': result.statement_id,
                                'query_state': 'EXPECTED_FAILED',
                                'error': result.status.error.message.split('\n\n== SQL ==')[0]})
        return [], result.statement_id
    assert result.status.state.value == 'SUCCEEDED', (result.statement_id, result.status.as_dict())
    columns = [column.name for column in result.manifest.schema.columns]
    data = list(result.result.data_array or []) if result.result else []
    next_chunk = result.result.next_chunk_index if result.result else None
    while next_chunk is not None:
        chunk = workspace.statement_execution.get_statement_result_chunk_n(result.statement_id, next_chunk)
        data.extend(chunk.data_array or [])
        next_chunk = chunk.next_chunk_index
    return [dict(zip(columns, row)) for row in data], result.statement_id


@pytest.mark.skipif(os.environ.get('COSTOPS_SQL_INTEGRATION') != '1',
                    reason='Opt-in read-only queries require CREA_DEV and harness warehouse')
@pytest.mark.parametrize('report', REPORTS)
def test_report_executes_directly_on_harness_warehouse(report):
    text = (SQL / (report + '.sql')).read_text(encoding='utf-8')
    rows, statement_id = warehouse_query(text)
    assert statement_id
    # An empty financial window is valid; no second report/view is required.
    assert isinstance(rows, list)


INTEGRATION = pytest.mark.skipif(os.environ.get('COSTOPS_SQL_INTEGRATION') != '1',
    reason='Opt-in synthetic SELECT fixtures require CREA_DEV and harness warehouse')
MODEL = 'databricks-claude-sonnet-5-5'
WORKSPACE = '7405606739630987'
FIXTURE_EVIDENCE = []
SCHEMAS = {
    'ENTITY': 'served_entity_id STRING, workspace_id STRING, endpoint_id STRING, endpoint_name STRING, entity_name STRING, change_time TIMESTAMP, endpoint_delete_time TIMESTAMP',
    'USAGE': 'workspace_id STRING, client_request_id STRING, databricks_request_id STRING, request_time TIMESTAMP, status_code INT, input_token_count BIGINT, output_token_count BIGINT, usage_context MAP<STRING,STRING>, served_entity_id STRING',
    'BILLING': 'record_id STRING, account_id STRING, workspace_id STRING, sku_name STRING, cloud STRING, usage_unit STRING, usage_quantity DECIMAL(38,18), usage_start_time TIMESTAMP, usage_end_time TIMESTAMP, usage_date DATE, record_type STRING, ingestion_date DATE, endpoint_id STRING, endpoint_name STRING, app_name STRING, warehouse_id STRING, job_id STRING',
    'PRICE': 'account_id STRING, sku_name STRING, cloud STRING, usage_unit STRING, currency_code STRING, price_start_time TIMESTAMP, price_end_time TIMESTAMP, list_price DECIMAL(38,18)',
}


def sql_literal(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "''") + "'"


def fixture_sql(report, calls, *, usage=(), entities=(), billing=(), prices=(), filters=None,
                dates=('2026-10-07', '2026-10-07'), runs=None):
    """Replace only marked input CTEs; execute the actual delivered calculations."""
    text = (SQL / (report + '.sql')).read_text(encoding='utf-8')
    inputs = {
        'RUN': [{'run_id': 'r', 'story_id': 'HU exact', 'state': 'completed',
                 'attempts': [{'attempt_id': 'a', 'state': 'completed'}], '_rescued_data': None}],
        'CALL': calls, 'USAGE': usage, 'ENTITY': entities, 'BILLING': billing, 'PRICE': prices,
    }
    if runs is not None:
        inputs['RUN'] = runs
    for kind, rows in inputs.items():
        pattern = rf'-- BEGIN {kind} SOURCE\n(.*?)-- END {kind} SOURCE'
        match = re.search(pattern, text, re.S)
        if not match:
            continue
        if kind in {'RUN', 'CALL'}:
            schema = re.search(r"schema => '([^']+)'", match.group(1)).group(1)
        else:
            schema = SCHEMAS[kind]
        values = ',\n'.join('(' + sql_literal(json.dumps(row)) + ')' for row in rows)
        if values:
            source = f"SELECT parsed.* FROM (SELECT from_json(value,{sql_literal(schema)},map('timeZone','UTC')) AS parsed FROM VALUES {values} AS fixture(value))"
        else:
            source = f"SELECT parsed.* FROM (SELECT from_json('{{}}',{sql_literal(schema)},map('timeZone','UTC')) AS parsed) WHERE false"
        replacement = f'-- BEGIN {kind} SOURCE\n{kind.lower()}_source AS (\n{source}\n),\n-- END {kind} SOURCE'
        text = re.sub(pattern, lambda _: replacement, text, flags=re.S)
    params = {'hu_id': '', 'run_id': '', 'attempt_id': '', 'model': '', 'call_id': ''}
    params.update(filters or {})
    select = f'SELECT DATE {sql_literal(dates[0])} AS fecha_desde, DATE {sql_literal(dates[1])} AS fecha_hasta, '
    select += ', '.join(f'{sql_literal(value)} AS {key}' for key, value in params.items())
    text = re.sub(r'WITH params AS \(.*?\), bounds AS',
                  lambda _: f'WITH params AS ({select}), bounds AS', text, count=1, flags=re.S)
    assert 'read_files(' not in text and 'FROM system.' not in text
    assert not re.search(r'\b(?:CREATE|INSERT|UPDATE|DELETE|MERGE|DROP)\b', re.sub(r'--[^\n]*', '', text), re.I)
    return text


def call(call_id='c', **changes):
    row = {'schema_version': 3, 'run_id': 'r', 'attempt_id': 'a', 'call_id': call_id,
           'story_id': 'HU exact', 'role': 'developer', 'stage': 'apply', 'model': MODEL,
           'status': 'complete', 'started_at': '2026-10-07T12:00:00Z',
           'completed_at': '2026-10-07T12:00:01Z', 'input_tokens': 100,
           'output_tokens': 20, 'estimated_cost_usd': '0.25', 'pricing_source': 'historical',
           'currency': 'USD', 'client_request_id': call_id, '_rescued_data': None}
    return {**row, **changes}


def request(request_id='p', call_id='c', **changes):
    row = {'workspace_id': WORKSPACE, 'client_request_id': call_id,
           'databricks_request_id': request_id, 'request_time': '2026-10-07T12:00:00Z',
           'status_code': 200, 'input_token_count': 100, 'output_token_count': 20,
           'usage_context': {'run_id': 'r', 'attempt_id': 'a', 'story_id': 'HU exact'},
           'served_entity_id': 'e'}
    return {**row, **changes}


def entity(entity_id='e', **changes):
    return {'served_entity_id': entity_id, 'workspace_id': WORKSPACE, 'endpoint_id': 'ep',
            'endpoint_name': MODEL, 'entity_name': MODEL, 'change_time': '2026-10-01T00:00:00Z',
            'endpoint_delete_time': None, **changes}


def fixture_query(name, sql):
    rows, statement_id = warehouse_query(sql)
    FIXTURE_EVIDENCE.append({'case': name, 'statement_id': statement_id,
                             'query_state': 'SUCCEEDED', 'rows': rows})
    return rows


@pytest.fixture(scope='session', autouse=True)
def save_fixture_evidence():
    yield
    if FIXTURE_EVIDENCE:
        destination = ROOT / 'docs/evidence/2026-10-07-costops/sql-fixtures.json'
        prior = json.loads(destination.read_text(encoding='utf-8'))['statements'] if destination.exists() else []
        by_case = {item['case']: item for item in [*prior, *FIXTURE_EVIDENCE]}
        destination.write_text(json.dumps({'profile': 'CREA_DEV', 'warehouse_id': '9e696889dea65361',
            'scope': 'SELECT-only synthetic fixtures; no persistent objects or LLM calls',
            'statements': list(by_case.values())}, ensure_ascii=False, indent=2), encoding='utf-8')


@INTEGRATION
def test_three_physical_requests_and_identical_duplicates_preserve_logical_cost():
    physical = [request('p1'), request('p2'), request('p3'), request('p3')]
    rows = fixture_query('three_requests_and_duplicate', fixture_sql(
        'harness_endpoint_usage_join', [call(input_tokens=1000, output_tokens=200)] * 2,
        usage=physical, entities=[entity()]))
    assert len(rows) == 1
    row = rows[0]
    assert int(row['request_count']) == 3
    assert int(row['physical_input_tokens_known']) == 300
    assert Decimal(row['estimated_cost_usd']) == Decimal('.25')
    assert Decimal(row['costo_reestimado_tarifa_revisada']) == Decimal('0.005999952')
    assert row['reconciliation_state'] == 'multiple'


@INTEGRATION
def test_summary_preserves_unknown_cost_and_partial_token_coverage():
    rows = fixture_query('unknown_usage_partial_summary', fixture_sql('harness_costs_summary',
        [call(), call('unknown', input_tokens=None, output_tokens=None, estimated_cost_usd=None)],
        usage=[request()], entities=[entity()]))
    assert len(rows) == 1
    row = rows[0]
    assert int(row['calls_total']) == 2
    assert int(row['calls_with_historical_cost']) == 1
    assert int(row['calls_with_input_tokens']) == 1
    assert Decimal(row['historical_cost_known_usd']) == Decimal('.25')
    assert row['historical_cost_coverage'] == 'partial'
    assert row['revised_cost_coverage'] == 'partial'


@INTEGRATION
def test_logical_and_physical_conflicts_do_not_select_arbitrary_values():
    calls = [call('logical'), call('logical', estimated_cost_usd='.75'), call('physical')]
    usage = [request('same', 'physical'), request('same', 'physical', input_token_count=999)]
    rows = fixture_query('logical_and_physical_conflicts', fixture_sql(
        'harness_endpoint_usage_join', calls, usage=usage, entities=[entity()]))
    keyed = {row['call_id']: row for row in rows}
    assert len(keyed) == 2
    assert keyed['logical']['logical_state'] == 'conflict'
    assert keyed['logical']['estimated_cost_usd'] is None
    assert keyed['logical']['input_tokens'] is None
    assert keyed['physical']['reconciliation_state'] == 'conflict'
    assert int(keyed['physical']['request_count']) == 0
    assert keyed['physical']['physical_input_tokens_known'] is None


@INTEGRATION
def test_context_model_mismatches_and_absent_entity_dimension():
    calls = [call('context'), call('model'), call('no_entity')]
    usage = [request('p1', 'context', usage_context={'attempt_id': 'other'}),
             request('p2', 'model', served_entity_id='other-model'),
             request('p3', 'no_entity', served_entity_id='absent')]
    rows = fixture_query('context_model_and_missing_dimension', fixture_sql(
        'harness_endpoint_usage_join', calls, usage=usage,
        entities=[entity(), entity('other-model', entity_name='databricks-claude-haiku-4-5')]))
    keyed = {row['call_id']: row for row in rows}
    for name in ('context', 'model'):
        assert int(keyed[name]['request_count']) == 0
        assert keyed[name]['reconciliation_state'] == 'missing'
    assert int(keyed['no_entity']['request_count']) == 1
    assert int(keyed['no_entity']['requests_with_unverified_model']) == 1
    rows = fixture_query('entire_entity_dimension_empty', fixture_sql(
        'harness_endpoint_usage_join', [call()], usage=[request()], entities=[]))
    assert int(rows[0]['request_count']) == 1
    assert int(rows[0]['requests_with_unverified_model']) == 1


@INTEGRATION
def test_exact_filters_and_inclusive_bogota_midnight_boundaries():
    calls = [call('before', started_at='2026-10-07T04:59:59Z'),
             call('start', started_at='2026-10-07T05:00:00Z'),
             call('last', started_at='2026-10-08T04:59:59Z'),
             call('after', started_at='2026-10-08T05:00:00Z'),
             call('wrong-hu', story_id='HU exact additional'), call('wrong-run', run_id='r-extra')]
    rows = fixture_query('bogota_boundaries_exact_filters', fixture_sql(
        'harness_costs_by_call', calls, filters={'hu_id': 'HU exact', 'run_id': 'r'}))
    assert {row['call_id'] for row in rows} == {'start', 'last'}
    rows = fixture_query('combined_filters_intersection', fixture_sql(
        'harness_costs_by_call', calls, filters={'hu_id': 'HU exact additional', 'run_id': 'r-extra'}))
    assert rows == []


def billing_row(record_id='b', sku='priced', quantity='10', **changes):
    return {'record_id': record_id, 'account_id': 'account', 'workspace_id': WORKSPACE,
        'sku_name': sku, 'cloud': 'AZURE', 'usage_unit': 'DBU', 'usage_quantity': quantity,
        'usage_start_time': '2026-10-07T12:00:00Z', 'usage_end_time': '2026-10-07T13:00:00Z',
        'usage_date': '2026-10-07', 'record_type': 'ORIGINAL', 'ingestion_date': '2026-10-08',
        'warehouse_id': '9e696889dea65361', **changes}


def price(sku='priced', **changes):
    return {'account_id': 'account', 'sku_name': sku, 'cloud': 'AZURE', 'usage_unit': 'DBU',
        'currency_code': 'USD', 'price_start_time': '2026-10-01T00:00:00Z',
        'price_end_time': None, 'list_price': '.105', **changes}


@INTEGRATION
def test_billing_adjustments_missing_ambiguous_and_crossing_prices():
    billing = [billing_row(), billing_row('retract', quantity='-10', record_type='RETRACTION'),
        billing_row('restate', quantity='12', record_type='RESTATEMENT'),
        billing_row('missing', 'missing'), billing_row('ambiguous', 'ambiguous'),
        billing_row('crossing', 'crossing'),
        billing_row('fractional', 'fractional', quantity='0.123456789012345678')]
    prices = [price(), price('ambiguous'), price('ambiguous', list_price='.2'),
        price('crossing', price_end_time='2026-10-07T12:30:00Z'), price('fractional')]
    rows = fixture_query('billing_net_and_price_diagnostics', fixture_sql(
        'harness_billing_reconciliation', [], billing=billing, prices=prices))
    keyed = {row['sku_name']: row for row in rows}
    assert Decimal(keyed['priced']['net_usage_quantity']) == Decimal('12')
    assert Decimal(keyed['priced']['list_cost_known_usd']) == Decimal('1.26')
    assert int(keyed['priced']['billing_records']) == 3
    assert keyed['priced']['monetary_coverage'] == 'complete'
    assert Decimal(keyed['fractional']['list_cost_known_usd']) == Decimal('0.01296296284629629619')
    for sku, diagnosis in [('missing', 'missing_price'), ('ambiguous', 'ambiguous_or_crossing_price'),
                           ('crossing', 'crossing_price_boundary')]:
        assert keyed[sku]['list_cost_known_usd'] is None
        assert keyed[sku]['monetary_coverage'] == 'partial'
        assert diagnosis in keyed[sku]['price_diagnostics']


@INTEGRATION
def test_shared_request_id_has_no_arbitrary_logical_owner():
    rows = fixture_query('ambiguous_logical_owners', fixture_sql(
        'harness_endpoint_usage_join', [call('owner1', client_request_id='shared'),
                                       call('owner2', client_request_id='shared')],
        usage=[request('p', 'shared')], entities=[entity()]))
    assert len(rows) == 2
    for row in rows:
        assert row['reconciliation_state'] == 'conflict'
        assert int(row['request_count']) == 0
        assert row['physical_input_tokens_known'] is None
        assert Decimal(row['estimated_cost_usd']) == Decimal('.25')


@INTEGRATION
def test_negative_financial_values_are_unknown_instead_of_subtracting_cost():
    rows = fixture_query('negative_tokens_and_cost', fixture_sql('harness_endpoint_usage_join',
        [call(input_tokens=-10, output_tokens=-5, estimated_cost_usd='-.25')],
        usage=[request(input_token_count=-10, output_token_count=-5)], entities=[entity()]))
    row = rows[0]
    assert row['input_tokens'] is None and row['output_tokens'] is None
    assert row['estimated_cost_usd'] is None
    assert row['costo_reestimado_tarifa_revisada'] is None
    assert row['physical_input_tokens_known'] is None
    assert row['physical_output_tokens_known'] is None
    assert row['physical_token_coverage'] == 'incomplete'


@INTEGRATION
def test_inverted_date_range_fails_instead_of_silently_returning_zero():
    for name, calls in [('inverted_date_range', [call()]), ('inverted_range_empty_source', [])]:
        warehouse_query(fixture_sql('harness_costs_by_call', calls,
            dates=('2026-10-08', '2026-10-07')), expected_failure='CostOps: fecha_desde/fecha_hasta',
            failure_case=name)


@INTEGRATION
def test_quality_missing_keys_orphans_rescued_fields_and_unknown_time_filters():
    calls = [call(), call(None), call('orphan', run_id='missing-run'),
             call('rescued', _rescued_data='{"input_tokens":"bad"}'),
             call('unknown-time', started_at=None),
             call('other-hu-time', started_at=None, story_id='different-HU')]
    runs = [{'run_id': 'r', 'story_id': 'HU exact', 'state': 'completed',
             'attempts': [{'attempt_id': 'a', 'state': 'completed'}], '_rescued_data': '{"unexpected":true}'}]
    rows = fixture_query('quality_keys_orphans_rescued_unknown_time', fixture_sql(
        'harness_costops_quality', calls, runs=runs, filters={'hu_id': 'HU exact'}))
    counts = {row['check_name']: int(row['affected_rows'] or 0) for row in rows}
    assert counts['missing_logical_key'] == 1
    assert counts['orphan_or_conflicting_run_attempt'] == 1
    assert counts['rescued_call_fields_review_required'] == 1
    assert counts['rescued_run_fields_review_required'] == 1
    assert counts['unknown_time_selected_ids_date_unverifiable'] == 1
