# Verificación de contratos de respuesta LLM

Cambio: `harden-llm-response-contracts`. Base revisada: `71d13dd9dd1e3831e18a7862128be8177737d32a`, rama `Db_Spec_Harness`.

## Comportamiento verificado localmente

El planner recibe los títulos canónicos de su plantilla y la instrucción de conservarlos literalmente con cuerpo en español, en propose/update y ambos estados del gestor. Los defectos de representación/encabezados conservan `invalid_contract` y permiten retry humano, sin convertir denegaciones de política en errores recuperables de presentación. El flujo sintético persiste un fallo de design después de proposal válido, rechaza identidad/fallo/revisión incorrectos y, tras retry autorizado, espera revisión del plan sin invocar developer ni publicar.

La respuesta final con texto externo solo habilita una corrección si contiene un único objeto completo y ya válido según contrato, Markdown y política. La corrección conserva todos los valores y tipos JSON; varios objetos, duplicados, truncamiento, context_request y contratos inválidos no habilitan esa ampliación. La evidencia conserva hashes, aceptación, vínculo parent_call_id/recovery_index y costo por llamada cuando existe usage. Usage ausente no se convierte en costo cero.

Regresiones nuevas: `tests/test_llm_presentation.py`, complementadas por `test_planner_artifact_contracts.py` y las suites existentes de recuperación, contexto, coordinación y conversación. Las pruebas iniciales fallaron antes de implementar; la revisión independiente detectó dos problemas corregidos: compatibilidad de planificación sin perfil y rechazo de varios objetos que empiezan/terminan con llaves. La revisión final no dejó hallazgos accionables.

## Comandos y entorno

Pruebas enfocadas:

```powershell
$env:PYTHONUTF8='1'
uv --cache-dir .deployments/.uv-cache run --project src/agents/harness --with pytest pytest tests/test_llm_presentation.py tests/test_planner_artifact_contracts.py tests/test_response_recovery.py tests/test_context_request_contract.py -q -p no:cacheprovider --basetemp="$env:TEMP/hc4"
```

Resultado: **116 passed**, una advertencia de deprecación Starlette/httpx, 215,23 segundos.

Suite completa:

```powershell
uv --cache-dir .deployments/.uv-cache run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider --ignore=tests/tmp_pytest --basetemp="$env:TEMP/hc5"
```

Resultado: **356 passed, 1 skipped**, una advertencia de deprecación Starlette/httpx, 1034,47 segundos. Se excluye una carpeta temporal preexistente sin permisos de lectura. Se usa un destino temporal corto porque Windows rechazaba rutas largas de snapshots en el basetemp dentro del repositorio; no se cambió el producto para eludirlo. La ejecución necesita acceso fuera del sandbox a los temporales de pytest. Logs locales en `.deployments/` (ignorados).

```powershell
node src/agents/harness/node_modules/@fission-ai/openspec/bin/openspec.js validate harden-llm-response-contracts --strict
git diff --check
```

Ambos pasaron antes de sincronizar. Sin cambios de infraestructura, modelos, presupuestos o perfil cliente. Los cambios locales previos de preparación NaturaPet y otro archive quedan fuera de esta publicación.

Sync verificado en `agent-prompt-contracts`, `change-planning` y `observability-control`: cada bloque delta coincide con la spec vigente y los escenarios previos se conservan. `validate --specs --strict`: **15 passed, 0 failed**. OpenSpec reportó 16/16 tareas completas y los cuatro artefactos done. Cambio archivado en `openspec/changes/archive/2026-10-06-harden-llm-response-contracts/`, incluida `.openspec.yaml`; `openspec list --json` no contiene cambios activos.

## Preflight de App e histórico

Perfil seleccionado por el usuario: `CREA_DEV`. App: `demo-dbx-harness-mvp`. Antes del despliegue: compute STOPPED; siete registros, dos complete y cinco failed, ninguno queued/running. El archivo del run `9f4d553d17ea406ca596600875735656` conserva failed y `retryable=false`, SHA256 `97c8bd7f29fcd75f83c062294c69e4fd09e88fe7d7cfe97948b09fc3985af73d`.

La validación local usa respuestas sintéticas: no acredita una nueva HU remota ni una llamada real del endpoint. El despliegue y su smoke HTTP se registrarán por separado con sus resultados observados. El intento histórico no se reintenta.
