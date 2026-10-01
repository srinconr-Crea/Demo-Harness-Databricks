# Verificación local

Fecha: 2026-10-01. Cambio: consume-client-openspec-skills.

## Resultado

- Suite completa: **158 passed, 1 skipped**, 703.86 s. Comando: `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider --tb=short --junitxml=.tmp/skills-tests.xml`.
- Pruebas del lector y procedencia: 13 passed; cubren skills faltantes/incompatibles, UTF-8, nombres, presupuestos, traversal, junctions, hashes, snapshots alterados, rondas contextualizadas y fallos de endpoint.
- Conversación y adaptador OpenSpec: 19 passed; mantienen ratio, revisión histórica del diff, actualizaciones, fallos de pruebas y publicación/reintento.
- Recorrido adicional con CLI real y skills oficiales generadas mediante preparación explícita: passed. Incluye reinicio en espera de aprobación, base remota sintética avanzada, nueva planificación/aprobación y PR simulado; no publica `.agents/`.
- Reintento y cancelación de históricos sin procedencia: passed en comprobación específica adicional.
- `openspec validate consume-client-openspec-skills --strict`: válido.
- `openspec instructions apply --change consume-client-openspec-skills --json`: all_done, 16/16 tareas completas.
- `git diff --check`: sin errores.

## Alcance y límites

Repositorios locales sintéticos, CLI OpenSpec 1.13.2 real, modelos y GitHub simulados. Se probaron contratos, controles y trazabilidad; no se invocaron endpoints LLM reales ni se ejecutó el Job remoto. La colección opcional de PySpark quedó omitida. FastAPI/Starlette emitió una advertencia de deprecación del transporte de TestClient.

La suite se ejecutó fuera del sandbox de archivos por las ACL temporales de pytest en Windows; la caché uv y el reporte se guardaron en `.tmp/`, ignorado por Git. Esta verificación local precedió al archivo y al despliegue autorizados posteriormente. La evidencia operativa está en `docs/evidence/2026-10-01-client-skills/deployment.md`.
