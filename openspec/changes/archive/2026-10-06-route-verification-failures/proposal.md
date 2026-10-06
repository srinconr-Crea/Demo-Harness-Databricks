# Proposal

## Why

El harness devuelve tanto errores de implementación como cambios de alcance a `update`, regenerando planes y solicitando aprobaciones aunque el contrato autorizado siga siendo válido. La ejecución `f9c8efe4b82449b98e0de1ea749c6a0e` mostró además una ruta OpenSpec impuesta incorrectamente y cuatro falsos cambios de alcance por respuestas sin operaciones, que prolongaron el intento sin resolver el bloqueo.

## What Changes

- Separar fallos de implementación, especificación/alcance, infraestructura/evidencia y defectos del harness antes de decidir una transición.
- Introducir `correcting` para corregir el candidato dentro del plan y manifiesto aprobados y volver a validación técnica y verificación Sonnet, sin planner ni aprobación adicional.
- Reservar `update` y nueva aprobación para cambios reales de especificación, comportamiento autorizado, archivos u operaciones.
- Conservar un máximo compartido de dos correcciones automáticas por intento y detener ciclos sin progreso; las revisiones del plan no reinician ese presupuesto.
- Admitir archivos ya conformes y operaciones parciales mediante cobertura explícita y comprobación del diff acumulado respecto de la base, sin exigir reescrituras ni aceptar omisiones como éxito.
- Resolver los destinos delta por capacidad OpenSpec declarada y existente, en lugar de imponer el nombre del cambio como capacidad.
- Trasladar notas, lecturas y pruebas con procedencia entre etapas; permitir retrieval acotado al verificador y distinguir tareas implementadas, verificadas y pendientes de publicación.
- Persistir categoría, motivo, versión del candidato, contador y evidencia de cada transición, con recuperación consistente y progreso visible.
- Mantener Sonnet obligatorio y Haiku independiente asesor con el comportamiento, routing y registro actuales. Su eliminación, desactivación o evaluación adicional quedan fuera del alcance.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `execution-validation`: clasificación de fallos, corrección dentro del plan, evidencia entre etapas, límites y verificación del candidato corregido.
- `deterministic-editing`: cobertura de manifiesto, archivos ya conformes y operaciones de corrección vinculadas al diff acumulado.
- `change-planning`: destinos delta por capacidad y conservación del contrato aprobado durante correcciones de implementación.
- `observability-control`: trazabilidad y presentación de correcciones, clasificación, progreso y recuperación sin ciclos indefinidos.

## Impact

Runtime en `conversation.py`, `openspec.py`, `patch.py`, `prompt_contracts.py`, `repo_context.py`, `context_manager.py`, `progress.py` y persistencia/coordinación cuando corresponda; contratos confiables en `config/defaults/prompts.yaml`, interfaz y documentación operativa. Pruebas de flujo, edición, skills, contexto, recuperación y publicación en `tests/`.

La spec actual de `execution-validation` manda volver al plan ante todo descuadre; este cambio reemplaza explícitamente ese comportamiento para intentos nuevos. Los históricos mantienen evidencia y modalidad originales; no se atribuyen clasificaciones ni correcciones retroactivas. No se modifica código cliente, infraestructura Databricks, secretos, modelos, permisos ni merge/despliegue mediante esta propuesta. El PR del candidato verificado continúa autorizado por el plan vigente.
