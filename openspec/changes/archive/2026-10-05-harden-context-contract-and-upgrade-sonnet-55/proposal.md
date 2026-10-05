# Proposal

## Why

La ejecución `fa0d8173517049358f53871d45c49117` falló en explore porque Sonnet entregó una lista de solicitudes de contexto donde el harness exige un objeto, con campos adicionales incompatibles; el diagnóstico genérico y su clasificación no reintentable dificultan recuperarla. Sonnet 5.5 ya aparece disponible en el workspace CREA_DEV y se propone migrar el producto junto con un contrato explícito y comprobable, sin atribuir al modelo nuevo una corrección automática del problema.

## What Changes

- Declarar una sola operación de contexto por turno, con formas exactas, tipos, límites y ejemplos compartidos por las rutas con gestor de contexto habilitado y deshabilitado.
- Rechazar listas, valores nulos, solicitudes mezcladas con salida final y campos inválidos antes de cualquier lectura; preservar el tratamiento actual de denegaciones de acceso y presupuestos.
- Registrar `acceptance=invalid_contract` y diagnóstico seguro para solicitudes mal formadas, separado de la invocación HTTP correcta. Permitir reintento humano de nuevos fallos de formato mediante checkpoint, identidad, revisión, procedencia y coordinación existentes; no reparar ni reintentar automáticamente.
- **BREAKING**: sustituir el endpoint exigido a los roles explorer, planner, developer y openspec_verifier por `databricks-claude-sonnet-5-5`, actualizando validación confiable, routing, permisos de instalación y pruebas. Haiku 4.5 conserva su función asesora.
- Mantener presupuestos de salida y contexto actuales. Comprobar JSON Schema y límite efectivo en Sonnet 5.5 con pruebas sintéticas antes de declarar capacidades verificadas; documentar tarifas específicas como estimaciones con fuente y fecha.
- Conservar históricos y la ejecución fallida originales, sin cambiar sus flags, mensajes o aprobaciones. Preparar migración y rollback mediante paquetes completos, con HUs drenadas.

## Capabilities

### New Capabilities

Ninguna; se amplían contratos existentes.

### Modified Capabilities

- `agent-prompt-contracts`: formas exactas de contexto, una operación por turno y equivalencia entre modalidades de gestión de contexto.
- `change-planning`: selección confiable de Sonnet 5.5 para los cuatro roles obligatorios y conservación de presupuestos.
- `observability-control`: aceptación y diagnóstico de solicitudes inválidas, reintento humano de nuevos fallos de formato y trazabilidad de la migración del modelo.

## Impact

El cambio afecta `harness/prompt_contracts.py`, `harness/repo_context.py`, `harness/context_manager.py`, `harness/models.py`, y las integraciones de persistencia/reintento en `harness/conversation.py` y `app/start_server.py` cuando sean necesarias. Afecta defaults de prompts/modelos, entorno de instalación, referencias operativas y pruebas de contratos, contexto, integraciones, recuperación e instalación.

La App debe recibir `CAN_QUERY` sobre el endpoint nuevo mediante su recurso de instalación. Si se modifica `databricks.yml` o `resources/`, se exige validación estricta del bundle dev. Las pruebas remotas se acotan a recursos del harness y datos sintéticos; no incluyen recursos, datos o despliegue de NaturaPet ni ejecución de esta HU real. No se agregan dependencias, herramientas de contexto, campos de acción HTTP ni aprobaciones. Este cambio genera planificación; implementación, smoke remoto y despliegue aún no están verificados.
