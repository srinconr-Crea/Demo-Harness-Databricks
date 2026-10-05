# Verificación de recuperación del planner

Cambio: `fix-planner-response-recovery`. Rama solicitada: `Db_Spec_Harness`.
Base de trabajo: `4225017d6f042b71f50b4dd0f8034b3e21f874d5`.

## Comportamiento verificado

Planner usa 64000 tokens configurables, con fallback global de 12000 y reserva
de contexto. Se distinguen respuesta truncada, JSON mal formado y contrato
inválido. La normalización local conserva el texto y la recuperación por modelo
permite una sola llamada adicional, enlazada con su evidencia y costo propio.
Los contratos, rutas, procedencia, aprobación y controles OpenSpec siguen
aplicándose después de recuperar una respuesta.

Los fallos persistidos conservan etapa de origen, revisión, identidad,
recuperabilidad, aclaraciones y checkpoint parcial. El retry comprueba esos datos
bajo coordinación; no puede retroceder una transición más reciente ni repetir
una publicación confirmada. Una revisión independiente encontró problemas de
concurrencia, conservación de comentarios y evidencia; se corrigieron y se
añadieron pruebas de regresión.

## Pruebas locales

Se usó el Python del entorno del proyecto para ejecutar pytest. El comando con
`uv run --project src/agents/harness --with pytest` no pudo acceder a su cache en
el sandbox. También se necesitaron permisos para los temporales de pytest y una
ruta temporal corta para evitar el límite de rutas Windows de un fixture.

La suite se ejecutó en cuatro grupos independientes por archivo, con
`src/agents/harness/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
--tb=short --basetemp <TEMP>/hfN <archivos>`. Los grupos con 49, 59 y 94 pruebas
pasaron. El cuarto grupo tuvo 48 éxitos y una expectativa histórica que asumía
estado activo tras un error de procedencia. Se actualizó esa expectativa a
`failed/preparation_error` y se verificó de nuevo su módulo completo. Tres
pruebas añadidas después de la colección inicial también se ejecutaron con éxito.
La colección final contiene 254 pruebas y todas pasaron: 250 en la ejecución
agrupada, la expectativa corregida en un módulo de 4 pruebas aprobado y las
3 pruebas adicionales. El módulo corregido tardó 249.28 segundos.

Las advertencias existentes de Starlette sobre httpx no son fallos.
`git diff --check`, `openspec validate fix-planner-response-recovery --strict` y
`openspec validate --specs --strict` pasaron (15 specs principales). El paquete
preparado también pasó `databricks bundle validate --strict -t dev --profile
CREA_DEV`; no se modificaron `databricks.yml` ni `resources/`.

La interfaz real se probó localmente con un fixture sintético: mostró Falló,
identificó propose como origen y dejó las etapas posteriores pendientes. Un clic
en Reintentar etapa llegó a revisión del plan conservando la aclaración Salida 2.
La captura local está en `.deployments/verification-final/ui-retry.png`.

## Comprobación remota acotada

Perfil autorizado: `CREA_DEV`. Endpoint:
`databricks-claude-sonnet-5`, en el workspace del harness.
Dos solicitudes sintéticas usaron `max_tokens: 64000`, `stream: false` y
`response_format: json_schema`; la segunda usó el esquema real del planner.

| Solicitud | finish_reason | Entrada | Salida | Duración | Costo estimado USD |
|---|---|---:|---:|---:|---:|
| Esquema mínimo | stop | 573 | 33 | 2.378 s | 0.002214 |
| Esquema del planner | stop | 773 | 38 | 2.296 s | 0.002889 |

El costo procede de precios configurados; no es facturación. Estas pruebas
confirman admisión del presupuesto y esquema, no duración ni calidad de una
salida de 64000 tokens. No se generó deliberadamente esa cantidad.
Las solicitudes y respuestas completas se guardaron localmente en
`.deployments/model-response-smoke-20261005.json` y
`.deployments/planner-schema-smoke-20261005.json`.

La consulta de ejecuciones encontró únicamente la HU indicada como activa con
último evento de error. El startup nuevo la conserva consultable y no la ejecuta
automáticamente. La HU real no se reintentó ni se modificó durante esta verificación.

## Publicación

Se sincronizaron y compararon las tres delta specs con sus specs principales.
Los 19 checks de tareas están completos; el cambio se archivó en
`openspec/changes/archive/2026-10-05-fix-planner-response-recovery/`.

El despliegue `01f1c0ef8c8c13cc8e201fe36aff476c` terminó en SUCCEEDED.
Fuente: `/Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-planner-recovery-20261005`.
Se conservó el app.yaml operativo, con sus referencias existentes y el mismo
hash de perfil; solo se desplegó código de la App mediante SNAPSHOT. El arranque
se confirmó en RUNNING y en logs a las 19:04:46 UTC. Una lectura del snapshot
confirmó que models.py coincide byte a byte con el paquete probado.
Después se detuvo la App y `apps get` confirmó compute_status STOPPED.

Para impedir que la versión anterior retomara la HU durante el inicio requerido
por Databricks, se reservó temporalmente su lease mediante CAS en la tabla de
coordinación del harness. El registro de la HU conservó su SHA-256
`e5c959da783fb013d600bfb2e7f87b490d7cca1981cfea53149b0accb492fac3`.
El primer helper falló por un nombre de argumento SDK; se corrigió y se completó
el despliegue con CLI. Databricks rechazó una parada durante el despliegue
pendiente; la parada posterior fue aceptada y verificada. La reserva se liberó
después de STOPPED, preservando etapa y checkpoint; los bytes de la HU quedaron
intactos. La evidencia operativa completa está en
`.deployments/guarded-deployment-evidence.json`.

Los cambios locales
preexistentes de preparación del cliente y del cambio OpenSpec anterior se
mantienen fuera de este commit. No se modifican recursos del cliente.
