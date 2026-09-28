# Plan de implementación: trazabilidad, control y reutilización del harness

Fecha: 2026-09-28. Estado: implementación local revisada; pendiente despliegue y prueba de extremo a extremo en Databricks.

## Avance de la implementación

Se implementaron contratos por HU, intento y llamada, entradas/salidas redactadas, identificadores de solicitud, eventos de gates, consulta SQL, cancelación cooperativa, parada con identidad del usuario, UI actualizada, tareas de agentes en YAML, registro de estrategia y un segundo perfil de prueba. CI incorpora una prueba PySpark sintética y una instantánea de checks del PR. `docs/agents/agent-spec.json` fue validado con la skill `creating-databricks-agents`.

La suite local valida el flujo sin acceso a PySpark/Java; ese caso corre en CI. El warehouse y la App estaban detenidos en el preflight y el bundle aún no está desplegado. Quedan para el siguiente piloto la comprobación de `client_request_id` y seguimiento de uso real, la autorización efectiva de `apps`/`CAN MANAGE`, la ejecución de la consulta SQL sobre el volumen y una HU sintética. Las trazas MLflow no se conectaron al flujo FastAPI; los eventos JSON son la evidencia actual.

## Objetivo y límites

Conservar el piloto NaturaPet que recibe una HU, valida una razón segura y abre un PR sin merge. Añadir trazabilidad consultable por HU, intento y llamada; control cooperativo de cancelación; parada de la App autorizada por Databricks; validación más cercana al código que se publica; y una vía comprobable para incorporar otra estrategia y otro proyecto.

La App actual sigue siendo una sola App FastAPI. `analyst`, `developer` y `verifier` son llamadas a modelos dentro de un orquestador determinista; no son Apps independientes ni tienen herramientas propias. El editor local aplica el cambio y el cliente GitHub publica la rama y el PR. Separar roles en Apps solo se justificaría si sus permisos o ciclos de despliegue debieran ser independientes.

Este diseño aplica la skill instalada `creating-databricks-agents` desde esta revisión: declarar rol, entradas, salida estructurada, evidencia, capacidades, identidad, fallos y observabilidad antes de extender agentes; empezar por la App existente y conservar contratos aptos para un futuro Supervisor. La iteración NP-002 no había invocado explícitamente esa skill. Para la UI y autorización de la App Python se usó también `databricks-apps-python`.

La implementación debe respetar `AGENTS.md`: recursos `demo_harness_*`, warehouse aislado, GitHub App restringida, rama `feature/*` del cliente y PR hacia `develop`; nunca merge ni escritura en recursos NaturaPet. No copiar el bundle al repositorio cliente.

## Decisiones de diseño

1. **Contrato canónico.** Versionar `RunContract` y `AgentCallContract`. Cada intento conserva de forma inmutable estado, tiempos, archivos cambiados, resultado, error y progreso de publicación. El resumen de nivel `run` puede señalar el intento más reciente, pero las consultas históricas unen por `run_id` y `attempt_id` contra el intento correspondiente.
2. **Entradas y salidas consultables.** Cada llamada guarda `input_text` (prompt realmente enviado), `output_text` (respuesta realmente recibida), `parsed_output` validado, huella SHA-256, fechas, duración, estado, tokens y costo estimado. Los campos de texto se limitan y se redactan antes de persistir si contienen secretos; el volumen UC conserva ACL y política de retención. El JSON sigue siendo la fuente canónica, y una vista SQL puede exponer los campos en una fila por llamada.
3. **Conciliación.** Generar `call_id` antes de invocar el endpoint y enviarlo como `client_request_id` cuando el endpoint lo admita. Registrar también `databricks_request_id` si está disponible. Verificar en el workspace que el seguimiento `system.serving.endpoint_usage` esté habilitado y visible para la identidad de consulta. Unir allí por identificador de solicitud. `system.billing.usage` se consulta por SKU, endpoint y ventana para reconciliación agregada; no se atribuye automáticamente una fila facturada a una llamada individual.
4. **Cancelación cooperativa.** Una solicitud en cola pasa a `cancelled` sin invocar modelos. Una solicitud en curso registra `cancel_requested_at` y `requested_by`; el flujo consulta esa marca después de cada llamada externa y antes de entrar a publicación. Una llamada ya iniciada puede terminar. Una vez iniciada la publicación, se deja concluir o fallar y se registra el estado real de rama, commit y PR; nunca se informa `cancelled` ocultando un PR creado.
5. **Parada de App.** Solo se ofrece tras un estado final (`complete`, `failed`, `cancelled`, `interrupted`). El servidor lo comprueba de nuevo y usa `x-forwarded-access-token` del solicitante con el scope `apps` para llamar a la API de parada de la App configurada; Databricks aplica `CAN MANAGE`. Se persiste el evento de auditoría antes de llamar a la API, sin almacenar el token. Si el workspace no permite ese scope o el usuario carece de permiso, devolver 403 y mantener la App activa.
6. **Validación y evaluación.** Mantener el gate SQL sintético y añadir una prueba PySpark local del fragmento de notebook transformado sobre datos sintéticos, más lectura de checks del PR. Incorporar un conjunto pequeño de HU exitosas, inválidas, fallidas y canceladas, con resultados medibles y vínculo a trazas/eventos. No presentar la prueba local como ejecución de todo el pipeline NaturaPet.
7. **Portabilidad.** El perfil YAML define repositorio, instalación, rutas, estrategia y recursos autorizados. Un registro de estrategias selecciona editor y validadores por `kind`; cada nuevo tipo requiere pruebas propias. Parametrizar warehouse, endpoints y perfil en el bundle. Probar con un segundo perfil y fixture de repositorio independiente antes de anunciar soporte multicliente.

