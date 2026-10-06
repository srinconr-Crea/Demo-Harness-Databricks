# Tasks

## 1. Contrato estructural explícito

- [x] 1.1 Agregar regresiones sintéticas en `test_planner_artifact_contracts.py` y `test_context_manager.py` que comprueben títulos canónicos y cuerpo en español en propose/update, ambos estados del gestor y contratos por artefacto/estrategia; verificar que fallen por ausencia de la nueva instrucción antes de implementarla.
- [x] 1.2 Compartir extracción de encabezados entre prompt y validador en `prompt_contracts.py`, entregar estructura propia por artefacto desde `openspec.py` y reforzar catálogo/recorrido mediado; verificar los tests de 1.1 y que context_request no requiera Markdown final.
- [x] 1.3 Actualizar versión/hash de prompts afectados y documentar en `docs/operacion.md` títulos literales y cuerpo en español; verificar procedencia de llamadas en ambos recorridos y que presupuestos incompatibles bloqueen sin truncar instrucciones.

## 2. Diagnóstico y reintento humano de presentación

- [x] 2.1 Agregar pruebas de propuesta con `Qué cambia`, serialización adicional y encabezados dentro de ejemplos, incluyendo título correcto y manifiesto prohibido combinado con Markdown inválido; verificar que el fallo identifique What Changes ausente y no clasifique una denegación de política como presentación recuperable.
- [x] 2.2 Introducir error específico de presentación y diagnóstico ordenado/acotado/redactado de títulos requeridos; preservar su clasificación por decorador, `repo_context.py`, `context_manager.py` y `conversation.py`; verificar acceptance=invalid_contract y retryable=true únicamente para presentación nueva con ambos estados del gestor.
- [x] 2.3 Agregar y pasar regresiones de conversación y endpoints para retry autorizado, fallo/revisión obsoletos, identidad no autorizada, checkpoint alterado, procedencia incompatible y trabajadores competidores; comprobar que los rechazos no generen llamadas y el plan regenerado espere aprobación vigente.
- [x] 2.4 Comprobar con tests reinicio sin llamadas, checkpoint parcial tras proposal válido y lectura histórica con retryable=false; documentar en `docs/operacion.md` alcance de retry y compatibilidad histórica, verificando que no se reescriban registros anteriores.

## 3. Recuperación finita de texto externo

- [x] 3.1 Agregar pruebas en `test_response_recovery.py` para objeto final con prefijo/sufijo externo, llaves y comillas dentro de cadenas, anidamiento, varios objetos, duplicados, cierre incompleto y finish_reason por límite; verificar elegibilidad conservadora y ausencia de corrección en casos ambiguos o truncados.
- [x] 3.2 Implementar detector léxico acotado y comprobación de contrato/Markdown/política del candidato final en `repo_context.py`, también sin gestor y para ambas estrategias; pasar 3.1 y demostrar que no se acepta por extracción ni se guarda como artefacto antes de corrección.
- [x] 3.3 Extender la única corrección de serialización existente con parent_call_id/recovery_index y comparación de valores JSON sensible a tipos; verificar éxito con respuesta idéntica y rechazo de contenido/manifiesto cambiado, solicitud de contexto, respuesta vacía, fallo de invocación y corrección agotada, con máximo dos llamadas totales.
- [x] 3.4 Agregar tests en `test_context_request_contract.py` para el XML observado antes de context_request del explorador y planner, con ambos estados del gestor; verificar malformed_json recuperable por acción humana, cero lecturas y cero llamadas de reparación automática.
- [x] 3.5 Verificar regresiones de controles literales, coma final y claves duplicadas existentes, además de un objeto con texto externo y ruta prohibida o encabezado ausente; comprobar que el envoltorio no habilite reparación automática de contratos inválidos ni transforme permisos.
- [x] 3.6 Verificar snapshots, hashes, aceptación original/corregida, vínculos y usage/costo propio de ambas llamadas, incluyendo usage ausente y fallos de persistencia; documentar elegibilidad, igualdad del objeto corregido y tope de una corrección en `docs/operacion.md`.

## 4. Verificación integrada

- [x] 4.1 Ejecutar la suite local completa con `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider` y conservar comando, revisión y resultados; comprobar además un flujo sintético que falle por presentación, reintente por acción humana y no aplique antes de aprobación vigente.
- [x] 4.2 Validar el cambio mediante `node src/agents/harness/node_modules/@fission-ai/openspec/bin/openspec.js validate harden-llm-response-contracts --strict` y revisar diff para confirmar que no cambia infraestructura, modelos, presupuestos ni recursos cliente; bundle validate no aplica al alcance actual y será obligatorio si un cambio posterior autorizado modifica bundle/resources.
- [x] 4.3 Registrar evidencia local y límites de verificación, revisar tareas completadas contra escenarios delta y preparar revisión del cambio; no atribuir despliegue ni smoke remoto. La activación de App y prueba sintética remota son acciones posteriores explícitas; sincronizar y archivar OpenSpec solo tras implementación verificada y el workflow correspondiente.
