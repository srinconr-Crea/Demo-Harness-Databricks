# Operación del Databricks Development Harness

## Recursos y despliegue

El bundle `databricks.yml` usa el catálogo `demo_harness_databricks_dev`, un volumen `artifacts` para registros, un volumen `demo_harness_sandbox` para paquetes de prueba y la tabla Delta `demo_harness_run_state` para coordinación. La App desplegada actualmente se llama `demo-dbx-harness-mvp`; el SQL warehouse aislado es `demo-harness-sandbox-wh` (`9e696889dea65361`). El perfil `CREA_DEV` apunta a `https://adb-7405606739630987.7.azuredatabricks.net`.

La clave PEM de la GitHub App vive en el secret scope `demo-harness-databricks` y no se copia a Git, prompts ni Job. El Job `demo_harness_sandbox` requiere una identidad de servicio **dedicada**, distinta de la App y de cualquier identidad del cliente. En el bundle, sustituir `SET_DEDICATED_SANDBOX_SERVICE_PRINCIPAL` mediante la variable `sandbox_service_principal` antes de desplegar. Conceder a esa identidad solo `READ_VOLUME` y `WRITE_VOLUME` sobre `demo_harness_sandbox`; no conceder acceso al volumen de registros, al secreto GitHub, a endpoints de modelos ni a los recursos del cliente. La App recibe `CAN_MANAGE_RUN` sobre el Job y `READ_VOLUME`/`WRITE_VOLUME` sobre el volumen sandbox. Revisar estas concesiones en el plan del bundle y en Unity Catalog antes del despliegue.

