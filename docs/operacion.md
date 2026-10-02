# Operación del Databricks Development Harness

Para desarrollar o retomar un cambio del producto, consulta el
[protocolo de contexto del proyecto](contexto-proyecto.md). La guía distingue
las fuentes del harness de las fuentes de cada repositorio cliente.

## Instalación y despliegue

Cada App atiende un cliente con el mismo código del producto. El operador entrega
un perfil externo aprobado y parámetros de infraestructura mediante el
[procedimiento de instalación](configuracion-instalacion.md). El bundle común no
selecciona cliente ni workspace por defecto. Los nombres e IDs del piloto se
conservan en [examples/naturapet](../examples/naturapet/README.md).

La instalación configura catálogo, esquema, volumen de registros, tabla de
coordinación y sandbox exclusivos. La App necesita SELECT/MODIFY en la tabla y
acceso a registros; el Job ejecuta con identidad dedicada distinta de la App y
sin secretos GitHub, acceso a modelos o recursos del cliente. La clave privada
se referencia desde secret scope; nunca se escribe en Git o perfiles. Revisar
ACL antes de habilitar HUs, incluida lectura del runner Workspace por el Job.

Ejecutar bundle validate --strict desde el paquete con el perfil CLI del entorno.
Para una instalación nueva, desplegar el bundle revisado y ejecutar la App. Para
actualizar solo código de una App existente, sincronizar el paquete y ejecutar
la App existente conservando sus bindings. La validación no demuestra permisos
ni ejecución: completar smoke sintético positivo y negativo del Job. Registrar
por separado evidencia local, validación y despliegue real.

El helper scripts/prepare_app_only_deployment.py sigue generando requests a partir
de configuración renderizada; su modo provisional omite sandbox y bloquea pruebas
que requieren Job. No usarlo para habilitar general_patch ejecutable sin sandbox.
Los scripts de provisión requieren argumentos explícitos y recursos del harness.

## Perfil y recuperación

El proceso fija perfil y hash al arrancar y los registra en cada intento y llamada.
Los snapshots están protegidos por el mismo almacén y ACL de checkpoints. Una
HU no modifica .harness/ ni activa configuración del repositorio. Las diferencias
de perfil o falta de procedencia histórica bloquean continuación y aprobación;
consulta y cancelación autorizadas siguen disponibles. Un reintento humano del
mismo repo fija el perfil actual, vuelve a planificar y exige aprobación nueva.
Drenar HUs antes de migrar y conservar paquete previo para rollback; nunca borrar
checkpoints ni inventar procedencia del histórico. Véase la guía de instalación.

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

El perfil aprobado delimita alcance, operaciones, extensiones, límites y validadores.
`.github/`, `.agents/`, `.harness/`, OpenSpec y `AGENTS.md` quedan protegidos;
secretos, datos y runtime están excluidos según política. No habilita ejecución
ni despliegue de recursos cliente. `silver_safe_ratio` conserva editor y prueba
SQL acotados. Los valores concretos del piloto viven en su ejemplo.

Las pruebas funcionales se seleccionan desde `tests/` del cliente y corren en el Job separado, junto con la validación estática del tipo de archivo. Pytest conserva Python aislado, plugins externos deshabilitados y entorno sin credenciales; `pythonpath=.` añade únicamente la raíz del checkout a las importaciones de pruebas. Los YAML compartidos mantienen Sonnet obligatorio y Haiku asesor, amplían la respuesta máxima a 12000 tokens y el registro resumido a 64000 caracteres. El presupuesto de contexto cliente permite 50 lecturas, 400 KB acumulados y 120 segundos por etapa.

Antes de la primera HU, integrar en `develop` la preparación manual OpenSpec 1.13.2 con las siete skills, contexto del proyecto y reglas; comprobar el acceso de la GitHub App y mantener pruebas sintéticas del comportamiento afectado. Una primera prueba de documentación o código puro con regresiones existentes evita depender de recursos externos. Selecciona pruebas existentes en el checkout cliente: este harness no aporta automáticamente una suite al cliente. En el producto, [test_project_context.py](../tests/test_project_context.py) comprueba referencias y el contexto general; nuevas reglas funcionales requieren pruebas específicas en el manifiesto aprobado.

Los cambios en `databricks.yml` o `resources/` activan obligatoriamente `bundle validate --strict -t dev`, si ese target está configurado en el perfil aprobado. Esta comprobación requiere CLI Databricks y autenticación aislada provisionadas en el Job; el runtime actual del Job solo declara pytest y no prepara dichas herramientas. Hasta provisionarlas, las HUs de bundle quedan bloqueadas en verificación y no publican PR. Nunca usar credenciales de la App como alternativa ni ejecutar bundle deploy/run del cliente. La revisión del PR y la parada de la App siguen siendo decisiones humanas.

## Registros, costos y retención

La [guía de gestión de contexto](gestion-contexto.md) define contratos por rol,
selección, cache, vigencia de decisiones, presupuesto, activación y rollback.
La política del producto está deshabilitada por defecto; una instalación verificada
puede habilitarla para intentos nuevos. Los históricos conservan su modalidad.

`runs/<run_id>.json` usa contrato v5; `attempts[]` conserva etapa, revisión, SHA base, mensajes, eventos, aprobaciones, publicación y checkpoint. `runs/agent_calls/<run_id>-<call_id>.json` usa contrato v3; contiene `run_id`, `attempt_id`, rol, etapa, revisión, modelo, estado, tiempos, tokens y `estimated_cost_usd` cuando existe `usage`. Una llamada fallida o sin `usage` tiene costo ausente, no cero. Los registros v3 de ejecución y v2 de llamadas siguen legibles para consultas históricas. [harness_costs_by_call.sql](sql/harness_costs_by_call.sql) une ejecución y llamadas por **ambos** `run_id` y `attempt_id`; `call_id` identifica cada invocación. Los precios YAML son supuestos, no facturación real.

Los artefactos redactados viven en `runs/openspec/`; los checkpoints de bytes exactos y diffs de revisión se almacenan por separado en el volumen UC. El operador debe restringir `READ_VOLUME` y `WRITE_VOLUME` a las identidades autorizadas, definir retención y borrado según la política del cliente, y conservar checkpoints de intentos activos y PR pendientes. Un registro histórico puede consultarse sin migrarlo; la coordinación nueva comienza en la tabla Delta. Si el JSON y la tabla divergen, la recuperación usa el checkpoint cuyo identificador coincide con la tabla y rechaza contenido alterado. Nunca borrar manualmente un checkpoint activo para resolver un error.
