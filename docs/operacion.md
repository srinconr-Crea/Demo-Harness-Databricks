# Operación del Databricks Development Harness

## Recursos y acceso

- Workspace Azure: `https://adb-7405606739630987.7.azuredatabricks.net`.
- App: `demo-dbx-harness-mvp`; URL: `https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com`.
- Catálogo propio: `demo_harness_databricks_dev`, con esquema y volumen gestionados por el bundle.
- SQL warehouse aislado: `demo-harness-sandbox-wh` (`9e696889dea65361`).
- GitHub App: `naturapet-databricks-harness-mvp` (App ID `5075619`, Installation ID `164865183`), instalada solo en `srinconr-Crea/Naturapet_DLH`.
- Secret scope: `demo-harness-databricks`, clave `github-app-private-key`. Contiene la clave PEM de la GitHub App; nunca se versiona.

El bundle de desarrollo se despliega con `databricks bundle deploy -t dev --profile CREA_DEV`. Después se publica el código de la App con `databricks bundle run harness -t dev --profile CREA_DEV`. Para detenerla: `databricks apps stop demo-dbx-harness-mvp --profile CREA_DEV`. El archivo `iniciar-harness.bat` vuelve a encenderla y abre su URL.

## HU piloto y segunda ejecución

### Flujo actual con OpenSpec

Cada intento toma el commit de la rama base del cliente y carga su árbol `openspec/` en un workspace temporal aislado. Ejecuta `openspec init --tools none` antes de cualquier llamada al desarrollador. Si el cliente aún no tiene OpenSpec, crea `openspec/config.yaml` con repositorio, rama, estrategia y notebook del perfil; si ya lo tiene, conserva su configuración y specs. El perfil debe declarar `openspec_root: openspec`.

El planner llama cuatro veces a `databricks-claude-sonnet-5` para producir propuesta, spec, diseño y tareas a partir de la HU, el perfil y las instrucciones de OpenSpec. `openspec validate --strict` y los controles deterministas deben aprobar el plan antes del editor. El desarrollador recibe esos artefactos; después de las pruebas sintéticas, el verificador los revisa junto al diff. El cambio OpenSpec se archiva y el notebook, la configuración, las specs resultantes y el historial del cambio se publican en un único commit de `feature/*` y en un PR. Una persona revisa el PR; el harness no hace merge ni despliega el cliente.

El estado y las huellas del plan aparecen en `GET /runs/{run_id}`, dentro de `attempts[].openspec`. Cada entrada de `artifacts` contiene un `artifact_id`; el contenido redactado se consulta con `GET /runs/{run_id}/openspec/{attempt_id}/{artifact_id}`. Los JSON completos están en `runs/openspec/<run_id>/<attempt_id>/<artifact_id>.json` del volumen UC. Una respuesta fallida conserva los artefactos ya generados y los eventos que alcanzaron a registrarse; un reintento recibe otro `attempt_id` y otro cambio OpenSpec. El volumen mantiene los mismos controles de acceso y retención que los demás registros.

Las cuatro llamadas Sonnet del planner se registran en `runs/agent_calls/` con `role = planner`, identificadores, tiempos, tokens y `estimated_cost_usd` cuando el endpoint entrega `usage`; un fallo o la ausencia de `usage` no se convierte en costo cero. Los JSON históricos con `role = analyst` siguen legibles. Para consultar costos por intento, use [harness_costs_by_call.sql](sql/harness_costs_by_call.sql).

En el piloto original, el formulario venía precargado con `NP-001`. El flujo comprobó `develop`, editó `notebooks/comercial/silver/04_business_derivations.ipynb`, validó sintaxis Python y tres filas sintéticas en el warehouse aislado, pidió revisión al modelo Haiku y creó `feature/np-001-margen-sobre-costo-en-silver-comercial` y su PR.

La versión actual deja el formulario vacío y obtiene `columna = numerador / denominador` de la HU. El perfil `config/clients/naturapet.yaml` conserva únicamente el repositorio, la rama, la instalación GitHub App, el notebook, la tabla, la columna ancla y la lista de columnas de origen permitidas. La estrategia `silver_safe_ratio` edita una sola columna con `safe_divide`; cualquier otra clase de cambio sigue bloqueada. Antes de reutilizar una rama o PR, el cliente comprueba que el conjunto completo de archivos cambiados coincida con los archivos validados.

