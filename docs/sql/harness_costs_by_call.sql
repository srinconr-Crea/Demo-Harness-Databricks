-- Solo lectura. Cambie únicamente params; fechas inclusivas en America/Bogota.
-- Instalación: workspace 7405606739630987; warehouse 9e696889dea65361.
WITH params AS (
  SELECT date_sub(to_date(convert_timezone(current_timezone(), 'America/Bogota', CAST(current_timestamp() AS TIMESTAMP_NTZ))), 6) AS fecha_desde,
         to_date(convert_timezone(current_timezone(), 'America/Bogota', CAST(current_timestamp() AS TIMESTAMP_NTZ))) AS fecha_hasta,
         '' AS hu_id, '' AS run_id, '' AS attempt_id, '' AS model, '' AS call_id
), bounds AS (
  SELECT *, make_timestamp(year(fecha_desde), month(fecha_desde), day(fecha_desde), 0, 0, 0, 'America/Bogota') AS inicio_utc,
    make_timestamp(year(date_add(fecha_hasta,1)), month(date_add(fecha_hasta,1)), day(date_add(fecha_hasta,1)), 0, 0, 0, 'America/Bogota') AS fin_utc,
    CASE WHEN fecha_desde IS NULL OR fecha_hasta IS NULL OR fecha_desde > fecha_hasta
         THEN raise_error('CostOps: fecha_desde/fecha_hasta deben formar un rango válido') ELSE true END AS valid_range
  FROM params
),
-- BEGIN RUN SOURCE
run_source AS (
  SELECT * FROM read_files('/Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/artifacts/runs/*.json',
    format => 'json', multiLine => true, timeZone => 'UTC', rescuedDataColumn => '_rescued_data',
    schema => 'run_id STRING, story_id STRING, state STRING, attempts ARRAY<STRUCT<attempt_id:STRING,state:STRING>>, _rescued_data STRING')
),
-- END RUN SOURCE
-- BEGIN CALL SOURCE
call_source AS (
  SELECT * FROM read_files('/Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/artifacts/runs/agent_calls/*.json',
    format => 'json', multiLine => true, timeZone => 'UTC', rescuedDataColumn => '_rescued_data',
    schema => 'schema_version INT, run_id STRING, attempt_id STRING, call_id STRING, story_id STRING, role STRING, stage STRING, model STRING, status STRING, acceptance STRING, started_at TIMESTAMP, completed_at TIMESTAMP, input_tokens BIGINT, output_tokens BIGINT, estimated_cost_usd DECIMAL(38,18), pricing_source STRING, currency STRING, client_request_id STRING, databricks_request_id STRING, pricing_snapshot STRUCT<version:STRING,currency:STRING,checked_at:STRING,effective_from:STRING,source:STRING,sku:STRING,input_usd_per_token:DECIMAL(38,18),output_usd_per_token:DECIMAL(38,18),usd_per_dbu:DECIMAL(38,18),input_dbu_per_million:DECIMAL(38,18),output_dbu_per_million:DECIMAL(38,18),limitations:STRING>, _rescued_data STRING')
),
-- END CALL SOURCE
run_rows AS (
  SELECT DISTINCT run_id, story_id, state, attempts FROM run_source WHERE run_id IS NOT NULL
), run_keys AS (
  SELECT run_id, count(*) AS run_variants FROM run_rows GROUP BY run_id
), run_one AS (
  SELECT r.* FROM run_rows r JOIN run_keys k USING(run_id) WHERE k.run_variants = 1
), attempt_rows AS (
  SELECT r.run_id, a.attempt_id, a.state AS attempt_state FROM run_one r
  LATERAL VIEW explode(r.attempts) e AS a
), attempt_keys AS (
  SELECT run_id, attempt_id, count(*) AS attempt_variants FROM attempt_rows GROUP BY run_id, attempt_id
), attempt_one AS (
  SELECT a.* FROM attempt_rows a JOIN attempt_keys k USING(run_id,attempt_id) WHERE k.attempt_variants = 1
), call_rows AS (
  SELECT DISTINCT schema_version, run_id, attempt_id, call_id, story_id, role, stage, model, status, acceptance,
    started_at, completed_at, input_tokens, output_tokens, estimated_cost_usd, pricing_source, currency,
    client_request_id, databricks_request_id, pricing_snapshot, (_rescued_data IS NOT NULL) AS rescued_contract FROM call_source
), call_keys AS (
  SELECT run_id, attempt_id, call_id, count(*) AS call_variants FROM call_rows GROUP BY run_id,attempt_id,call_id
), tariffs AS (
  SELECT * FROM VALUES
    ('databricks-claude-sonnet-5-5', CAST(0.000002999955 AS DECIMAL(15,12)), CAST(0.000014999985 AS DECIMAL(15,12))),
    ('databricks-claude-haiku-4-5', CAST(0.000001500030 AS DECIMAL(15,12)), CAST(0.000007500045 AS DECIMAL(15,12)))
    AS t(model, input_per_token, output_per_token)
), calls AS (
  SELECT c.*, k.call_variants, r.state AS run_state, a.attempt_state,
    CASE WHEN k.call_variants > 1 THEN 'conflict'
         WHEN c.run_id IS NULL OR c.attempt_id IS NULL OR c.call_id IS NULL THEN 'missing_key'
         ELSE 'unique' END AS logical_state,
    CASE WHEN r.run_id IS NULL THEN 'orphan_or_conflicting_run'
         WHEN a.attempt_id IS NULL THEN 'missing_or_conflicting_attempt' ELSE 'matched' END AS history_state,
    CASE WHEN k.call_variants = 1 AND c.run_id IS NOT NULL AND c.attempt_id IS NOT NULL AND c.call_id IS NOT NULL
              AND c.input_tokens >= 0 AND c.output_tokens >= 0
         THEN c.input_tokens*t.input_per_token + c.output_tokens*t.output_per_token END AS costo_reestimado_tarifa_revisada,
    'harness-costops-2026-10-07' AS revised_pricing_version,
    'cache_components_not_observed; estimate_not_invoice' AS pricing_limitation
  FROM call_rows c JOIN call_keys k ON c.run_id <=> k.run_id AND c.attempt_id <=> k.attempt_id AND c.call_id <=> k.call_id
  LEFT JOIN run_one r ON c.run_id = r.run_id
  LEFT JOIN attempt_one a ON c.run_id = a.run_id AND c.attempt_id = a.attempt_id
  LEFT JOIN tariffs t ON c.model = t.model CROSS JOIN bounds p
  WHERE p.valid_range AND (c.started_at >= p.inicio_utc AND c.started_at < p.fin_utc )
    AND (p.hu_id = '' OR c.story_id = p.hu_id) AND (p.run_id = '' OR c.run_id = p.run_id)
    AND (p.attempt_id = '' OR c.attempt_id = p.attempt_id) AND (p.model = '' OR c.model = p.model)
    AND (p.call_id = '' OR c.call_id = p.call_id)
) , normalized_calls AS (
  SELECT run_id,attempt_id,call_id,
    CASE WHEN max(call_variants)=1 THEN max(schema_version) END AS schema_version,
    CASE WHEN max(call_variants)=1 THEN max(story_id) END AS story_id,
    CASE WHEN max(call_variants)=1 THEN max(role) END AS role,
    CASE WHEN max(call_variants)=1 THEN max(stage) END AS stage,
    CASE WHEN max(call_variants)=1 THEN max(model) END AS model,
    CASE WHEN max(call_variants)=1 THEN max(status) END AS status,
    CASE WHEN max(call_variants)=1 THEN max(acceptance) END AS acceptance,
    CASE WHEN max(call_variants)=1 THEN max(started_at) END AS started_at,
    CASE WHEN max(call_variants)=1 THEN max(completed_at) END AS completed_at,
    CASE WHEN max(call_variants)=1 AND max(input_tokens)>=0 THEN max(input_tokens) END AS input_tokens,
    CASE WHEN max(call_variants)=1 AND max(output_tokens)>=0 THEN max(output_tokens) END AS output_tokens,
    CASE WHEN max(call_variants)=1 AND max(estimated_cost_usd)>=0 THEN max(estimated_cost_usd) END AS estimated_cost_usd,
    CASE WHEN max(call_variants)=1 THEN max(pricing_source) END AS pricing_source,
    CASE WHEN max(call_variants)=1 THEN max(currency) END AS currency,
    CASE WHEN max(call_variants)=1 THEN max(client_request_id) END AS client_request_id,
    CASE WHEN max(call_variants)=1 THEN max(databricks_request_id) END AS databricks_request_id,
    CASE WHEN max(call_variants)=1 THEN max(pricing_snapshot) END AS pricing_snapshot,
    max(rescued_contract) AS rescued_contract,max(call_variants) AS call_variants,
    CASE WHEN max(call_variants)=1 THEN max(run_state) END AS run_state,
    CASE WHEN max(call_variants)=1 THEN max(attempt_state) END AS attempt_state,
    CASE WHEN max(call_variants)=1 THEN max(history_state) ELSE 'conflicting_call' END AS history_state,
    CASE WHEN max(call_variants)>1 THEN 'conflict' ELSE max(logical_state) END AS logical_state,
    CASE WHEN max(call_variants)=1 THEN max(costo_reestimado_tarifa_revisada) END AS costo_reestimado_tarifa_revisada,
    max(revised_pricing_version) AS revised_pricing_version,max(pricing_limitation) AS pricing_limitation
  FROM calls GROUP BY run_id,attempt_id,call_id
), logical_calls AS (
  SELECT * FROM normalized_calls
), costops_result AS (
SELECT story_id AS hu_id, run_id, attempt_id, call_id, role, stage, model, status, acceptance,
  run_state,attempt_state,history_state,logical_state,started_at AS started_at_utc,
  convert_timezone(current_timezone(),'America/Bogota',CAST(started_at AS TIMESTAMP_NTZ)) AS started_at_bogota,
  input_tokens,output_tokens,estimated_cost_usd AS costo_historico_estimado_usd,
  pricing_source,pricing_snapshot,costo_reestimado_tarifa_revisada,revised_pricing_version,pricing_limitation,
  client_request_id,databricks_request_id,
  CASE WHEN input_tokens IS NULL OR output_tokens IS NULL THEN 'missing' ELSE 'endpoint_reported' END AS token_source
FROM logical_calls
), costops_result_marker AS (
  SELECT *,true AS _costops_has_row FROM costops_result
)
SELECT r.* EXCEPT(_costops_has_row)
FROM bounds p LEFT JOIN costops_result_marker r ON true
WHERE CASE WHEN p.fecha_desde IS NULL OR p.fecha_hasta IS NULL OR p.fecha_desde>p.fecha_hasta
  THEN raise_error('CostOps: fecha_desde/fecha_hasta deben formar un rango valido')
  ELSE coalesce(r._costops_has_row,false) END

ORDER BY r.started_at_utc,r.run_id,r.attempt_id,r.call_id;
