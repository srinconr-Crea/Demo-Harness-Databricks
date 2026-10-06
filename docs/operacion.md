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

Los contratos de capacidades y destinos se detallan en la
[guía del planner](agents/planner.md); la cobertura y las operaciones acumuladas
se describen en el [contrato del editor](editor-manifest.md).

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

Las pruebas funcionales se seleccionan desde `tests/` del cliente y corren en el Job separado, junto con la validación estática del tipo de archivo. Pytest conserva Python aislado, plugins externos deshabilitados y entorno sin credenciales; `pythonpath=.` añade únicamente la raíz del checkout a las importaciones de pruebas. Los YAML compartidos mantienen Sonnet obligatorio y Haiku asesor; el planner permite hasta 64000 tokens y otros roles conservan 12000 como fallback, con registro resumido de 64000 caracteres. El presupuesto de contexto cliente permite 50 lecturas, 400 KB acumulados y 120 segundos por etapa.

Antes de la primera HU, integrar en `develop` la preparación manual OpenSpec 1.13.2 con las siete skills, contexto del proyecto y reglas; comprobar el acceso de la GitHub App y mantener pruebas sintéticas del comportamiento afectado. Una primera prueba de documentación o código puro con regresiones existentes evita depender de recursos externos. Selecciona pruebas existentes en el checkout cliente: este harness no aporta automáticamente una suite al cliente. En el producto, [test_project_context.py](../tests/test_project_context.py) comprueba referencias y el contexto general; nuevas reglas funcionales requieren pruebas específicas en el manifiesto aprobado.

Los cambios en `databricks.yml` o `resources/` activan obligatoriamente `bundle validate --strict -t dev`, si ese target está configurado en el perfil aprobado. Esta comprobación requiere CLI Databricks y autenticación aislada provisionadas en el Job; el runtime actual del Job solo declara pytest y no prepara dichas herramientas. Hasta provisionarlas, las HUs de bundle quedan bloqueadas en verificación y no publican PR. Nunca usar credenciales de la App como alternativa ni ejecutar bundle deploy/run del cliente. La revisión del PR y la parada de la App siguen siendo decisiones humanas.

## Verificación y corrección de implementación

Las pruebas obligatorias y Sonnet conservan los hallazgos antes de decidir la
continuación. La categoría propuesta por el modelo no otorga permisos: el
harness contrasta evidencia, plan, perfil y manifiesto vigentes.

| Categoría | Continuación |
| --- | --- |
| `implementation` | `correcting` usa el desarrollador con la fase `apply`, conserva aprobación y revisión del plan, y vuelve a validación técnica y Sonnet. Solo permite reparaciones dentro del contrato autorizado. |
| `scope_spec` | `update` prepara otra revisión del plan y espera aprobación humana antes de editar el alcance adicional. Los hallazgos mixtos que requieren cambiar el contrato impiden la corrección dependiente. |
| `infrastructure_evidence` | Recuperación o lecturas acotadas ya autorizadas; si la evidencia sigue siendo insuficiente, `failed` con diagnóstico. Un sandbox inaccesible o `passed=false` sin causa no autoriza modificar código. |
| `harness_defect` | `failed` y diagnóstico del producto, sin enviar al planner o desarrollador cliente a repararlo. |

Los rechazos ambiguos, contratos inválidos y denegaciones de política conservan
sus controles. Los hallazgos informativos no generan reparaciones por sí solos.
Haiku 4.5 conserva su invocación asesora: recomendaciones, rechazo e
indisponibilidad no bloquean ni consumen correcciones de implementación.

La revisión/hash del plan identifica la autorización; la versión/hash del
candidato identifica los bytes que se prueban. Una corrección material invalida
la elegibilidad de pruebas y Sonnet del candidato anterior. Sus resultados
permanecen históricos y la App muestra `correcting`, causa y verificación
pendiente para los bytes nuevos. Las notas del desarrollador no sustituyen
pruebas ejecutadas. El estado de tareas se registra aparte durante la
corrección, sin modificar los bytes aprobados de `tasks.md`; sync, archive y PR
siguen pendientes hasta sus transiciones deterministas.

El máximo compartido entre fallos técnicos y semánticos es de dos correcciones
lógicas por intento. Checkpoint y coordinación reservan cada continuación antes
de invocar el modelo; reiniciar, actualizar el plan o cambiar de etapa no reinicia
el contador. Antes de otra llamada equivalente se comprueba progreso pertinente
del candidato, contrato o evidencia: prosa distinta, timestamps, IDs y una nueva
aprobación del mismo alcance no resuelven un bloqueo. La recurrencia sin avance
detiene el intento con evidencia. La recuperación de formato conserva su límite
propio y no constituye una corrección de implementación. Cada llamada real
conserva su uso y costo estimado cuando existe `usage`.

