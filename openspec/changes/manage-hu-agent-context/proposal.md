# Proposal

## Why

La App ya persiste aclaraciones, aprobaciones y checkpoints, recupera archivos bajo presupuesto y compone skills con un system prompt común. Sin embargo, no existe una política explícita y verificable que decida cuándo recuperar fuentes, reutilizar cache, consultar memoria o compactar, ni contratos versionados de prompts por rol y fase.

## What Changes

- Introducir un gestor de contexto por HU con árbol de decisión determinista y evidencia de cada elección.
- Incorporar cache de lecturas derivadas con invalidación por identidad de cliente, perfil, repositorio, revisión del checkout y hashes de fuentes.
- Mantener memoria estructurada de decisiones confirmadas dentro de cada HU; excluir memoria automática entre HUs y clientes.
- Evaluar compactación por presupuesto y redundancia, conservando restricciones, preguntas y referencias exactas a aprobaciones, sin resumirlas como autoridad.
- Versionar system prompts por rol/fase con rol, restricciones y contrato de salida; aplicar validación determinista a respuestas.
- Integrar recuperación, procedencia, costos, compatibilidad histórica y pruebas de regresión en el flujo actual.
- Mantener modelos y pruebas obligatorios, Haiku asesor, sandbox separado y publicación autorizada por el plan vigente.

## Capabilities

### New Capabilities

- `conversation-context`: selección de contexto, cache, memoria por HU, compactación verificable y reconstrucción tras reinicios.
- `agent-prompt-contracts`: prompts confiables versionados por rol/fase y salidas validadas, sin elevación de autoridad por contenido recuperado.

### Modified Capabilities

- `observability-control`: añadir trazabilidad de decisiones de contexto, prompts, compactaciones y llamadas auxiliares sin alterar los requisitos existentes.

## Impact

`harness/conversation.py`, `repo_context.py`, `skills.py`, `models.py`, `contracts.py`, `store.py`, configuración de roles/contexto, documentación y pruebas. Se proponen módulos `context_manager.py` y `prompt_contracts.py`; sus nombres son decisiones de diseño revisables. Sin nuevo servicio externo, índice vectorial ni recurso Databricks obligatorio. Campos persistentes opcionales para históricos y activación explícita para intentos nuevos. La propuesta `establish-project-context` puede implementarse antes o después: el runtime usa OpenSpec del cliente y no depende de reformatear el contexto del producto.