La validación remota ejecuta una expresión SQL equivalente, sin DDL ni datos de NaturaPet. CI ejecuta además el fragmento editado de un notebook sintético en PySpark local con Java 17. Ninguna prueba ejecuta el pipeline completo de NaturaPet. Después de crear el PR, el harness consulta una instantánea de checks; `pending` o `unavailable` nunca se presenta como `passed`.

## Contratos y recuperación

El catálogo `demo_harness_databricks_dev` contiene el volumen `artifacts`. La ruta real del esquema en desarrollo puede llevar prefijo de usuario; la App toma el valor resuelto de `RUN_STORE_DIR`. Cada HU guarda `runs/<run_id>.json` con versión de esquema, HU completa, perfil y versión, repositorio, estado, fechas UTC y una lista de intentos. Cada intento conserva sus archivos cambiados, resultado, eventos de gates, solicitud de cancelación y progreso de publicación. Cada llamada guarda `runs/agent_calls/<run_id>-<call_id>.json` con `run_id`, `attempt_id`, `call_id`, rol, modelo, entrada y salida redactadas y limitadas, huellas SHA-256, respuesta estructurada, tiempos, estado, tokens, costo estimado en USD e identificadores de solicitud. La unión histórica usa siempre `run_id` y `attempt_id`; `call_id` identifica cada llamada. Son JSON en el volumen UC, no tablas Delta.

Al iniciar, la App marca como `interrupted` los registros `queued` o `running` de un proceso anterior. Reenviar la misma HU crea un nuevo `attempt_id` y conserva el historial anterior. La revisión del volumen antes de estos cambios encontró dos registros de NP-001: uno `failed` y uno `complete`; ninguno estaba pendiente. Los registros previos siguen legibles sin migración automática. El contrato de ejecución actual es v3 y el de llamadas v2.

Cancelar una HU en cola la marca `cancelled` antes de ejecutar el runner. En curso, se registra quién lo pidió y la cancelación se aplica en el siguiente punto seguro. La llamada externa en curso puede terminar. Cuando comenzó la publicación, se guarda rama, commit y URL del PR que alcancen a crearse; la ejecución no se presenta como cancelada ocultando el PR. La parada de la App solo se ofrece después de un estado final, se registra antes de invocar la API y requiere el token reenviado del usuario y permiso `CAN MANAGE` en Databricks. El token no se persiste. Una respuesta `stop_requested` confirma la solicitud, no que la App ya esté detenida.

Las entradas y salidas pueden contener HU, fragmentos de código o diffs. El volumen debe tener ACL limitadas a operadores autorizados. El flujo redacta patrones de claves PEM y tokens Databricks y limita el texto con `config/defaults/runtime.yaml`; el operador debe fijar la retención y borrado de JSON de acuerdo con la política del proyecto antes de usar datos sensibles.

## Costos

Las capturas del calculador de Databricks muestran, en Azure US East 2 y bajo un ejemplo artificial de 43.200 peticiones al mes con 1 token de entrada y 1 de salida: Sonnet 5 USD 0,78/mes y Haiku 4.5 USD 0,39/mes. De esos valores se infieren tarifas aproximadas de USD 3/15 por millón de tokens de entrada/salida para Sonnet y USD 1,5/7,5 para Haiku. Están en `config/defaults/models.yaml` por endpoint; no sustituyen la factura real. El flujo registra por llamada tokens, respuesta, fecha y costo estimado cuando el endpoint informa `usage`. Warehouse y App generan costos adicionales no incluidos en ese cálculo. No hay límite monetario en el MVP.

### Comprobar uso de modelos después de una HU

El registro inmediato está en `runs/agent_calls/` del volumen UC; `system.billing.usage` es la fuente de consumo facturado y puede llegar después. Para NP-002 se comprobó el 2026-09-28 que las tres llamadas sumaban 10.540 tokens de entrada, 1.348 de salida y USD 0,048543 **estimados**. La consulta siguiente devuelve el detalle por agente en el esquema de desarrollo desplegado:

```sql
SELECT role, model, input_tokens, output_tokens,
       CAST(estimated_cost_usd AS DECIMAL(18, 9)) AS estimated_cost_usd,
       completed_at, run_id, attempt_id
FROM read_files(
  '/Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/artifacts/runs/agent_calls/',
  format => 'json'
)
WHERE story_id = 'NP-002'
ORDER BY completed_at;
```

