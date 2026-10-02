# Proposal

## Why

La App persiste aclaraciones y checkpoints, pero reenvía contexto acumulado y utiliza un system prompt común sin selección verificable por rol. Se adopta la opción 2 acordada: gestor determinista que preserve decisiones y fuentes vigentes; la compactación asistida queda para otro cambio.

## What Changes

- Seleccionar contexto por HU, rol y fase según aplicabilidad, vigencia y presupuesto, con razones auditables.
- Incorporar cache de lecturas/búsquedas por intento, invalidada por perfil, contenido del candidato e inventario; separar I/O de tokens.
- Conservar decisiones estructuradas con origen, sustituciones y conflictos; distinguir vigencia de memoria, TTL de cache y retención de evidencia.
- Reducir contexto mediante deduplicación exacta, eliminación de derivaciones obsoletas y selección pertinente, sin resumen semántico LLM.
- Versionar prompts y contratos de herramientas/salidas para explorer, planner, developer, openspec_verifier obligatorio y verifier asesor.
- Integrar recuperación, compatibilidad histórica y evaluación comparable; conservar modelos, pruebas, sandbox y publicación autorizada por el plan vigente.

## Capabilities

### New Capabilities

- `conversation-context`: selección y reducción deterministas, cache, memoria por HU con ciclo de vigencia y reconstrucción.
- `agent-prompt-contracts`: prompts por rol/fase y contratos de herramientas y salidas, sin elevar contenido recuperado a autoridad.

### Modified Capabilities

- `observability-control`: trazabilidad de selección, invalidación, reducción y prompts, sin llamadas auxiliares ni ahorro ficticio.

## Impact

conversation.py, repo_context.py, skills.py, models.py, contracts.py, store.py, configuración, documentación y pruebas. Módulos propuestos: context_manager.py y prompt_contracts.py. Campos opcionales para históricos y activación explícita para nuevos intentos; sin cambio de API pública ni recursos Databricks previstos.

Fuera de alcance: compactor LLM, roles/modelos nuevos, resumen semántico automático, vector DB, provider prompt caching y memoria entre HUs. La limpieza se planifica separadamente en remove-unused-harness-scaffold. establish-project-context ya está archivado y su protocolo de desarrollo no implementa memoria de la App.
