# Operación del MVP

## Recursos y acceso

- Workspace Azure: `https://adb-7405606739630987.7.azuredatabricks.net`.
- App: `demo-dbx-harness-mvp`; URL: `https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com`.
- Catálogo propio: `demo_harness_databricks_dev`, con esquema y volumen gestionados por el bundle.
- SQL warehouse aislado: `demo-harness-sandbox-wh` (`9e696889dea65361`).
- GitHub App: `naturapet-databricks-harness-mvp` (App ID `5075619`, Installation ID `164865183`), instalada solo en `srinconr-Crea/Naturapet_DLH`.
- Secret scope: `demo-harness-databricks`, clave `github-app-private-key`. Contiene la clave PEM de la GitHub App; nunca se versiona.

El bundle de desarrollo se despliega con `databricks bundle deploy -t dev --profile CREA_DEV`. Después se publica el código de la App con `databricks bundle run harness -t dev --profile CREA_DEV`. Para detenerla: `databricks apps stop demo-dbx-harness-mvp --profile CREA_DEV`. El archivo `iniciar-harness.bat` vuelve a encenderla y abre su URL.

## HU piloto y segunda ejecución

En el piloto original, el formulario venía precargado con `NP-001`. El flujo comprobó `develop`, editó `notebooks/comercial/silver/04_business_derivations.ipynb`, validó sintaxis Python y tres filas sintéticas en el warehouse aislado, pidió revisión al modelo Haiku y creó `feature/np-001-margen-sobre-costo-en-silver-comercial` y su PR.

La versión actual deja el formulario vacío y obtiene `columna = numerador / denominador` de la HU. El perfil `config/clients/naturapet.yaml` conserva únicamente el repositorio, la rama, la instalación GitHub App, el notebook, la tabla, la columna ancla y la lista de columnas de origen permitidas. La estrategia `silver_safe_ratio` edita una sola columna con `safe_divide`; cualquier otra clase de cambio sigue bloqueada. Antes de reutilizar una rama o PR, el cliente comprueba que el conjunto completo de archivos cambiados coincida con los archivos validados.

La validación remota ejecuta una expresión SQL equivalente, sin DDL ni datos de NaturaPet. No ejecuta el notebook PySpark ni la CI del repositorio cliente. Es una limitación que debe constar en la revisión humana del PR.

## Contratos y recuperación

El catálogo `demo_harness_databricks_dev` contiene el volumen `artifacts`. La ruta real del esquema en desarrollo puede llevar prefijo de usuario; la App toma el valor resuelto de `RUN_STORE_DIR`. Cada HU guarda `runs/<run_id>.json` con versión de esquema, HU completa, perfil y versión, repositorio, estado, intentos, fechas UTC, archivos cambiados y resultado. Cada respuesta de agente guarda `runs/agent_calls/<run_id>-<call_id>.json` con `run_id`, `attempt_id`, `call_id`, rol, modelo, respuesta, tokens, fecha UTC, costo estimado en USD y origen de la tarifa. La unión de una ejecución con sus costos usa `run_id` y `attempt_id`; `call_id` identifica cada llamada sin ambigüedad. Son archivos JSON del volumen UC, no tablas Delta.

Al iniciar, la App marca como `interrupted` los registros `queued` o `running` de un proceso anterior. Reenviar la misma HU crea un nuevo `attempt_id` y conserva el historial anterior. La revisión del volumen antes de estos cambios encontró dos registros de NP-001: uno `failed` y uno `complete`; ninguno estaba pendiente. Los registros previos permanecen sin migración automática al contrato v2.

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

El consumo facturado de modelos se busca en `system.billing.usage` con `sku_name = 'PREMIUM_ANTHROPIC_MODEL_SERVING'` y `usage_type = 'TOKEN'`. Ese uso se registra en DBU y no equivale al costo estimado en USD del contrato. En la revisión de NP-002, la tabla de facturación solo contenía eventos del 2026-09-28 hasta las 15:00 UTC, mientras la HU corrió entre las 19:14 y 19:15 UTC; todavía no era posible conciliarla con la factura.

## GitHub App y secreto

La GitHub App usa un token de instalación de corta duración. Su clave privada se cargó al secreto `github-app-private-key` por stdin, sin imprimirla ni versionarla. Al renovar la clave, conserva el mismo procedimiento. La App solicita permisos `Contents` y `Pull requests` de lectura/escritura, y `Metadata` de lectura. No tiene webhooks y solo está instalada en NaturaPet.

## Incorporar otro proyecto

1. Crear un perfil YAML nuevo siguiendo `config/clients/naturapet.yaml`, con repo, rama base, rutas permitidas y contexto del proyecto; seleccionar su nombre con `HARNESS_CLIENT_PROFILE` en el despliegue. No colocar fórmulas de HU en el perfil.
2. Crear una instalación de GitHub App con alcance exclusivo para ese repositorio y un secreto dedicado.
3. Reutilizar `silver_safe_ratio` solo si el notebook cumple su contrato estructural, o implementar un editor y pruebas deterministas para otra clase de cambio.
4. Crear o asignar sandbox remoto separado; verificar permisos de App y costo.
5. Ejecutar pruebas locales, `bundle validate`, y un piloto sin merge automático.

La configuración de otro cliente por sí sola no activa tipos de cambio nuevos: cada estrategia debe contar con editor, validadores y pruebas antes de permitir publicación.
