# Proposal

## Why

El intento `9f4d553d17ea406ca596600875735656` falló primero porque el explorador antepuso XML al JSON y, tras un reintento humano, porque el planner tradujo `What Changes` como `Qué cambia`. El rechazo del encabezado se reprodujo y desapareció al corregir únicamente ese título: necesitamos contratos de presentación explícitos, diagnóstico específico y recuperación acotada sin debilitar los controles del harness.

## What Changes

- Exigir al planner los encabezados canónicos de la plantilla CLI, literalmente y con el cuerpo en español, tanto en propose como update y con el gestor de contexto habilitado o deshabilitado.
- Identificar los encabezados requeridos ausentes mediante diagnóstico seguro, conservando la validación Markdown y OpenSpec estricta; no traducir ni normalizar silenciosamente el documento.
- Distinguir defectos de presentación de denegaciones de política y habilitar reintento humano de etapa para los primeros mediante los controles existentes.
- Ampliar la recuperación finita de serialización del planner para una respuesta final completa precedida o seguida por texto ajeno al JSON, mediante como máximo una llamada adicional, vinculada y nuevamente validada. No aceptar JSON extraído arbitrariamente.
- Mantener solicitudes de contexto con texto/XML extra como fallos sin lectura ni reparación automática, recuperables por acción humana.
- Conservar respuestas originales, aceptación, checkpoint, procedencia, uso y costo por llamada. Los históricos mantienen sus errores y recuperabilidad originales.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `agent-prompt-contracts`: instrucciones canónicas por artefacto disponibles en ambos recorridos del gestor de contexto.
- `change-planning`: ampliación acotada de recuperación de serialización final y clasificación de presentación Markdown, conservando los rechazos de política y contrato.
- `observability-control`: diagnóstico de encabezados faltantes y reintento humano específico de presentación, con trazabilidad y compatibilidad histórica.

## Impact

- Runtime: `harness/prompt_contracts.py`, `openspec.py`, `repo_context.py`, `skills.py`, `context_manager.py` y `conversation.py`, bajo `src/agents/harness/`; catálogo confiable `config/defaults/prompts.yaml`.
- Evidencia y consulta: contratos de llamada y persistencia existentes, `app/start_server.py` y endpoints/interfaz de recuperación, solo si resulta necesario transportar el diagnóstico seguro; no se propone migración de almacenamiento.
- Pruebas: regresiones específicas en `tests/test_planner_artifact_contracts.py`, `test_response_recovery.py`, `test_context_manager.py`, `test_context_request_contract.py` y pruebas de conversación. Suite local completa antes de publicar.
- Documentación operativa: actualizar `docs/operacion.md` con elegibilidad de corrección y retry; sincronizar specs únicamente después de implementar y verificar.
- Exclusiones: habilitar JSON Schema del endpoint, cambiar modelos o presupuestos, infraestructura, recursos NaturaPet, reparación automática de contexto, aplicar la HU original, reescribir históricos, merge o despliegue.
- Estado: propuesta de comportamiento, sin implementación ni validación remota del cambio. Base de análisis del harness: `71d13dd9dd1e3831e18a7862128be8177737d32a`.
