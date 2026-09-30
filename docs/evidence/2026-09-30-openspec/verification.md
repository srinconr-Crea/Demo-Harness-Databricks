# Verificación del flujo conversacional OpenSpec

Fecha: 30 de septiembre de 2026. Cambio: `conversational-client-openspec-workflow`.

## Interfaz y API

Cliente sintético local `example/client`, checkout Git real fijado a SHA,
servidor FastAPI real y OpenSpec 1.13.2 real. Las respuestas de modelos y
la publicación GitHub son simuladas; no se crearon PR ni llamadas LLM externos.

El recorrido `76fd9be945fc486291ec36da980ca121` completó:

1. HU y descripción, exploración y aclaración.
2. Cuatro artefactos, validación estricta y revisión del plan.
3. Solicitud de cambios, revisión 2 y aprobación humana.
4. Apply, verificación determinista, sync/archive y revisión del diff.
5. Cambios al diff, restauración del checkpoint, revisión 3 y nueva aprobación.
6. Aprobación final, publicación simulada y recarga conservando el resultado.

La API registró 19 llamadas simuladas y tres aprobaciones. Los costos sin
uso real se muestran como no disponibles. Los checks del PR se mantuvieron
`pending`. El diff incluye `src/value.py`, specs sincronizados e historial
archivado. Las [capturas del diff](diff-review.png) y de la
[publicación simulada](publication.png) documentan los controles finales.

El módulo `tests/ui_harness_server.py` conserva datos entre reinicios, inyecta
una identidad solo en el servidor de pruebas y se enlaza exclusivamente a
`127.0.0.1`. No pertenece al código desplegado en la App.

Una segunda HU (`74af009e927b4784a1403c73a6598f66`) quedó en revisión del
plan mientras se reinició el servidor. Conservó el hash del plan y sus cuatro
artefactos, continuó hasta completar y guardó el SHA del commit publicado.
El historial terminó en `publication_complete` y registró un solo `pr_created`.
Una descripción con una etiqueta `img` y un manejador `onerror` se mostró como
texto, sin ejecutar HTML.

```powershell
src/agents/harness/.venv/Scripts/python.exe tests/ui_harness_server.py --data-dir .ui-preview-data/ui --port 8765
```

En Windows usar una carpeta corta para los datos; los checkpoints pueden
superar el límite de rutas de Windows con directorios de evidencia largos.

## Job sandbox real

- Workspace: `adb-7405606739630987.7.azuredatabricks.net`, perfil `CREA_DEV`.
- Job: `611081415041874`, `demo_harness_sandbox`.
- Identidad dedicada: `dac4cb01-380f-4af5-b594-132d6d693beb`.
- Identidad App distinta: `8910cd3e-32f6-4c75-b16f-b5ff3ea258d2`.
- Volumen: `demo_harness_databricks_dev.dev_srinconr_demo_harness_databricks.demo_harness_sandbox`.

Ejecución positiva `934798586729592`: dos pruebas pasaron. Comprobó ausencia
de variables Databricks, GitHub, AWS y Azure en el proceso pytest, plugins
automáticos deshabilitados y rechazo de una instrucción shell escrita en el
README del checkout. Ejecución negativa `202007151489708`: el Job terminó y
el resultado del adaptador fue `passed: false`; la prueba fallida no se aprobó.

La identidad tiene `USE_CATALOG` y `USE_SCHEMA` solo en los recursos del
harness, `READ_VOLUME`/`WRITE_VOLUME` en el volumen sandbox y `CAN_READ` en
el archivo del runner. La App tiene `CAN_MANAGE_RUN` en el Job. No se
concedieron secretos, modelos, volumen de registros ni recursos del cliente
a la identidad del Job. El usuario de despliegue conserva el rol User sobre
esa identidad para configurar `run_as`.

```powershell
src/agents/harness/.venv/Scripts/python.exe scripts/smoke_sandbox.py --profile CREA_DEV --job-id 611081415041874 --volume-dir /Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/demo_harness_sandbox
```

## Límite de la evidencia

Suite local: 99 pruebas aprobadas y una omitida. JavaScript del formulario:
`node --check` sin errores. Bundle de desarrollo: validación estricta aprobada.
Tras añadir la regresión de grants, cinco pruebas específicas de sandbox y API
también pasaron. El despliegue final `01f1bd0840391d799c359e06e9a23aa2`
terminó `SUCCEEDED`, la App quedó `RUNNING` y `/` y `/configuration` respondieron
HTTP 200. El HTML publicado coincide con el archivo local y el runtime tiene
bindings de la tabla de coordinación, Job y volumen sandbox.

Estas pruebas verifican el harness y un cliente sintético. La incorporación
de un repositorio cliente real requiere el PR de preparación, su merge humano
y un perfil con pruebas propias. El perfil desplegado `naturapet` conserva
`silver_safe_ratio`; las HUs generales se habilitan por cliente configurado.
