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

El perfil YAML fija repositorio, rama base, rutas editables, instalación de GitHub App y estrategia. La preparación es exclusivamente humana, fuera de la App. En el checkout cliente, una persona usa la CLI compatible (actualmente 1.13.2), selecciona los workflows y genera las skills:

```powershell
openspec config set profile custom
openspec config set delivery skills
openspec config set workflows '["explore","propose","update","apply","verify","sync","archive"]'
openspec init --tools agents --profile custom --no-animation
```

Estas preferencias son globales a esa instalación de CLI; se pueden aislar mediante XDG_CONFIG_HOME. Configurar `openspec/config.yaml` con contexto y reglas del cliente, comprobar los siete `.agents/skills/openspec-*/SKILL.md` (verify no pertenece a core) y crear un PR `feature/*` con configuración/specs y skills. Revisión y merge son humanos. La App solo admite la base integrada y no ejecuta init/update, no repara archivos ni crea ese PR. El antiguo script onboard_client.py se retira.

El runtime consume las skills completas como instrucciones mediadas; allowed-tools no da acceso a shell. `openspec_skills` en el perfil confiable configura versiones compatibles y presupuestos: 128 KiB por skill, 1 MiB por catálogo y 512 KiB por prompt. Inicialmente generatedBy debe coincidir con la versión CLI; un cambio incompatible o una skill faltante bloquea la HU con diagnóstico. `.agents/` permanece solo lectura para el desarrollador.

Actualizar CLI y skills fuera de las HUs, regenerar mediante `openspec update` con los workflows seleccionados y someter los cambios a otro PR humano. Un intento activo conserva SHA base, hashes y runtime; no cambia silenciosamente de instrucciones. Los procesos anteriores sin procedencia requieren reintento explícito con cliente preparado; consulta y cancelación siguen disponibles y su modalidad de publicación se conserva.

La procedencia se guarda en cada llamada y los snapshots íntegros en `instructions/<run_id>/<attempt_id>/`, bajo las ACL del volumen de registros; no se exponen por el hilo principal. Los hashes normalizan rutas temporales para permitir recuperación en otro directorio. Fases deterministas generan evidencia sin llamadas o costos ficticios.

El checkout completo se hace en una carpeta local temporal al SHA exacto de la base. El token de instalación solo se pasa en variables de entorno de Git y no se almacena en URL, argumentos, configuración ni logs. El harness rechaza enlaces y límites excedidos. Tras cada etapa conserva un checkpoint de los bytes cambiados y su manifiesto SHA-256 para restaurar el estado después de reinicios.

## Conversación de HU y pruebas generales

La [guía de desarrollo general y publicación automática](repository-workflow.md) define propuesta, manifiesto, autorización, adaptadores, sandbox e interfaz. Las nuevas ejecuciones requieren aprobación del plan y continúan automáticamente hasta el PR después de verificar, sincronizar y archivar. Los intentos históricos mantienen su revisión final del diff. Haiku 4.5 es asesor; Sonnet y pruebas obligatorias siguen bloqueando.

El formulario recibe hu y description. GET /runs/{run_id} muestra estado, revisión, mensajes, autorizaciones y checklist; /events pagina eventos, /calls expone uso y costos, /artifacts/{artifact_id} entrega artefactos y /diff permite consultar el candidato preparado o publicado. Todos los endpoints de una HU exigen x-forwarded-user y acceso del creador o revisores configurados.

POST /runs/{run_id}/actions recibe action, expected_revision, idempotency_key, expected_hash para aprobar y text para answer/changes. Una respuesta vuelve a explorar; pedir cambios produce propuesta nueva. Los históricos admiten aprobación del diff; los nuevos no requieren esa acción. Una base avanzada invalida el candidato y exige nueva planificación y aprobación. POST /runs/{run_id}/retry reintenta la etapa fallida con expected_revision. Los checkpoints y leases conservan recuperación e idempotencia.

El perfil NaturaPet conserva silver_safe_ratio y la prueba SQL sintética; no se amplía automáticamente. tests/fixtures/clients/repository.yaml ejemplifica alcance repository, rutas solo lectura/sin acceso, extensiones y matriz de pruebas. El operador configura suites e instala las herramientas del Job antes de habilitar tipos nuevos. CLI bundle, prueba o identidad ausentes bloquean publicación. La revisión del PR y la parada de la App siguen siendo decisiones humanas.

## Registros, costos y retención

`runs/<run_id>.json` usa contrato v5; `attempts[]` conserva etapa, revisión, SHA base, mensajes, eventos, aprobaciones, publicación y checkpoint. `runs/agent_calls/<run_id>-<call_id>.json` usa contrato v3; contiene `run_id`, `attempt_id`, rol, etapa, revisión, modelo, estado, tiempos, tokens y `estimated_cost_usd` cuando existe `usage`. Una llamada fallida o sin `usage` tiene costo ausente, no cero. Los registros v3 de ejecución y v2 de llamadas siguen legibles para consultas históricas. [harness_costs_by_call.sql](sql/harness_costs_by_call.sql) une ejecución y llamadas por **ambos** `run_id` y `attempt_id`; `call_id` identifica cada invocación. Los precios YAML son supuestos, no facturación real.

Los artefactos redactados viven en `runs/openspec/`; los checkpoints de bytes exactos y diffs de revisión se almacenan por separado en el volumen UC. El operador debe restringir `READ_VOLUME` y `WRITE_VOLUME` a las identidades autorizadas, definir retención y borrado según la política del cliente, y conservar checkpoints de intentos activos y PR pendientes. Un registro histórico puede consultarse sin migrarlo; la coordinación nueva comienza en la tabla Delta. Si el JSON y la tabla divergen, la recuperación usa el checkpoint cuyo identificador coincide con la tabla y rechaza contenido alterado. Nunca borrar manualmente un checkpoint activo para resolver un error.
