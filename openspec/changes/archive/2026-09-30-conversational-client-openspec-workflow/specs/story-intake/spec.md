# Spec Delta

## MODIFIED Requirements

### Requirement: Historia completa
El harness SHALL aceptar una historia nueva cuando contenga una HU y una descripción no vacías; no SHALL exigir campos separados de arquitectura, origen/destino, reglas de negocio, requisitos no funcionales o validación. La información faltante necesaria para planificar SHALL obtenerse mediante aclaraciones en la conversación.

#### Scenario: Entrada válida
- **WHEN** se envía una HU y una descripción no vacías
- **THEN** el harness devuelve un identificador de ejecución y el estado de su conversación

#### Scenario: Entrada incompleta
- **WHEN** falta la HU o la descripción, o alguna está vacía
- **THEN** el harness rechaza la solicitud antes de clonar o ejecutar la historia

#### Scenario: Detalle insuficiente
- **WHEN** la HU y descripción son válidas pero no permiten elaborar un plan comprobable
- **THEN** el flujo solicita una aclaración en `explore` sin inventar los datos faltantes
