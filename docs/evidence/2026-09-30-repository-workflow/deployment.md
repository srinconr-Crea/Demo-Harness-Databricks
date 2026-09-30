# Despliegue del flujo general de OpenSpec

Despliegue autorizado por el usuario el 30/09/2026, sobre el target `dev` y el perfil `CREA_DEV`. Código registrado en el commit `5c17078`, rama `Db_Spec_Harness`, repositorio `srinconr-Crea/Demo-Harness-Databricks`.

## Bundle y App

- `databricks bundle deploy -t dev --profile CREA_DEV --auto-approve --fail-on-active-runs`: correcto. Actualizó App, Job sandbox y grants del volumen sandbox; cero recursos creados o eliminados. No modificó recursos NaturaPet.
- `databricks bundle run harness -t dev --profile CREA_DEV`: correcto.
- App: `demo-dbx-harness-mvp`.
- Deployment ID: `01f1bd193cfe1edcb280957879350789`.
- Estado confirmado: despliegue `SUCCEEDED`, App `RUNNING`, compute `ACTIVE`.
- Actualización del despliegue: 30/09/2026 16:52:50 America/Bogota; startup de Uvicorn confirmado en logs a las 16:53:00.
- URL: https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com
- Consulta autenticada a `/`: HTTP 200, presente el texto de la nueva interfaz de aprobación de propuesta y continuación automática.
- Consulta autenticada a `/configuration`: HTTP 200.

## Job sandbox real

Se ejecutó `scripts/smoke_sandbox.py` sobre el Job `611081415041874`, verificando que su identidad `dac4cb01-380f-4af5-b594-132d6d693beb` es diferente de la identidad de la App. Solo se usó el volumen `demo_harness_databricks_dev.dev_srinconr_demo_harness_databricks.demo_harness_sandbox`.

- Run `460706929298818`: caso positivo aprobado; dos pruebas correctas, resultado sintético esperado y entorno sin credenciales de la App. El README no confiable no ejecutó su instrucción.
- Run `505496185981591`: caso negativo rechazado correctamente; una aserción sintética falló y `passed` quedó `false`.

## Evidencia y límites

La suite local previa al despliegue terminó con 143 pruebas aprobadas y una omitida por PySpark ausente. El cambio OpenSpec y las diez specs principales validaron en modo estricto.

El arranque registró dos avisos de recuperación correspondientes a registros históricos sin `attempts` ni versión de esquema. Esos registros son finales (uno complete y otro failed); se conservaron intactos y no hay una HU activa afectada. La App terminó su startup y respondió correctamente.

El perfil activo sigue siendo `naturapet`, conservando su estrategia `silver_safe_ratio`; la política general no se activa implícitamente en ese cliente. La validación de bundles cliente sigue requiriendo CLI y autenticación sandbox provisionadas antes de habilitar el adaptador. Esta prueba real no envió HUs a NaturaPet ni invocó modelos o creó PRs cliente. La App se dejó encendida para revisión del usuario.
