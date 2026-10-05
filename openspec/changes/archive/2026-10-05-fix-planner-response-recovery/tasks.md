# Tasks

## 1. Presupuestos y capacidades del modelo

- [x] 1.1 Extender la carga de configuración en models.py/start_server.py y defaults/agents.yaml con límites por rol (planner 64000, otros 12000) y capacidades confiables por endpoint; verificar fallback histórico, enteros inválidos y límites incompatibles con pruebas de configuración en tests/test_integrations.py.
- [x] 1.2 Retirar ambos overrides de 6000 en openspec.py y propagar el límite resuelto a context_manager.py y al recorrido sin gestor; verificar propose/update y silver_safe_ratio, reserva de contexto y rechazo previo a invocación con tests/test_openspec.py y tests/test_context_manager.py.
- [x] 1.3 Documentar límite efectivo, reserva, diferencia tokens/caracteres y activación por instalación en docs/operacion.md y docs/configuracion-instalacion.md; verificar que ejemplos concuerdan con los defaults y pruebas de carga.

## 2. Terminación, contratos y evidencia

- [x] 2.1 Añadir finish_reason, límite y aceptación opcionales en ModelResponse/AgentCallContract y propagación en start_server.py/store; verificar round trips de contratos históricos y nuevos con tests/test_contracts.py y tests/test_integrations.py, sin costo ficticio cuando falta usage.
- [x] 2.2 Clasificar output_truncated, malformed_json e invalid_contract en el recorrido del planner, distinguiendo truncamiento del log; verificar respuesta cortada en 6000, JSON válido pero contrato inválido y finish_reason ausente mediante fixtures deterministas.
- [x] 2.3 Añadir response_format condicionado por capacidad comprobada del endpoint y esquema compatible con contexto/final; verificar requests mediante FakeWorkspaceAPI, lecturas autorizadas, rechazo de error HTTP sin fallback silencioso y caso sin soporte. Mantener los controles de manifiesto y OpenSpec.
- [x] 2.4 Conservar respuesta original/normalizada mediante referencias y hashes protegidos y datos resumidos redactados; verificar secretos redactados, ACL/rutas existentes y diferenciación log/modelo en pruebas de persistencia. Documentar campos opcionales y diagnóstico en docs/operacion.md.

## 3. Recuperación acotada del JSON

- [x] 3.1 Implementar normalización con seguimiento de cadenas/escapes para CR/LF/tab y parser con rechazo de claves duplicadas; verificar LF literal, CRLF, comillas escapadas, barras invertidas, controles fuera de cadena, duplicados y cadena incompleta sin inventar contenido.
- [x] 3.2 Integrar recuperación de respuestas finales en ambas rutas del planner con máximo una llamada de corrección y parent_call_id/recovery_index; verificar éxito, segunda respuesta mal formada, contexto con varias rondas y ausencia de llamadas adicionales ante truncamiento, contrato inválido o política denegada.
- [x] 3.3 Revalidar salida recuperada con contrato, manifiesto, rutas y validación estricta OpenSpec; verificar rechazo de una reparación que amplía rutas o devuelve context_request en lugar del contrato final y que no se habilita apply antes de aprobación.
- [x] 3.4 Documentar normalizaciones permitidas, límite de recuperación y costo por llamada en docs/operacion.md; verificar dos registros/costos independientes y cero llamadas nuevas para una normalización local, usando tests/test_integrations.py y tests/test_openspec.py.

## 4. Persistencia del fallo y reintento coordinado

- [x] 4.1 Modelar failure con categoría, failed_stage, revisión, identidad y retryable, y persistir failed en conversation.py bajo lease/CAS; verificar fallo después de proposal, checkpoint parcial íntegro y evidencia consultable con tests/test_conversation.py y tests de coordinación/store existentes.
- [x] 4.2 Ajustar conversation_webapp.background para no duplicar ni sobrescribir fallos finalizados por el engine; verificar error de guardado, lease perdido y transición más reciente sin presentar persistencia exitosa.
- [x] 4.3 Implementar retry vigente de failed con restauración de etapa/checkpoint, limpieza de finished_at activo, evento trazable y una transición por identidad del fallo; verificar doble solicitud concurrente, revisión obsoleta, identidad no autorizada, cancelación y ausencia de publicación duplicada en tests/test_conversation_webapp.py/tests/test_conversation.py.
- [x] 4.4 Mantener recuperación histórica y controles de perfil, skills y política de contexto; verificar reinicio que conserva failed sin llamadas nuevas, históricos running/error, perfil distinto y checkpoint alterado. Documentar continuidad, regeneración de artefactos y rollback compatible en docs/operacion.md.

## 5. Interfaz y verificación integral

- [x] 5.1 Ajustar app/index.html y progress.py para causa legible, fase de origen fallida y botón Reintentar etapa basado en recuperabilidad; verificar flujo de fallo/retry mediante tests/test_conversation_webapp.py y fixture UI sintético existente, preservando aclaraciones y comentarios en edición. Actualizar la descripción operativa de esos estados en docs/operacion.md.
- [x] 5.2 Ejecutar la suite completa con `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider` y `openspec validate fix-planner-response-recovery --strict`; registrar revisión, comandos y resultados, diferenciando pruebas locales de evidencia remota.
- [x] 5.3 Antes de habilitar defaults en una instalación, comprobar en el endpoint del harness admisión de 64000, esquema Claude y timeout mediante metadata y smoke sintético acotado; registrar solicitud efectiva, finish_reason/usage y compatibilidad, sin generar deliberadamente 64000 tokens, reintentar la HU real ni usar recursos cliente. Si no hay acceso, dejar activación pendiente y documentar la limitación, sin afirmar compatibilidad.
- [x] 5.4 Revisar diff final y archivos previstos contra las tres delta specs y los límites del repositorio; verificar que cambios previos quedaron intactos y que no hay cambios de infraestructura. Si el alcance aprobado incorpora databricks.yml/resources, ejecutar además bundle validate --strict con target/perfil autorizado y registrar resultado antes de publicar.
