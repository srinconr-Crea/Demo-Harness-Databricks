# Tasks

## 1. Contrato confiable y salida específica

- [x] 1.1 Reforzar y versionar el contrato planner en config/defaults/prompts.yaml con separación OpenSpec/manifiesto y serialización única; verificar en tests/test_context_manager.py los textos efectivos, versión/hash por llamada y ausencia de autoridad añadida por contenido cliente.
- [x] 1.2 Especializar los prompts de openspec.py por artefacto/estrategia y añadir un ejemplo serializado correctamente; verificar en tests/test_openspec.py/tests/test_integrations.py proposal general_patch, specs/design/tasks y silver_safe_ratio, incluyendo propose y update.
- [x] 1.3 Coordinar, si es necesario, el schema en repo_context.py con el contrato específico sin bloquear context_request; verificar solicitudes de lectura de specs, campos finales obligatorios y endpoint sin soporte de schema con fixtures, manteniendo los controles posteriores al parseo.
- [x] 1.4 Documentar separación de artefactos y manifiesto, serialización única y límites de garantía del schema en docs/operacion.md; verificar que los ejemplos JSON producen Markdown con saltos reales al interpretarse una sola vez.

## 2. Validación común del manifiesto y diagnóstico

- [x] 2.1 Compartir la validación del manifiesto entre prompt_contracts.py y openspec.py y detectar entradas OpenSpec con motivo específico; verificar aceptación de código/pruebas permitidos y rechazo de mezcla OpenSpec, campos/tipos, operación, traversal, ruta prohibida, extensión, duplicados y límites en pruebas de contratos/planificación.
- [x] 2.2 Añadir diagnóstico de artefacto, índice y motivo con ruta solo cuando sea segura, usando redacción vigente y evidencia protegida existente; verificar mensajes distinguibles, referencia a llamada y ausencia de datos restringidos en tests/test_response_recovery.py/tests/test_integrations.py.
- [x] 2.3 Documentar el significado del rechazo y cómo consultar la evidencia en docs/operacion.md; verificar ejemplos para la tercera entrada OpenSpec y un histórico sin campos nuevos, sin cambiar perfiles ni filtrar operaciones prohibidas.

## 3. Representación y estructura Markdown

- [x] 3.1 Introducir comprobación compartida de la estructura requerida por contrato/instrucciones confiables antes de escribir el artefacto; verificar en tests/test_openspec.py la reproducción sintética del documento doblemente serializado, secciones reales ausentes y encabezados dentro de bloques de código que no satisfacen la estructura.
- [x] 3.2 Preservar contenido legítimo sin decodificación adicional; verificar LF/CRLF, acentos, comillas, barras, secuencias literales en bloques/ejemplos y estructuras válidas de proposal/specs/design/tasks, con igual resultado en las rutas con y sin gestor.
- [x] 3.3 Mantener invalid_contract y evidencia de la respuesta rechazada, sin invocar recuperación automática de contrato; verificar número de llamadas, ausencia de artefacto aceptado para esa salida y conservación de los casos previos de normalización sintáctica y truncamiento en tests/test_response_recovery.py.
- [x] 3.4 Documentar representación inválida y conservación de escapes legítimos en docs/operacion.md; verificar que los ejemplos y diagnósticos coinciden con el comportamiento implementado y no prometen reparar automáticamente un contrato inválido.

## 4. Integración y controles finales

- [x] 4.1 Añadir un recorrido sintético de conversación que acepta un artefacto y rechaza el siguiente por representación/manifiesto; verificar failed/checkpoint parcial, aclaraciones conservadas, ausencia de developer/PR y ausencia de llamadas extra con tests/test_conversation.py/tests/test_conversation_webapp.py.
- [x] 4.2 Ejecutar la matriz propose/update, general_patch/silver_safe_ratio y contexto habilitado/deshabilitado con contenido conforme a las instrucciones; verificar validación estricta OpenSpec del plan válido y persistencia/diagnóstico equivalentes del plan rechazado.
- [x] 4.3 Ejecutar la suite completa con `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider` y `openspec validate fix-planner-artifact-contracts --strict`; registrar comandos, revisión y resultados reales, documentando un ejecutor equivalente si el sandbox impide uv/cache y diferenciando fixtures de evidencia remota.
- [x] 4.4 Revisar el diff final contra las tres delta specs, el alcance y los cambios preexistentes; verificar que no se alteraron perfiles, 64000 tokens, permisos, reglas de retry, infraestructura ni la HU real. Si el alcance autorizado se amplía a bundle/recursos, validar además el bundle con target/perfil autorizado antes de publicar.
