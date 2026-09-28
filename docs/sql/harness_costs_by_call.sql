-- Provide :runs_path and :calls_path as parameter markers pointing at the configured UC volume.
-- One row per model call; the attempt join prevents files from another retry being attributed here.
WITH runs AS (
  SELECT * FROM read_files(:runs_path, format => 'json', multiLine => true)
), attempts AS (
  SELECT r.run_id, r.story_id, r.story.title AS story_title, r.client_profile,
         r.repository, a.attempt_id, a.state AS attempt_state,
         a.changed_files, a.result, a.publication, a.queued_at, a.started_at, a.finished_at
  FROM runs r
  LATERAL VIEW OUTER explode(r.attempts) exploded AS a
), calls AS (
  SELECT * FROM read_files(:calls_path, format => 'json', multiLine => true)
)
SELECT c.story_id AS hu_id, a.story_title, c.run_id, c.attempt_id, c.call_id,
       c.role AS agente, c.model AS modelo, c.status AS llamada_estado,
       a.attempt_state AS intento_estado, a.changed_files AS archivos_cambiados,
       c.input_text AS entrada_agente, coalesce(c.output_text, c.response) AS salida_agente,
       c.parsed_output AS salida_estructurada, c.input_sha256, c.output_sha256,
       c.started_at, c.completed_at, c.duration_ms,
       c.input_tokens, c.output_tokens, c.estimated_cost_usd AS costo_estimado_usd,
       c.pricing_source, c.client_request_id, c.databricks_request_id,
       a.result.pr_url AS pr_url, a.publication.stage AS etapa_publicacion
FROM calls c
LEFT JOIN attempts a ON a.run_id = c.run_id AND a.attempt_id = c.attempt_id
ORDER BY c.started_at, c.call_id;
