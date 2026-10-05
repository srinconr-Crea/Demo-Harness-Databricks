# Proposal

## Why

La ejecución `c97a8f40a4eb4cfa973490f3b9ede340` superó el problema de JSON inválido, pero su nuevo intento falló porque el planner incluyó una delta OpenSpec en el manifiesto de código. La misma respuesta devolvió Markdown con 30 secuencias de salto de línea literales y ningún salto real: el contrato debe prevenir y diagnosticar ambos defectos antes de aceptar artefactos.

## What Changes

- Explicitar en los prompts y contratos del planner que el manifiesto contiene exclusivamente operaciones de código y pruebas admitidas por el perfil. Los artefactos OpenSpec se producen en el recorrido de planificación y no se incorporan como operaciones del desarrollador.
- Especializar la salida solicitada por artefacto y estrategia: summary/manifest son obligatorios para proposal general_patch; no se presentan como obligatorios para los otros artefactos.
- Exigir una sola serialización JSON: después de interpretar la respuesta, content debe ser Markdown con estructura y saltos reales conforme al artefacto. Preservar secuencias literales legítimas dentro del documento; no aplicar reemplazos globales ni decodificación adicional arbitraria.
- Validar la representación del Markdown antes de guardarlo como artefacto aceptado y mantener la validación estricta de OpenSpec del plan completo.
- Dar un diagnóstico que identifique la entrada y restricción incumplida del manifiesto, o el defecto de representación del contenido, con redacción segura y evidencia original protegida.
- Cubrir propose/update, contexto habilitado/deshabilitado y la regresión silver_safe_ratio. Conservar failed, checkpoints, aprobación humana y los límites existentes de recuperación.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `agent-prompt-contracts`: contrato específico que separa manifiesto de código y artefactos, con serialización única del contenido.
- `change-planning`: aceptación de Markdown estructurado sin reinterpretación indiscriminada de escapes y sin saneamiento silencioso de manifiestos prohibidos.
- `observability-control`: diagnóstico del rechazo enlazado a llamada, artefacto y evidencia protegida.

## Impact

Implementación prevista en `src/agents/harness/config/defaults/prompts.yaml`, `harness/prompt_contracts.py`, `harness/openspec.py` y, si lo exige la composición del schema, `harness/repo_context.py`. Pruebas en `tests/test_openspec.py`, `tests/test_context_manager.py`, `tests/test_response_recovery.py` y pruebas existentes de conversación/integración; documentación en `docs/operacion.md`.

No cambia el perfil cliente, sus rutas ni permisos, modelos, presupuesto de salida, infraestructura Databricks, formato público de acciones o autorización de publicación. No modifica ni reintenta la HU real. La propuesta no implementa, despliega ni publica cambios.
