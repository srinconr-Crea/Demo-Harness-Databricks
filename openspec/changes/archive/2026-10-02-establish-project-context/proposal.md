# Proposal

## Why

Al retomar el desarrollo del harness en otra conversación, las decisiones y el estado pueden depender de recuerdos del chat o documentos duplicados. Necesitamos un protocolo versionado para reconstruir contexto desde fuentes verificables, distinguiendo principios, comportamiento vigente, implementación y trabajo pendiente.

## What Changes

- Definir un contexto general breve en `openspec/config.yaml`, conservando propósito, mapa del código activo, aislamiento y referencias; trasladar detalles variables a sus fuentes existentes.
- Establecer un protocolo de inicio y reanudación en `AGENTS.md` y una guía breve `docs/contexto-proyecto.md`, referenciada desde README y operación.
- Recuperar solo specs, cambios y fragmentos pertinentes; identificar rama/SHA y contradicciones antes de asumir que una propuesta está implementada.
- Mantener decisiones duraderas en specs/diseños versionados. Registrar decisiones arquitectónicas transversales excepcionales en documentos breves bajo `docs/decisions/`, enlazados al cambio que las introdujo, sin copiar requisitos.
- Definir comprobaciones de coherencia y ejercicios de reanudación sin historial del chat.
- No implementar cache, memoria ni compactación del runtime en este cambio.

## Capabilities

### New Capabilities

- `project-context`: protocolo de reconstrucción del contexto del desarrollo desde fuentes versionadas, tratamiento de discrepancias y mantenimiento de referencias.

### Modified Capabilities

Ninguna. El protocolo para desarrollar el producto no modifica la recuperación del checkout cliente ni la conversación de HU en la App.

## Impact

Documentación, `AGENTS.md`, `openspec/config.yaml`, nueva spec y comprobaciones documentales nuevas en `tests/test_project_context.py`. Sin cambios de API, modelos, infraestructura o permisos. La propuesta hermana `manage-hu-agent-context` es independiente: ninguna implementación es prerrequisito de la otra. Estas propuestas no constituyen aprobación de implementación.
