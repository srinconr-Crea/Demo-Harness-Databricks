# Contrato de contexto y Sonnet 5.5

## Alcance

Cambio `harden-context-contract-and-upgrade-sonnet-55`. El run original `fa0d8173517049358f53871d45c49117` permanece como evidencia histórica, sin reejecución ni modificación. Esta evidencia separa pruebas locales, consultas del operador y verificación operativa; disponibilidad no equivale a despliegue.

## Tarifas estimadas

Consulta del 5 de octubre de 2026: la [tabla oficial de Databricks](https://www.databricks.com/product/pricing/proprietary-foundation-model-serving) publica para Sonnet 5 y 5.5 tasas globales de 28.571 DBU por millón de tokens de entrada y 142.857 de salida. La [API de precios minoristas de Azure](https://prices.azure.com/api/retail/prices) devuelve USD 0.07 para `Premium Serverless Realtime Inferencing DBU`, región `eastus2`, tipo Consumption; meterId `743ac278-9ce3-5ec1-b10c-21edeeef5943`, fecha de vigencia `2023-04-01`.

La multiplicación y redondeo produce USD 2 por millón de entrada y USD 10 de salida. Se configura como supuesto global estimado específico de Sonnet 5.5, no precio contractual ni facturación real. La tarifa publicada aplica un 10% adicional si se habilita procesamiento regional; descuentos, caché y cambios de región requieren actualizar el supuesto. Haiku conserva la estimación previa del operador del 25 de septiembre; no se recalculan llamadas históricas. Sin usage el costo permanece ausente.

La respuesta completa del calculador y las solicitudes sintéticas se conservan localmente bajo `.deployments/sonnet55-retail-pricing.json` y `.deployments/sonnet55-smoke.json` (fuera de Git); no contienen datos cliente ni credenciales.

## Endpoint real, identidad del operador

Perfil seleccionado: CREA_DEV. Endpoint `databricks-claude-sonnet-5-5`, estado READY. El operador tiene CAN_MANAGE. Esto no prueba permisos de la App.

La prueba específica de JSON Schema fue rechazada por Databricks con `INVALID_PARAMETER_VALUE`: la traducción de structured output requiere uso forzado de tools que este modelo rechaza. Se conserva `json_schema: false`; las validaciones del harness permanecen obligatorias. La llamada fallida tiene su propio registro, sin usage/costo ficticios.

Dos pruebas textuales breves con `max_tokens=64000` terminaron con `finish_reason=stop`:

| call_id | Contrato | Tokens entrada/salida |
| --- | --- | --- |
| 9e1989739845441cbc60220553bd1fa7 | context_request individual read_file | 460 / 27 |
| 61bc96fbbc7746d58aa921ef57bf69fe | content Markdown final | 466 / 177 |

Las pruebas usaron exclusivamente texto sintético y Foundation Model API del workspace. No exigieron generar 64.000 tokens ni invocaron recursos NaturaPet.

## Verificación local y operativa

Resultados de suite, revisión, paquete, permisos y despliegue se completan conforme se ejecutan. La migración operativa no se considera comprobada hasta verificar la identidad de la App y su smoke sintético. El paquete anterior y su source_code_path se conservan para rollback; no se borran registros ni checkpoints.

### Recorrido integrado local

Run sintético `2dafa1c422344727b5d98dc581e35dcd`, CLI OpenSpec real 1.13.2, estado final complete. Modelos y GitHub simulados; pruebas del candidato ejecutadas por el runner local aislado. Una lista inválida falla sin lecturas; el reintento humano recupera exploring, se responden aclaraciones y se espera aprobación vigente del plan antes de aplicar, verificar, sincronizar, archivar y simular el PR. No se publicó ningún PR real. Se actualizó el fixture para respetar las secciones obligatorias de los templates reales de design/tasks.

### Paquete y revisión

Paquete completo `context-sonnet55-final-20261005`: `databricks bundle validate --strict -t dev --profile CREA_DEV` terminó con Validation OK. Perfil aprobado sin cambios: SHA256 `27ac71c9b2c0c3bdea588ee77d06df20eedb228fbf47002121404f6f7f0df01f`. Solo se desplegará la App del harness, conservando warehouse, tabla de estado, volúmenes y Job sandbox actuales.

La revisión independiente detectó aceptación de roles obligatorios omitidos por default. Se corrigió y añadieron 12 casos de configuración ausente/incompatible. `git diff --check` sin errores tras retirar un salto sobrante del fixture. Los cambios locales previos de preparación NaturaPet y su archivo OpenSpec anterior se excluyen del commit de este cambio.

Paquete previo de rollback: `/Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-planner-artifact-contracts-20261005`, deployment `01f1c0f73ddc1fe38977f34d011b2b9e`. Para rollback, restaurar recurso CAN_QUERY de Sonnet 5 y desplegar ese paquete completo; conservar todos los registros/checkpoints. No reutilizar el routing nuevo con el paquete antiguo.

### Pendientes antes de operación

El usuario autorizó explícitamente archivar/push antes de desplegar. La identidad/permisos reales de la App y smoke operativo se comprobarán después del primer push y se incorporarán en un commit de evidencia. No se admitirá el paquete como operativo antes de esos resultados. La App estaba STOPPED; la consulta de registros confirmó cero queued/running. Las HUs esperando interacción permanecen sin avance automático.

### Suite y especificaciones

Suite completa: 316 passed, 0 failed (cuatro grupos aislados: 66 + 85 + 67 + 98). Se usó el Python del entorno del proyecto con pytest -q -p no:cacheprovider y temporales cortos de Windows; el comando uv equivalente no pudo acceder al caché desde el sandbox. Sin fallos en la repetición final. Advertencia existente de deprecación Starlette/httpx; no altera los resultados.

OpenSpec validate del cambio en modo strict: válido. `validate --specs --strict`: 15 passed, 0 failed. Se sincronizaron agent-prompt-contracts, change-planning y observability-control; los bloques de delta se compararon con las especificaciones principales y se preservaron sus demás requisitos. Implementación localizada en prompt_contracts/repo_context/context_manager, models/config, pruebas de contrato/recovery y empaquetado. El archivo mantiene explícitas las comprobaciones operativas 4.2 y 5.4 hasta el despliegue autorizado.
