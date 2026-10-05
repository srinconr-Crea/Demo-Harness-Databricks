# Proposal

## Why

La HU reportada falló durante planificación por respuesta truncada y, después, por JSON con saltos de línea sin escapar; la interfaz siguió mostrando ejecución activa. El código local confirma topes de 6.000 tokens que prevalecen sobre los 12.000 configurados, ausencia de clasificación por motivo de terminación y persistencia del evento de error sin transición coherente de estado.

## What Changes

- Configurar límites de salida por rol, retirar los topes fijos de planificación y proponer 64.000 tokens para planner, sujetos a compatibilidad comprobada del endpoint y reserva de contexto efectiva.
- Diferenciar truncamiento, JSON mal formado y contrato inválido, conservando causa, uso y evidencia.
- Solicitar JSON mediante esquema cuando la instalación declare soporte comprobado; mantener parseo y controles deterministas en todos los casos.
- Recuperar de forma acotada errores de serialización, sin inventar contenido truncado ni ampliar permisos: normalización sintáctica conservadora y como máximo una llamada adicional de corrección por respuesta final de artefacto.
- Persistir fallo recuperable, etapa de origen y checkpoint coherentes; conservar Reintentar etapa, aclaraciones y artefactos disponibles, sin duplicar trabajadores ni publicaciones.
- Cubrir ambos fallos, agotamiento de recuperación, persistencia, reinicio y reintento con pruebas locales y evidencia remota separada.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `change-planning`: presupuestos efectivos y aceptación estricta de respuestas con recuperación acotada.
- `observability-control`: motivos de terminación, trazabilidad de recuperación y estado persistente de fallo recuperable.
- `conversation-review`: presentación del fallo y reintento autorizado con continuidad de la conversación.

## Impact

Modelos, repo_context, generación OpenSpec, contexto, contratos, coordinación, persistencia, servidor e interfaz del harness; defaults de agentes/runtime/contexto, documentación operativa y pruebas. Se conservan los endpoints de HU; retry ampliará su admisión al fallo recuperable vigente. Campos nuevos serán opcionales para históricos, sin atribuirles evidencia nueva.

No incluye cambios de infraestructura, recursos cliente, merge, despliegue ni reintento de la HU real. Los errores de la HU son antecedentes aportados en el chat: esta propuesta no vuelve a consultar sus registros remotos ni demuestra compatibilidad del endpoint con 64.000 tokens o esquemas.