El desarrollador puede proponer operaciones parciales, pero debe cubrir cada
entrada del manifiesto con una operación, `already_conformant` con hash actual
comprobable o un bloqueo con evidencia. `operations=[]` no acredita éxito por
sí solo. El manifiesto limita el efecto acumulado base/candidato: un `create`
aprobado permite corregir mediante `modify` el archivo ya creado en ese intento;
un `modify` aprobado no permite eliminar el archivo. El editor comprueba hashes,
rutas, tipos, atomicidad y límites acumulados antes de escribir. Las pruebas se
seleccionan sobre todos los cambios respecto de la base, aunque la última
corrección toque solo parte de ellos.

La propuesta declara capacidades OpenSpec nuevas o modificadas y sus destinos
exactos, contrastados con el inventario autorizado. Los deltas se generan por
capacidad, no por nombre de la HU, y los requisitos `MODIFIED` se comprueban
contra la base además de la validación estricta. `update` retira los destinos
obsoletos del candidato conservando evidencia histórica. El desarrollador no
recibe permiso de escritura OpenSpec; cada cliente conserva su propio árbol,
separado del harness.

## Compatibilidad, drenaje y rollback del workflow

El contrato de workflow se fija por intento junto con su procedencia. Los
históricos conservan registros, mensajes y modalidad original sin inventar
categorías, candidatos o verificaciones ausentes. Un intento activo anterior
continúa solo bajo un contrato compatible; si no puede recuperarse, se detiene
con diagnóstico y requiere un nuevo intento explícito. No migrar silenciosamente
aprobaciones históricas al workflow de corrección.

Antes de actualizar una instalación, drenar intentos activos o identificar
explícitamente los que conservan el workflow anterior. Conservar el paquete
previo y todos los checkpoints/evidencias para rollback. Un runtime anterior que
no entiende `correcting` no debe reanudar automáticamente esos intentos:
restaurar un runtime compatible o crear un nuevo intento con planificación y
aprobación propias. La recuperación de `correcting` exige compatibilidad de
plan, perfil, catálogo, candidato y evidencia, más checkpoint y lease/CAS; el
retry humano conserva comprobaciones de `failure_id`, revisión e identidad y
no se habilita automáticamente para todos los fallos nuevos. Publicar o
desplegar una versión requiere el procedimiento operativo autorizado; la
verificación local de este cambio no equivale a despliegue ni smoke remoto.

## Fallos del planner y reintento

El planner usa un límite de salida por rol de 64.000 tokens; otros roles conservan
el fallback de 12.000. La configuración confiable declara capacidades por endpoint;
el harness comprueba entrada más reserva de salida sin reducir silenciosamente
límites ni instrucciones. El límite de log sigue siendo 64.000 caracteres y su
recorte no indica truncamiento del modelo. Los límites de artefacto y permisos
siguen aplicándose aunque la respuesta permitida sea mayor.

El JSON por esquema se solicita cuando el endpoint está comprobado y habilitado.
Se distinguen output_truncated (terminación por límite), malformed_json y
invalid_contract. Sin finish_reason se conserva su ausencia. JSON completo con
CR/LF/tab literales en cadenas cerradas admite escape sintáctico conservador;
no se inventan cierres ni valores, y claves duplicadas se rechazan. Si aún falla
la serialización de una respuesta final completa del planner, puede realizarse
una sola llamada adicional de corrección, vinculada a la original. No se recuperan
automáticamente truncamientos, contratos inválidos ni solicitudes de contexto
mal formadas. Contrato, manifiesto, política y OpenSpec siguen siendo obligatorios.

Un fallo persiste failed con etapa de origen, revisión, identidad y recuperabilidad.
La App muestra causa y Reintentar etapa cuando procede. El reintento humano
conserva aclaraciones y evidencia, restaura el checkpoint íntegro y puede regenerar
artefactos de esa etapa. El plan resultante requiere aprobación vigente. Reiniciar
la App no reintenta fallos persistidos ni históricos con último evento de error.
Retry comprueba failure_id, revisión, perfil, contexto y procedencia; lease/CAS
impide trabajadores duplicados. Si falla el almacenamiento o se pierde el lease,
se conserva el checkpoint previo y se diagnostica sin fabricar una transición.

Las llamadas agregan finish_reason, effective_max_tokens, acceptance,
parent_call_id/recovery_index y huellas de normalización. La evidencia íntegra de
respuesta se conserva en snapshots protegidos del almacén existente; no se expone
por el hilo. Cada llamada real mantiene usage/costo estimado propio; normalización
local no genera una llamada ficticia. Los históricos admiten campos ausentes.

