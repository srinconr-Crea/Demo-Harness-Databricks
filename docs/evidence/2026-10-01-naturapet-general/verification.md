# Perfil general de NaturaPet

Cambio solicitado por el usuario el 01/10/2026, para publicar en `Db_Spec_Harness` y desplegar la App del harness.

## Configuración

El perfil `naturapet` versión 3 habilita exclusivamente `general_patch` con alcance de repositorio, operaciones create/modify/delete y nueve tipos de archivo. Mantiene protegidos gobierno de GitHub, skills, OpenSpec, secretos y datos. Los límites son 40 archivos, 2 MB por candidato, 50 lecturas y 400 KB de contexto. El explorador y desarrollador reciben la política completa, incluido el alcance repository.

Los YAML compartidos mantienen los modelos y precios existentes; actualizan las instrucciones de roles, el límite de salida a 12000 tokens y el registro resumido a 64000 caracteres. Las instrucciones de fase siguen procediendo de skills y CLI. El runner permite importar módulos del checkout mediante `pytest -o pythonpath=.` conservando `python -I`, plugins deshabilitados y entorno sin credenciales de la App.

## Comprobaciones realizadas

- Develop de NaturaPet consultado en SHA `9c48831022a329902f765058de37e6d0a1528eb7`; no se modificó ni publicó el repositorio cliente.
- Suite cliente existente: 14 pruebas locales correctas en Python aislado. Antes del ajuste, la colección fallaba con `No module named src`.
- Job dedicado `611081415041874`, run `512273624896935`: 14 pruebas cliente correctas; identidad distinta de la App. Paquete SHA-256 `d56fd32f0fd9133138089da8c649211b4b8b6ca032765edd8ef3c09d8507eb8f`.
- Controles remotos: run `290903720426167`, caso positivo y ausencia de credenciales aprobados (2 pruebas); run `579118734488184`, aserción negativa rechazada correctamente (`passed: false`).
- Pruebas focalizadas de política, contratos y sandbox: 25 correctas.
- Suite completa del harness: 158 aprobadas, 1 omitida por PySpark ausente, 720.29 segundos. Advertencia existente de Starlette/TestClient. Reporte local ignorado: `.tmp/naturapet-general-tests.xml`.
- Bundle del harness: validación estricta correcta.
- OpenSpec: 11 specs correctas.

## Despliegue de la App

- Perfil CREA_DEV, target dev, App `demo-dbx-harness-mvp`.
- Código sincronizado mediante bundle sync; deployment SNAPSHOT `01f1bdbabaef1e199ab29a2fca9e8e8c`, estado SUCCEEDED. No se actualizaron recursos, permisos ni identidad del Job.
- App RUNNING y compute ACTIVE, con los once recursos existentes y ocho variables conservados.
- Startup completo de Uvicorn: 2026-10-01 17:08:53 UTC (12:08:53 America/Bogota).
- Consultas autenticadas `/` y `/configuration`: HTTP 200. Perfil naturapet, estrategias exactamente `["general_patch"]`.
- URL: https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com

Los dos avisos de recuperación de históricos ValueError ya observados en despliegues anteriores siguen presentes. El startup finalizó correctamente. No se enviaron HUs ni llamadas LLM reales ni se crearon PRs cliente. La App se dejó encendida para la prueba del usuario.

## Requisitos antes de una HU

La base consultada aún no contiene OpenSpec ni las skills. Integrar un PR manual en `develop` con OpenSpec 1.13.2, los siete workflows requeridos y contexto/reglas del proyecto. No basta un init con los workflows core si falta verify, update o sync.

`tests/` es el objetivo funcional configurado. Las 14 regresiones actuales pasan, pero una nueva regla de negocio necesita pruebas sintéticas propias. La App no ejecuta recursos ni datos reales de NaturaPet.

Las HUs que afectan `databricks.yml` o `resources/` requieren CLI Databricks y autenticación aislada en el sandbox para validar el target existente `dev`. El Job actual declara pytest y no provisiona ese validador; dichas HUs bloquearán publicación hasta completar esa preparación. Código puro, configuración ajena al bundle y documentación pueden probarse con los validadores existentes, sujeto a las pruebas y al plan aprobado.