## Fase 1: contratos y costo por llamada

### Tarea 1. Formalizar roles y contratos de datos

- Archivos: `src/agents/harness/harness/contracts.py`, `src/agents/harness/harness/workflow.py`, `tests/test_contracts.py`, `tests/test_workflow.py`, y una especificación de roles bajo `docs/agents/`.
- Especificar entradas y salidas JSON para analista (`valid`, `notes`, evidencia), desarrollador (`expression`, `notes`) y verificador (`approved`, `notes`, hallazgos). Completar y validar una copia versionada de `agent-spec.json` según `creating-databricks-agents`. Aplicar validación Pydantic antes de cualquier gate o publicación. El desarrollador propone; el editor determinista escribe.
- Ampliar `RunAttempt` con `changed_files`, `result`, `publication` y cancelación. Al reintentar, conservar los valores del intento anterior y comenzar un intento vacío. Mantener lectura de JSON v1/v2.
- Pruebas: dos intentos de una misma HU conservan costos, respuestas y archivos propios; salida inválida de cada rol falla cerrado; registros legados siguen consultables.

### Tarea 2. Registrar entrada, salida e identificador antes de invocar

- Archivos: `src/agents/harness/harness/models.py`, `src/agents/harness/app/start_server.py`, `src/agents/harness/harness/store.py`, `tests/test_integrations.py`, `tests/test_store.py`.
- Cambiar el contrato de `ModelClient.complete(role, prompt, *, call_id, max_tokens=...)` para enviar `client_request_id=call_id`, guardar inicio y fin, registrar errores de endpoint sin inventar tokens ni costo, y persistir `input_text`, `output_text`, `parsed_output` y `request_id` cuando exista. No registrar credenciales ni claves. Validar tamaño y redacción antes de escribir en UC.
- Pruebas: el identificador enviado coincide con el JSON; una respuesta y una excepción producen registros distintos y consultables; el costo queda `null` cuando no llega `usage`.

### Tarea 3. Conciliar y consultar

- Archivos: `docs/operacion.md`, nueva consulta SQL versionada bajo `docs/sql/`, y prueba de estructura del contrato en `tests/test_contracts.py`.
- Preflight de solo lectura: comprobar disponibilidad, permisos y columnas de `system.serving.endpoint_usage`; no habilitar una función ni cambiar ACL sin revisión de permisos. La consulta devuelve una fila por `run_id` + `attempt_id` + `call_id`, con HU, archivos, rol, modelo, entrada, salida, tokens, costo estimado y uso del endpoint cuando exista. Separar los totales de facturación de `system.billing.usage`.
- Criterio: los tres registros de NP-002 siguen visibles como legado sin join exacto retrospectivo; una llamada nueva con ID correlacionable se une sin usar hora aproximada.

## Fase 2: cancelar HU y detener App

### Tarea 4. Cancelación y publicación observable

- Archivos: `src/agents/harness/harness/webapp.py`, `src/agents/harness/harness/workflow.py`, `src/agents/harness/harness/github.py`, `tests/test_webapp.py`, `tests/test_workflow.py`, `tests/test_integrations.py`.
- Añadir `POST /runs/{run_id}/cancel`. Rechazar estados finales; para `queued`, terminar el intento; para `running`, persistir solicitud y comprobarla en puntos seguros. Registrar etapas `not_started`, `branch_created`, `file_pushed`, `pr_created`, incluidos SHA y URL cuando existan. La cancelación antes de publicar garantiza que no se invoque `create_feature_pr`; si la publicación empezó, el resultado refleja los artefactos reales.
- Pruebas: cancelar en cola no llama modelos; cancelar durante analista, desarrollador, sandbox y verificador impide iniciar la etapa siguiente; carrera con inicio de publicación no produce un falso `cancelled`; un reinicio conserva solicitud y progreso.

### Tarea 5. Parada autorizada y controles de interfaz