## Registros, costos y retención

La [guía de gestión de contexto](gestion-contexto.md) define contratos por rol,
selección, cache, vigencia de decisiones, presupuesto, activación y rollback.
La política del producto está deshabilitada por defecto; una instalación verificada
puede habilitarla para intentos nuevos. Los históricos conservan su modalidad.

`runs/<run_id>.json` usa contrato v5; `attempts[]` conserva etapa, revisión, SHA base, mensajes, eventos, aprobaciones, publicación y checkpoint. `runs/agent_calls/<run_id>-<call_id>.json` usa contrato v3; contiene `run_id`, `attempt_id`, rol, etapa, revisión, modelo, estado, tiempos, tokens y `estimated_cost_usd` cuando existe `usage`. Una llamada fallida o sin `usage` tiene costo ausente, no cero. Los registros v3 de ejecución y v2 de llamadas siguen legibles para consultas históricas. [harness_costs_by_call.sql](sql/harness_costs_by_call.sql) une ejecución y llamadas por **ambos** `run_id` y `attempt_id`; `call_id` identifica cada invocación. Los precios YAML son supuestos, no facturación real.

Los artefactos redactados viven en `runs/openspec/`; los checkpoints de bytes exactos y diffs de revisión se almacenan por separado en el volumen UC. El operador debe restringir `READ_VOLUME` y `WRITE_VOLUME` a las identidades autorizadas, definir retención y borrado según la política del cliente, y conservar checkpoints de intentos activos y PR pendientes. Un registro histórico puede consultarse sin migrarlo; la coordinación nueva comienza en la tabla Delta. Si el JSON y la tabla divergen, la recuperación usa el checkpoint cuyo identificador coincide con la tabla y rechaza contenido alterado. Nunca borrar manualmente un checkpoint activo para resolver un error.
## Contrato del planner y representación de artefactos

En proposal de `general_patch`, `manifest` contiene exclusivamente operaciones de
código y pruebas admitidas por el perfil. Las rutas OpenSpec se describen en el
impacto de la propuesta y las gestiona el harness durante planificación, sync y
archive; no se incluyen como operaciones del desarrollador. Specs, design y
tasks reciben su contrato de contenido sin heredar campos obligatorios de
proposal. La estrategia acotada conserva su propio contrato.

`content` se serializa una sola vez dentro del JSON externo. Por ejemplo,
`{"content":"## Why\n\nMotivo.\n\n## Impact\nCódigo y pruebas."}` produce un documento
con saltos reales después de interpretar JSON. Una segunda serialización deja
separadores literales y no cumple la estructura Markdown. El harness comprueba
la estructura requerida antes de guardar el artefacto, preserva escapes
legítimos dentro de ejemplos y mantiene la validación OpenSpec estricta del plan.
El schema JSON verifica forma de salida, no permisos ni validez del documento.

Un error de manifiesto identifica el artefacto, índice de entrada y restricción,
por ejemplo `proposal, entrada 3: OpenSpec se gestiona fuera del manifiesto de
código`. Las rutas recibidas del modelo permanecen en la respuesta protegida;
el error público no reproduce arbitrariamente esas cadenas. Un defecto del
documento identifica el artefacto y su representación o estructura requerida.
Ambos se clasifican como `invalid_contract`: no se filtran operaciones ni se
reinterpreta el texto para aparentar éxito, y no generan otra llamada automática.
Para fallos nuevos de presentación (encabezados o representación Markdown), el
diagnóstico identifica el artefacto y los títulos requeridos ausentes, ordenados,
acotados y redactados. El planner recibe los encabezados canónicos de su plantilla
CLI y debe conservarlos literalmente; el cuerpo se redacta en español. Esta
instrucción y validación se aplican en propose/update con el gestor de contexto
habilitado o deshabilitado. Specs y tasks conservan sus estructuras propias.

Los defectos de presentación nuevos permiten Reintentar etapa por acción humana
con identidad autorizada, failure_id, revisión, perfil, contexto, procedencia,
checkpoint y lease/CAS vigentes. Se conservan evidencias y artefactos parciales,
sin tratarlos como un plan aprobado. El plan regenerado exige aprobación vigente.
El reinicio mantiene failed sin nuevas llamadas. No se convierten denegaciones
de política, manifiestos inválidos o presupuestos incompatibles en errores
recuperables de presentación. Los históricos conservan mensaje y retryable;
`9f4d553d17ea406ca596600875735656` permanece no reintentable y repetir su HU
requiere una ejecución nueva.