El entorno `dev` ya configura la identidad `demo_harness_sandbox`
(`dac4cb01-380f-4af5-b594-132d6d693beb`) y el Job `611081415041874`.
Las pruebas reales positivas y negativas y el recorrido de interfaz constan
en la [evidencia de verificación](evidence/2026-09-30-openspec/verification.md).
El despliegue inicial requirió `USE_CATALOG` y `USE_SCHEMA` en el catálogo y
esquema del harness, además de los grants del volumen declarados en el bundle.
La identidad necesita `CAN_READ` solo sobre el archivo Workspace
`src/agents/harness/app/sandbox_job_runner.py` dentro de los archivos del bundle;
comprobar ese ACL si se recrea el archivo. El usuario que configura `run_as`
necesita el rol Service Principal User sobre la identidad dedicada, conservando
los demás roles existentes según el [procedimiento oficial](https://learn.microsoft.com/en-us/azure/databricks/security/auth/access-control/service-principal-acl).

```powershell
databricks auth describe --profile CREA_DEV
databricks bundle validate --strict -t dev --profile CREA_DEV
databricks bundle deploy -t dev --profile CREA_DEV --var sandbox_service_principal=<application-id-dedicado>
databricks bundle run harness -t dev --profile CREA_DEV
```

La validación comprueba el esquema del bundle; **no** demuestra que la identidad, grants y ejecución real del Job estén operativos. Probar primero con un cliente sintético. El despliegue o los cambios de permisos requieren revisión operativa. Para detener la App: `databricks apps stop demo-dbx-harness-mvp --profile CREA_DEV`.

La tabla de coordinación se crea una vez antes del despliegue mediante `src/agents/harness/app/provision_run_state.py --profile CREA_DEV --warehouse-id 9e696889dea65361 --table demo_harness_databricks_dev.dev_srinconr_demo_harness_databricks.demo_harness_run_state`. La tabla ya fue preparada en el entorno de desarrollo; repetir el comando es idempotente. Confirmar que la App tiene `SELECT` y `MODIFY` sobre ella.

## Publicación provisional de la App

Mientras la identidad dedicada y las pruebas del Job están pendientes, publicar
solo la App con los recursos existentes y la tabla de coordinación. El script
siguiente omite los bindings del Job y del volumen sandbox; `general_patch`
continúa bloqueado si requiere pruebas ejecutables. No ejecutar el despliegue
completo del bundle hasta configurar la identidad dedicada.

```powershell
databricks bundle validate --strict -t dev --profile CREA_DEV -o json > .databricks/app-deploy-config.json
src/agents/harness/.venv/Scripts/python.exe scripts/prepare_app_only_deployment.py .databricks/app-deploy-config.json
databricks bundle sync -t dev --profile CREA_DEV
databricks apps update demo-dbx-harness-mvp --profile CREA_DEV --json @.databricks/app-only-update.json
databricks apps start demo-dbx-harness-mvp --profile CREA_DEV
databricks apps deploy demo-dbx-harness-mvp --profile CREA_DEV --json @.databricks/app-only-deployment.json
```

Este procedimiento provisional se conserva como alternativa cuando el sandbox
no esté disponible. En `dev` el Job ya está desplegado y probado; la preparación
OpenSpec de cada cliente y su merge humano siguen siendo pasos de incorporación.

## Incorporación única de un cliente

El perfil YAML fija repositorio, rama base, rutas editables, instalación de GitHub App y estrategia. OpenSpec vive en el repositorio cliente. Ejecutar `src/agents/harness/app/onboard_client.py` con el perfil configurado para clonar la base, correr `openspec init --tools none`, escribir `openspec/config.yaml` con contexto del cliente y abrir un PR `feature/openspec-setup-*` que contenga solo OpenSpec. Una persona integra ese PR en la rama base. La App rechaza toda HU cuyo SHA base no contenga `openspec/config.yaml` válido; cada HU posterior **no** vuelve a inicializar OpenSpec.

El checkout completo se hace en una carpeta local temporal al SHA exacto de la base. El token de instalación solo se pasa en variables de entorno de Git y no se almacena en URL, argumentos, configuración ni logs. El harness rechaza enlaces y límites excedidos. Tras cada etapa conserva un checkpoint de los bytes cambiados y su manifiesto SHA-256 para restaurar el estado después de reinicios.

## Conversación de HU

El formulario tiene dos campos: `hu` y `description`. `POST /run` devuelve `run_id` y cola la ejecución. `GET /runs/{run_id}` muestra estado, etapa, revisión, mensajes, aprobaciones y referencias de artefactos; `GET /runs/{run_id}/events?after=0&limit=50` pagina eventos; `GET /runs/{run_id}/calls` muestra rol, modelo, tokens y costo estimado. `GET /runs/{run_id}/artifacts/{artifact_id}` recupera el artefacto de la revisión y `GET /runs/{run_id}/diff` entrega el candidato final con su hash. Todos los endpoints de una ejecución exigen `x-forwarded-user` y limitan acceso al creador o revisores del perfil.

1. `exploring` puede pasar a `awaiting_clarification`. Responder con acción `answer` y texto.
2. `proposing` produce proposal, specs, design y tasks con Sonnet 5, ejecuta `openspec validate --strict` y pasa a `awaiting_plan_review`. Aprobar con `approve` y `expected_hash` del plan, o pedir `changes` con texto. Cada actualización incrementa la revisión y exige una aprobación nueva.
3. `applying` llama al desarrollador. `silver_safe_ratio` usa el editor acotado; `general_patch` aplica operaciones `create`, `modify` o `delete` solo dentro de rutas y extensiones configuradas. `verifying` ejecuta validadores y pruebas del perfil, el verificador OpenSpec Sonnet 5 y una revisión independiente. Hallazgos vuelven a `updating` hasta dos correcciones; una evidencia inconclusa no llega al diff final.
4. `preparing_final_diff` completa tareas, sincroniza y archiva el cambio OpenSpec en el checkout. `awaiting_diff_review` muestra el diff completo y el hash del candidato. Se puede aprobar o pedir cambios; los cambios restauran el checkpoint previo al archivo y vuelven al plan. La aprobación se vincula al SHA base, revisión y bytes exactos.
5. `publishing` comprueba otra vez la cabeza remota de la base. Si avanzó, invalida el candidato y reinicia la exploración sobre el nuevo SHA. Si coincide, crea o reutiliza `feature/*` y el PR cuando su diff remoto completo coincide. El PR requiere revisión y merge humano; el harness nunca hace merge ni despliega código cliente. Los checks `pending` y `unavailable` se muestran con esos estados, nunca como aprobados.

Las acciones se envían a `POST /runs/{run_id}/actions` con `action`, `expected_revision`, `idempotency_key`, `expected_hash` cuando sea aprobación y `text` cuando sea respuesta o cambios. También se permite `cancel` durante una espera. Las aprobaciones obsoletas son rechazadas. La App reanuda intentos `queued` o `running` al reiniciar; las esperas no ocupan un trabajador. Si una etapa falla por infraestructura, el evento `error` conserva el checkpoint previo y la App ofrece `POST /runs/{run_id}/retry` con `expected_revision` para repetir la etapa. Si el PR ya existe, la App conserva y comprueba rama, commit y URL antes de completar.

## Perfil para cambios generales y sandbox

`general_patch` declara `allowed_paths`, `extensions`, `operations`, `max_files`, `max_bytes`, `test_adapters` y `test_paths`. Un perfil debe habilitar pruebas ejecutables (`pytest_sandbox`) para código o archivos de datos que puedan alterar el programa. Los objetivos `test_paths` son configurados por el operador y deben existir en el checkout cliente; la HU no puede cambiarlos. El Job recibe un ZIP acotado por archivos y bytes, verifica su SHA-256, extrae sin enlaces ni traversal y ejecuta pytest con un entorno sin secretos de la App, tiempo máximo y salida acotada. Si el Job no está configurado o falla, la publicación queda bloqueada. Para documentación Markdown se exige estructura; para Python y notebooks se comprueba sintaxis; JSON y YAML se analizan antes de las pruebas.

El perfil piloto existente mantiene `silver_safe_ratio` y su prueba SQL de tres casos: positivo, cero y NULL. Para un cliente general, copiar el ejemplo sintético de `tests/fixtures/clients/general.yaml`, adaptar repositorio, rutas y pruebas, y configurar una instalación GitHub App exclusiva. El perfil actual desplegado todavía no habilita `general_patch`; se activa por cliente cuando sus pruebas estén configuradas. El Job dedicado ya está disponible en `dev`. La HU no debe contener comandos de pruebas ni rutas que amplíen el perfil. El scaffold `agent.py`, `graph.py`, `tools.py` y `eval/` no ejecuta el flujo FastAPI.

## Registros, costos y retención

`runs/<run_id>.json` usa contrato v4; `attempts[]` conserva etapa, revisión, SHA base, mensajes, eventos, aprobaciones, publicación y checkpoint. `runs/agent_calls/<run_id>-<call_id>.json` usa contrato v3; contiene `run_id`, `attempt_id`, rol, etapa, revisión, modelo, estado, tiempos, tokens y `estimated_cost_usd` cuando existe `usage`. Una llamada fallida o sin `usage` tiene costo ausente, no cero. Los registros v3 de ejecución y v2 de llamadas siguen legibles para consultas históricas. [harness_costs_by_call.sql](sql/harness_costs_by_call.sql) une ejecución y llamadas por **ambos** `run_id` y `attempt_id`; `call_id` identifica cada invocación. Los precios YAML son supuestos, no facturación real.

Los artefactos redactados viven en `runs/openspec/`; los checkpoints de bytes exactos y diffs de revisión se almacenan por separado en el volumen UC. El operador debe restringir `READ_VOLUME` y `WRITE_VOLUME` a las identidades autorizadas, definir retención y borrado según la política del cliente, y conservar checkpoints de intentos activos y PR pendientes. Un registro histórico puede consultarse sin migrarlo; la coordinación nueva comienza en la tabla Delta. Si el JSON y la tabla divergen, la recuperación usa el checkpoint cuyo identificador coincide con la tabla y rechaza contenido alterado. Nunca borrar manualmente un checkpoint activo para resolver un error.
