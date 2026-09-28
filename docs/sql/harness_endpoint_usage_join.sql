-- Requires system.serving.endpoint_usage access and request tracking enabled.
-- Use the base query as a view named harness_costs_by_call, then join by the exact request ID.
SELECT c.*, u.request_time AS usage_request_time,
       u.input_token_count AS usage_input_tokens,
       u.output_token_count AS usage_output_tokens,
       u.status_code AS usage_status_code,
       u.usage_context AS usage_context
FROM harness_costs_by_call c
LEFT JOIN system.serving.endpoint_usage u
  ON c.client_request_id = u.client_request_id
ORDER BY c.started_at, c.call_id;