Una respuesta final completa del planner con texto externo al JSON puede admitir
una sola llamada correctora cuando se demuestre un único objeto completo, sin
duplicados ni context_request, con contrato, Markdown y política válidos. Ese
objeto se comprueba solo para elegibilidad: no se acepta por extracción. La
corrección debe devolver únicamente JSON y preservar exactamente sus valores y
tipos; se valida de nuevo antes de aceptar el artefacto y el plan sigue pasando
OpenSpec estricto. Varios objetos, ambigüedad, contenido truncado o un contrato
inválido impiden esa corrección. Los controles literales y recuperación de
serialización anteriores conservan su alcance; el tope total es una llamada
correctora por respuesta, sin recuperación recursiva ni presupuestos nuevos.

XML o texto externo a una solicitud de contexto del explorador o planner produce
malformed_json, sin lecturas ni corrección automática: solo reintento humano
controlado. Ambas llamadas reales de una corrección final conservan call_id,
parent_call_id/recovery_index, hashes y snapshots protegidos; la original conserva
su aceptación rechazada. Cada llamada registra su uso y costo estimado propio
cuando existe usage, y costo ausente cuando no existe. Fallos de almacenamiento
detienen la operación sin fabricar aceptación ni perder el checkpoint previo.
Los errores históricos conservan su mensaje original. La consulta de llamadas
permite localizar `call_id` y `response_evidence_sha256` para revisar el original
con los permisos existentes. Los presupuestos y reglas de retry no cambian.

## Contrato explícito del desarrollador

Cada llamada de aplicación o corrección recibe `developer_output_contract`
con formas, reglas y ejemplos derivados de los tipos del editor. Se conserva
durante lecturas sucesivas, con el gestor de contexto habilitado o deshabilitado.
El catálogo `role-contracts-v6` registra la nueva procedencia; la compatibilidad
de intentos previos sigue sujeta a los controles existentes, sin reanudación
automática ni cambio retroactivo de mensajes.

`create` exige `op`, `path` y `content`, archivo ausente y hash previo ausente o
null. `modify` exige además `expected_sha256` de los bytes actuales leídos.
`delete` exige ese hash y contenido ausente o null. El contenido es el archivo
completo UTF-8, no un diff. `base_sha256` y otros campos desconocidos se rechazan
antes de escribir; los ejemplos no autorizan rutas fuera del manifiesto o perfil.

En `classified-corrections-v1`, `coverage` declara exactamente una entrada por
ruta: `applied` corresponde a una operación propuesta y no acredita ejecución
ni pruebas; `already_conformant` requiere hash vigente sin edición; `blocked`
requiere motivo. Para un borrado ya conforme, el hash prueba sus bytes exactos
de base. `coverage.sha256` acredita evidencia y no reemplaza el hash de edición.
Una lista vacía de operaciones con cobertura válida sigue pasando por pruebas
y Sonnet. Históricos sin esa modalidad conservan su contrato sin cobertura
obligatoria, y `silver_safe_ratio` conserva `expression` y `notes`.

Los nuevos errores de forma identifican índice y campos canónicos o una etiqueta
genérica segura, sin contenido, valores sensibles ni rutas arbitrarias. Ambas
modalidades registran aceptación rechazada y conservan el original protegido,
usage/costo por llamada cuando existen y el reintento humano vigente. No se
renombran campos ni se agrega una llamada correctora. Denegaciones de política,
hashes obsoletos y errores de persistencia mantienen sus controles propios.

## Solicitudes individuales de contexto

El modelo solicita una sola operación por turno, exclusivamente mediante
context_request como objeto. Las formas admitidas son:

```json
{"context_request":{"op":"list_tree"}}
{"context_request":{"op":"read_file","path":"src/common/schema.py"}}
{"context_request":{"op":"search_text","query":"normalize_table_name"}}
```

Cada línea corresponde a una respuesta distinta. list_tree no recibe path;
search_text recibe solo op y query. Después del resultado puede solicitar otra
operación o devolver el contrato final del rol sin context_request. Listas, null,
campos adicionales y solicitudes mezcladas con salida final se rechazan antes
de leer, con acceptance=invalid_contract y diagnóstico seguro.

Los nuevos fallos de formato admiten Reintentar etapa por acción humana con
identidad, failure_id, revisión, perfil, contexto, procedencia y checkpoint
compatibles. Un reinicio no los reintenta automáticamente. Los históricos
con retryable=false conservan su mensaje y estado; para repetir ese caso se
presenta una HU nueva con planificación y aprobación propias. Política,
permisos, presupuestos y tratamiento de denegaciones siguen vigentes.
