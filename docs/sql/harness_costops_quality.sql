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
)
,
-- BEGIN ENTITY SOURCE
entity_source AS (
  SELECT served_entity_id, workspace_id, endpoint_id, endpoint_name, entity_name, change_time, endpoint_delete_time
  FROM system.serving.served_entities WHERE workspace_id = '7405606739630987'
),
-- END ENTITY SOURCE
-- BEGIN USAGE SOURCE
usage_source AS (
  SELECT workspace_id, client_request_id, databricks_request_id, request_time, status_code,
    input_token_count, output_token_count, usage_context, served_entity_id
  FROM system.serving.endpoint_usage CROSS JOIN bounds p
  WHERE workspace_id = '7405606739630987' AND request_time >= p.inicio_utc AND request_time < p.fin_utc AND p.valid_range
),
-- END USAGE SOURCE
logical_client_keys AS (
  SELECT client_request_id,count(*) AS logical_owners FROM logical_calls
  WHERE logical_state='unique' AND client_request_id IS NOT NULL GROUP BY client_request_id
), physical_rows AS (
  SELECT DISTINCT workspace_id, client_request_id, databricks_request_id, request_time, status_code,
    input_token_count, output_token_count, to_json(map_from_entries(array_sort(map_entries(usage_context)))) AS context_json, served_entity_id FROM usage_source
), physical_keys AS (
  SELECT workspace_id, databricks_request_id, count(*) AS physical_variants FROM physical_rows
  GROUP BY workspace_id,databricks_request_id
), physical_one AS (
  SELECT u.*, k.physical_variants FROM physical_rows u JOIN physical_keys k
    ON u.workspace_id = k.workspace_id AND u.databricks_request_id <=> k.databricks_request_id
  WHERE k.physical_variants = 1 AND u.databricks_request_id IS NOT NULL
), entity_matches AS (
  SELECT u.workspace_id, u.databricks_request_id, count(e.served_entity_id) AS entity_matches,
    CASE WHEN count(e.served_entity_id)=1 THEN max(e.entity_name) END AS entity_model,
    CASE WHEN count(e.served_entity_id)=1 THEN max(e.endpoint_id) END AS endpoint_id,
    CASE WHEN count(e.served_entity_id)=1 THEN max(e.endpoint_name) END AS endpoint_name
  FROM physical_one u LEFT JOIN entity_source e ON u.served_entity_id = e.served_entity_id
    AND u.workspace_id = e.workspace_id AND u.request_time >= e.change_time
    AND (e.endpoint_delete_time IS NULL OR u.request_time < e.endpoint_delete_time)
  GROUP BY u.workspace_id,u.databricks_request_id
), compatible_requests AS (
  SELECT c.run_id,c.attempt_id,c.call_id,u.*, e.entity_matches,e.entity_model,e.endpoint_id,e.endpoint_name,
    CASE WHEN e.entity_matches=0 THEN 'model_unverified_missing_dimension' ELSE 'model_verified' END AS model_evidence
  FROM logical_calls c JOIN physical_one u ON c.client_request_id = u.client_request_id
  JOIN logical_client_keys owners ON c.client_request_id=owners.client_request_id AND owners.logical_owners=1
  JOIN entity_matches e ON u.workspace_id=e.workspace_id AND u.databricks_request_id=e.databricks_request_id
  WHERE c.logical_state='unique' AND (get_json_object(u.context_json,'$.run_id') IS NULL OR get_json_object(u.context_json,'$.run_id')=c.run_id)
    AND (get_json_object(u.context_json,'$.attempt_id') IS NULL OR get_json_object(u.context_json,'$.attempt_id')=c.attempt_id)
    AND (get_json_object(u.context_json,'$.story_id') IS NULL OR get_json_object(u.context_json,'$.story_id')=c.story_id)
    AND e.entity_matches <= 1 AND (e.entity_matches=0 OR e.entity_model=c.model)
), request_totals AS (
  SELECT run_id,attempt_id,call_id,count(*) AS request_count,
    count(CASE WHEN input_token_count>=0 THEN input_token_count END) AS requests_with_input_tokens,count(CASE WHEN output_token_count>=0 THEN output_token_count END) AS requests_with_output_tokens,
    sum(CASE WHEN input_token_count>=0 THEN input_token_count END) AS physical_input_tokens_known,sum(CASE WHEN output_token_count>=0 THEN output_token_count END) AS physical_output_tokens_known,
    collect_set(databricks_request_id) AS physical_request_ids,collect_set(status_code) AS physical_status_codes,
    count_if(entity_matches=0) AS requests_with_unverified_model
  FROM compatible_requests GROUP BY run_id,attempt_id,call_id
), conflicted_matches AS (
  SELECT DISTINCT c.run_id,c.attempt_id,c.call_id FROM logical_calls c JOIN physical_rows u
    ON c.client_request_id=u.client_request_id JOIN physical_keys k
    ON u.workspace_id=k.workspace_id AND u.databricks_request_id <=> k.databricks_request_id
    WHERE k.physical_variants > 1 OR u.databricks_request_id IS NULL
  UNION SELECT c.run_id,c.attempt_id,c.call_id FROM logical_calls c JOIN logical_client_keys k
    ON c.client_request_id=k.client_request_id WHERE k.logical_owners>1
), reconciled AS (
  SELECT c.*, coalesce(t.request_count,0) AS request_count,t.requests_with_input_tokens,t.requests_with_output_tokens,
    t.physical_input_tokens_known,t.physical_output_tokens_known,t.physical_request_ids,t.physical_status_codes,
    t.requests_with_unverified_model,
    CASE WHEN c.logical_state<>'unique' OR x.call_id IS NOT NULL THEN 'conflict' WHEN t.request_count IS NULL THEN 'missing'
         WHEN t.request_count=1 THEN 'single' ELSE 'multiple' END AS reconciliation_state,
    CASE WHEN t.requests_with_input_tokens=t.request_count AND t.requests_with_output_tokens=t.request_count
         THEN 'complete' ELSE 'incomplete' END AS physical_token_coverage
  FROM logical_calls c LEFT JOIN request_totals t USING(run_id,attempt_id,call_id)
  LEFT JOIN conflicted_matches x USING(run_id,attempt_id,call_id)
)
,
selected_days AS (
  SELECT DISTINCT endpoint_id,endpoint_name,to_date(convert_timezone(current_timezone(),'America/Bogota',CAST(request_time AS TIMESTAMP_NTZ))) AS local_day
  FROM compatible_requests WHERE endpoint_id IS NOT NULL OR endpoint_name IS NOT NULL
),
-- BEGIN BILLING SOURCE
billing_source AS (
  SELECT record_id,account_id,workspace_id,sku_name,cloud,usage_unit,usage_quantity,
    usage_start_time,usage_end_time,usage_date,record_type,ingestion_date,
    usage_metadata.endpoint_id AS endpoint_id,usage_metadata.endpoint_name AS endpoint_name,
    usage_metadata.app_name AS app_name,usage_metadata.warehouse_id AS warehouse_id,usage_metadata.job_id AS job_id
  FROM system.billing.usage CROSS JOIN bounds p
  WHERE workspace_id='7405606739630987' AND usage_end_time > p.inicio_utc AND usage_start_time < p.fin_utc AND p.valid_range
),
-- END BILLING SOURCE
-- BEGIN PRICE SOURCE
price_source AS (
  SELECT account_id,sku_name,cloud,usage_unit,currency_code,price_start_time,price_end_time,
    CAST(pricing.effective_list.default AS DECIMAL(38,18)) AS list_price
  FROM system.billing.list_prices WHERE currency_code='USD'
),
-- END PRICE SOURCE
billing_selected AS (
  SELECT b.*,CASE WHEN b.app_name='demo-dbx-harness-mvp' THEN 'app'
    WHEN b.warehouse_id='9e696889dea65361' THEN 'sql_warehouse'
    WHEN b.job_id='611081415041874' THEN 'sandbox_job' ELSE 'inference' END AS component,
    CASE WHEN p.hu_id<>'' OR p.run_id<>'' OR p.attempt_id<>'' OR p.model<>'' OR p.call_id<>''
         THEN 'endpoint_period_shared' ELSE 'harness_resources_and_endpoint_period_shared' END AS attribution_scope
  FROM billing_source b CROSS JOIN bounds p WHERE
    ((p.hu_id='' AND p.run_id='' AND p.attempt_id='' AND p.model='' AND p.call_id='') AND
      (b.app_name='demo-dbx-harness-mvp' OR b.warehouse_id='9e696889dea65361' OR b.job_id='611081415041874'))
    OR EXISTS (SELECT 1 FROM selected_days d WHERE
      ((d.endpoint_id IS NOT NULL AND b.endpoint_id=d.endpoint_id) OR (d.endpoint_name IS NOT NULL AND b.endpoint_name=d.endpoint_name))
      AND b.usage_end_time>make_timestamp(year(d.local_day),month(d.local_day),day(d.local_day),0,0,0,'America/Bogota')
      AND b.usage_start_time<make_timestamp(year(date_add(d.local_day,1)),month(date_add(d.local_day,1)),day(date_add(d.local_day,1)),0,0,0,'America/Bogota'))
), billing_distinct AS (
  SELECT DISTINCT * FROM billing_selected
), billing_rows AS (
  SELECT record_id, count(*) AS record_variants,
    CASE WHEN count(*)=1 THEN max(account_id) END AS account_id,
    CASE WHEN count(*)=1 THEN max(workspace_id) END AS workspace_id,
    CASE WHEN count(*)=1 THEN max(sku_name) END AS sku_name,
    CASE WHEN count(*)=1 THEN max(cloud) END AS cloud,
    CASE WHEN count(*)=1 THEN max(usage_unit) END AS usage_unit,
    CASE WHEN count(*)=1 THEN max(usage_quantity) END AS usage_quantity,
    CASE WHEN count(*)=1 THEN max(usage_start_time) END AS usage_start_time,
    CASE WHEN count(*)=1 THEN max(usage_end_time) END AS usage_end_time,
    CASE WHEN count(*)=1 THEN max(usage_date) END AS usage_date,
    CASE WHEN count(*)=1 THEN max(record_type) END AS record_type,
    CASE WHEN count(*)=1 THEN max(ingestion_date) END AS ingestion_date,
    CASE WHEN count(*)=1 THEN max(endpoint_id) END AS endpoint_id,
    CASE WHEN count(*)=1 THEN max(endpoint_name) END AS endpoint_name,
    CASE WHEN count(*)=1 THEN max(app_name) END AS app_name,
    CASE WHEN count(*)=1 THEN max(warehouse_id) END AS warehouse_id,
    CASE WHEN count(*)=1 THEN max(job_id) END AS job_id,
    CASE WHEN count(*)=1 THEN max(component) END AS component,
    CASE WHEN count(*)=1 THEN max(attribution_scope) END AS attribution_scope
  FROM billing_distinct GROUP BY record_id
), price_matches AS (
  SELECT b.record_id,count(p.sku_name) AS price_matches,
    count_if(p.price_start_time<=b.usage_start_time AND (p.price_end_time IS NULL OR p.price_end_time>=b.usage_end_time)) AS full_price_matches,
    CASE WHEN count(p.sku_name)=1 THEN max(p.list_price) END AS list_price
  FROM billing_rows b LEFT JOIN price_source p ON b.account_id=p.account_id AND b.sku_name=p.sku_name
    AND b.cloud=p.cloud AND b.usage_unit=p.usage_unit AND p.currency_code='USD'
    AND p.price_start_time<b.usage_end_time AND (p.price_end_time IS NULL OR p.price_end_time>b.usage_start_time)
  GROUP BY b.record_id
), billed AS (
  SELECT b.*,m.price_matches,m.full_price_matches,m.list_price,
    CASE WHEN b.record_variants>1 OR b.record_id IS NULL THEN 'conflicting_or_missing_record_id' WHEN m.price_matches=0 THEN 'missing_price' WHEN m.price_matches>1 THEN 'ambiguous_or_crossing_price'
      WHEN m.full_price_matches<>1 THEN 'crossing_price_boundary' WHEN m.list_price IS NULL THEN 'missing_price_value'
      WHEN try_cast(b.usage_quantity AS DECIMAL(27,18)) IS NULL
        OR try_cast(b.usage_quantity AS DECIMAL(27,18))<>b.usage_quantity
        OR try_cast(m.list_price AS DECIMAL(10,6)) IS NULL
        OR try_cast(m.list_price AS DECIMAL(10,6))<>m.list_price OR m.list_price<0 THEN 'invalid_decimal_precision'
      ELSE 'unique' END AS price_state,
    CASE WHEN b.record_variants=1 AND b.record_id IS NOT NULL AND m.price_matches=1 AND m.full_price_matches=1
      AND try_cast(b.usage_quantity AS DECIMAL(27,18))=b.usage_quantity
      AND try_cast(m.list_price AS DECIMAL(10,6))=m.list_price AND m.list_price>=0
      THEN try_cast(b.usage_quantity AS DECIMAL(27,18))*try_cast(m.list_price AS DECIMAL(10,6)) END AS list_cost_usd
  FROM billing_rows b LEFT JOIN price_matches m USING(record_id)
), call_billing_coverage AS (
  SELECT r.run_id,r.attempt_id,r.call_id,max(b.usage_end_time) AS billing_end_utc
  FROM compatible_requests r LEFT JOIN billed b ON b.component='inference' AND
    ((r.endpoint_id IS NOT NULL AND r.endpoint_id=b.endpoint_id) OR
     (r.endpoint_name IS NOT NULL AND r.endpoint_name=b.endpoint_name))
  GROUP BY r.run_id,r.attempt_id,r.call_id
), costops_result AS (
SELECT 'logical_identical_extra_rows' AS check_name,(SELECT count(*) FROM call_source s CROSS JOIN bounds p WHERE s.started_at>=p.inicio_utc AND s.started_at<p.fin_utc
  AND (p.hu_id='' OR s.story_id=p.hu_id) AND (p.run_id='' OR s.run_id=p.run_id)
  AND (p.attempt_id='' OR s.attempt_id=p.attempt_id) AND (p.model='' OR s.model=p.model) AND (p.call_id='' OR s.call_id=p.call_id) AND
  EXISTS(SELECT 1 FROM calls c WHERE c.run_id <=> s.run_id AND c.attempt_id <=> s.attempt_id AND c.call_id <=> s.call_id))-(SELECT count(*) FROM calls) AS affected_rows
UNION ALL SELECT 'physical_identical_extra_rows',(SELECT count(*) FROM usage_source)-(SELECT count(*) FROM physical_rows)
UNION ALL SELECT 'rescued_run_fields_review_required',count_if(r._rescued_data IS NOT NULL) FROM run_source r WHERE EXISTS(SELECT 1 FROM calls c WHERE c.run_id=r.run_id)
UNION ALL SELECT 'logical_conflict_variants',count_if(logical_state='conflict') FROM calls
UNION ALL SELECT 'missing_logical_key',count_if(logical_state='missing_key') FROM calls
UNION ALL SELECT 'unknown_time_selected_ids_date_unverifiable',count(*) FROM call_rows c CROSS JOIN bounds p
  WHERE c.started_at IS NULL AND (p.hu_id='' OR c.story_id=p.hu_id) AND (p.run_id='' OR c.run_id=p.run_id)
    AND (p.attempt_id='' OR c.attempt_id=p.attempt_id) AND (p.model='' OR c.model=p.model) AND (p.call_id='' OR c.call_id=p.call_id)
UNION ALL SELECT 'orphan_or_conflicting_run_attempt',count_if(history_state<>'matched') FROM calls
UNION ALL SELECT 'rescued_call_fields_review_required',count_if(rescued_contract) FROM calls
UNION ALL SELECT 'missing_tokens',count_if(input_tokens IS NULL OR output_tokens IS NULL) FROM logical_calls
UNION ALL SELECT 'missing_cost',count_if(estimated_cost_usd IS NULL) FROM logical_calls
UNION ALL SELECT 'missing_pricing_snapshot_legacy',count_if(pricing_snapshot IS NULL) FROM logical_calls
UNION ALL SELECT 'negative_tokens',count_if(input_tokens<0 OR output_tokens<0) FROM calls
UNION ALL SELECT 'negative_historical_cost',count_if(estimated_cost_usd<0) FROM calls
UNION ALL SELECT 'physical_conflict_ids',count_if(physical_variants>1) FROM physical_keys
UNION ALL SELECT 'physical_missing_request_id',count_if(databricks_request_id IS NULL) FROM physical_keys
UNION ALL SELECT 'unmatched_logical_calls',count_if(reconciliation_state='missing') FROM reconciled
UNION ALL SELECT 'multiple_physical_requests',count_if(reconciliation_state='multiple') FROM reconciled
UNION ALL SELECT 'ambiguous_client_request_id',count_if(logical_owners>1) FROM logical_client_keys
UNION ALL SELECT 'model_dimension_missing',sum(coalesce(requests_with_unverified_model,0)) FROM reconciled
UNION ALL SELECT 'physical_requests_without_selected_call',count(*) FROM physical_one u
  WHERE NOT EXISTS (SELECT 1 FROM compatible_requests r WHERE r.workspace_id=u.workspace_id AND r.databricks_request_id=u.databricks_request_id)
UNION ALL SELECT 'conflicting_or_missing_billing_record_id',count_if(record_variants>1 OR record_id IS NULL) FROM billed
UNION ALL SELECT 'missing_or_ambiguous_prices',count_if(price_state<>'unique') FROM billed
UNION ALL SELECT 'billing_records_not_monetized',count_if(list_cost_usd IS NULL) FROM billed
UNION ALL SELECT 'calls_after_billing_coverage',count(*) FROM logical_calls c LEFT JOIN call_billing_coverage b USING(run_id,attempt_id,call_id)
  WHERE c.started_at>b.billing_end_utc OR b.billing_end_utc IS NULL
UNION ALL SELECT 'cache_cost_uncertainty',count(*) FROM logical_calls
), costops_result_marker AS (
  SELECT *,true AS _costops_has_row FROM costops_result
)
SELECT r.* EXCEPT(_costops_has_row)
FROM bounds p LEFT JOIN costops_result_marker r ON true
WHERE CASE WHEN p.fecha_desde IS NULL OR p.fecha_hasta IS NULL OR p.fecha_desde>p.fecha_hasta
  THEN raise_error('CostOps: fecha_desde/fecha_hasta deben formar un rango valido')
  ELSE coalesce(r._costops_has_row,false) END
;