- Archivos: `src/agents/harness/harness/webapp.py`, `src/agents/harness/app/start_server.py`, `src/agents/harness/app/index.html`, `databricks.yml`, `tests/test_webapp.py`.
- Añadir `POST /app/stop` vinculado al `run_id`, únicamente en estado final y con nombre de App tomado de configuración del servidor. Usar token de usuario reenviado y scope `apps`; la llamada de gestión debe ejecutarse con identidad del usuario, nunca con la identidad de servicio. Guardar actor, hora, resultado solicitado y error saneado en registro de auditoría antes de la parada.
- Preflight: confirmar en el workspace que la autorización de usuario y el scope `apps` están permitidos, y que la API exige el permiso esperado. Validar bundle y permisos efectivos antes de desplegar.
- La UI muestra **Cancelar HU** solo en `queued`/`running`, **Detener App** solo en terminal, y el progreso de cancelación/publicación. Mantener mensajes accesibles, distinguir solicitud de parada de parada confirmada y no mostrar tokens.
- Pruebas: 401 si falta token, 403 si Databricks niega permisos, 409 si hay HU activa, y llamada de parada únicamente con el token del solicitante.

## Fase 3: validación y reutilización

### Tarea 6. Prueba del código transformado y checks del PR

- Archivos: `src/agents/harness/harness/notebook_edit.py`, `src/agents/harness/harness/sandbox.py`, `src/agents/harness/harness/github.py`, `tests/test_notebook_edit.py`, `tests/test_sandbox.py`, `tests/test_integrations.py`.
- Ejecutar con PySpark local el código objetivo extraído del notebook transformado y filas sintéticas para positivo, cero y NULL. Comparar el resultado con la regla de la HU y registrar evidencia. Consultar checks del commit/PR sin hacer merge; reportar `pending`, `passed` o `failed` de manera separada al gate previo a publicar.
- Criterio: un notebook sintácticamente válido que calcule mal falla; los checks pendientes no se presentan como aprobados.

### Tarea 7. Estrategias y segundo perfil

- Archivos: `src/agents/harness/harness/contracts.py`, `src/agents/harness/harness/workflow.py`, módulo nuevo `src/agents/harness/harness/strategies/`, `src/agents/harness/config/clients/`, `databricks.yml`, pruebas de contratos y flujo.
- Extraer `silver_safe_ratio` detrás de una interfaz de estrategia (`parse`, `edit`, `validate`) sin ampliar sus permisos. El bundle toma perfil, warehouse y endpoints de variables/recursos; YAML no contiene fórmulas de HU. Añadir un perfil y un fixture de repositorio independientes para demostrar aislamiento y rechazo cruzado de rutas; cualquier segunda estrategia requiere editor y pruebas propias antes de habilitar GitHub.
- Criterio: cambiar de perfil no cambia código Python y una HU de otro perfil no puede escribir en NaturaPet.

## Fase 4: evaluación, documentación y entrega

### Tarea 8. Evaluación y observabilidad

- Archivos: `src/agents/harness/eval/`, `src/agents/harness/harness/` para eventos, `docs/operacion.md` y pruebas de evaluación.
- Vincular `run_id`, `attempt_id` y `call_id` a eventos o trazas MLflow del flujo real, sin asumir que `agent.py`, `graph.py` o `eval/` del scaffold ya lo observan. Crear casos de HU válida, ambigua, fuera de alcance, fallo de modelo, fallo de sandbox y cancelación. Medir tasa de PR correcto, rechazos seguros, duración y costo por éxito; revisar una muestra de trazas antes de ampliar autonomía.
- Criterio: se puede explicar desde los registros qué recibió y respondió cada rol, qué gate decidió y qué llegó a GitHub.

### Tarea 9. Gates de entrega

- Archivos: `.github/workflows/harness-ci.yml`, `README.md`, `docs/operacion.md`, evidencia de cada fase.
- Ejecutar pruebas focalizadas por tarea, suite completa al cierre de fases, lint, `databricks bundle validate --strict -t dev` y plan de bundle con perfil explícito. Revisar permisos y diffs antes de desplegar. Tras autorización de despliegue, hacer smoke corto, una HU sintética y revisión de logs/ACL. Publicar el harness solo tras CI verde; la publicación de código cliente sigue siendo PR sin merge.
- Evidencia por fase: alcance, comandos, resultado, hallazgos nuevos, riesgo residual y siguiente gate.

## Riesgos a revisar antes de implementar

- Compatibilidad real de `client_request_id` y disponibilidad de `system.serving.endpoint_usage` para los endpoints pay-per-token del workspace.
- Privilegios y scope `apps` de la autorización en nombre del usuario, especialmente la respuesta del navegador al detener su propia App.
- Escrituras concurrentes en JSON sobre volumen UC durante reintentos, cancelación y callback de modelos; elegir serialización o almacenamiento transaccional si el preflight muestra más de una instancia activa.
- Tamaño, confidencialidad y retención de entradas y salidas que incluyen HU, fragmentos de código y diffs.
- Viabilidad de ejecutar el fragmento PySpark del notebook objetivo sin recursos NaturaPet ni dependencias privadas inesperadas.

## Referencias de viabilidad

- [Autorización de usuario y scope `apps` en Databricks Apps](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/auth).
- [Permisos `CAN USE` y `CAN MANAGE` para Databricks Apps](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/permissions).
- [Seguimiento por solicitud y `client_request_id`](https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/configure-ai-gateway-endpoints).
- [Latencia y alcance de `system.billing.usage`](https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing).