Para unir una HU con sus llamadas, filtra los registros de `runs/` por `state IS NOT NULL` o por un estado concreto y une por **ambos** `run_id` y `attempt_id`. `read_files` sobre la carpeta padre puede incluir los JSON de `agent_calls/`; omitir ese filtro duplica filas y costos.

La consulta versionada [harness_costs_by_call.sql](sql/harness_costs_by_call.sql) devuelve una fila por llamada con HU, intento, agente, entrada, salida, archivos del mismo intento y costo estimado. Define `:runs_path` como el patrón `.../runs/*.json` y `:calls_path` como `.../runs/agent_calls/*.json` del volumen resuelto por el bundle. El [join opcional con endpoint_usage](sql/harness_endpoint_usage_join.sql) requiere seguimiento de solicitudes habilitado y acceso a la tabla de sistema. La tabla existe en el workspace, pero su configuración de seguimiento y filas para estos endpoints aún no se ha comprobado; NP-002 es anterior al envío de `client_request_id` y no admite join exacto retrospectivo. `system.billing.usage` sigue separado de costos estimados por llamada.

El consumo facturado de modelos se busca en `system.billing.usage` con `sku_name = 'PREMIUM_ANTHROPIC_MODEL_SERVING'` y `usage_type = 'TOKEN'`. Ese uso se registra en DBU y no equivale al costo estimado en USD del contrato. En la revisión de NP-002, la tabla de facturación solo contenía eventos del 2026-09-28 hasta las 15:00 UTC, mientras la HU corrió entre las 19:14 y 19:15 UTC; todavía no era posible conciliarla con la factura.

## GitHub App y secreto

La GitHub App usa un token de instalación de corta duración. Su clave privada se cargó al secreto `github-app-private-key` por stdin, sin imprimirla ni versionarla. Al renovar la clave, conserva el mismo procedimiento. La App solicita permisos `Contents` y `Pull requests` de lectura/escritura, y `Metadata` de lectura. No tiene webhooks y solo está instalada en NaturaPet. La lectura opcional de checks solicita un token separado con `Checks: read`; como ese permiso aún no está concedido a la instalación piloto, el resultado puede ser `unavailable` sin bloquear el PR. Para verlo, agregar solo `Checks: read` a la GitHub App y volver a consentir la instalación. GitHub [documenta ese permiso para listar checks](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference).

## Incorporar otro proyecto

1. Crear un perfil YAML nuevo siguiendo `config/clients/naturapet.yaml`, con repo, rama base, rutas permitidas y contexto del proyecto; seleccionar su nombre con `HARNESS_CLIENT_PROFILE` en el despliegue. No colocar fórmulas de HU en el perfil.
2. Crear una instalación de GitHub App con alcance exclusivo para ese repositorio y un secreto dedicado.
3. Reutilizar `silver_safe_ratio` solo si el notebook cumple su contrato estructural, o implementar un editor y pruebas deterministas para otra clase de cambio.
4. Crear o asignar sandbox remoto separado; verificar permisos de App y costo.
5. Ejecutar pruebas locales, `bundle validate`, y un piloto sin merge automático.

El registro de editores está en `harness/strategies.py`. Un segundo perfil sintético en `tests/fixtures/clients/independent.yaml` prueba aislamiento de rutas sin una segunda instalación real ni permisos de producción. Nuevas clases de HU exigen un editor, validadores y pruebas antes de registrarse.

## Estado de la entrega

El código y la configuración de esta iteración se publican en la rama `MVP-Databricks-Harness`. El preflight de solo lectura del 2026-09-28 encontró la App `demo-dbx-harness-mvp` detenida y con scopes efectivos de identidad básicos; el scope `apps` del bundle todavía no está desplegado. El warehouse de sandbox estaba detenido. Por eso no se ejecutaron consultas SQL nuevas ni una HU en Databricks durante esta entrega. Antes del siguiente piloto: revisar el plan del bundle, desplegar la App con `user_api_scopes: [apps]`, comprobar el consentimiento y `CAN MANAGE` para el operador, activar o verificar seguimiento de uso por solicitud y ejecutar una HU sintética. La evaluación automática de los JSON está en `harness/evaluation.py`; las trazas MLflow del flujo FastAPI todavía no están conectadas.

La configuración de otro cliente por sí sola no activa tipos de cambio nuevos: cada estrategia debe contar con editor, validadores y pruebas antes de permitir publicación.
