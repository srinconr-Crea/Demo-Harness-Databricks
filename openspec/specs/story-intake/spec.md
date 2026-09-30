# Story Intake Specification

## Purpose

Definir la entrada manual de historias de usuario y el seguimiento visible de sus ejecuciones.

## Requirements

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

### Requirement: Reintento trazable

El harness SHALL conservar los intentos anteriores de una historia y asignar un identificador nuevo a cada reintento permitido.

#### Scenario: Reenvío tras fallo
- **WHEN** se reenvía una historia cuyo intento anterior terminó en fallo
- **THEN** el nuevo intento queda asociado a la misma ejecución sin borrar el historial

### Requirement: Cancelación cooperativa

El harness SHALL aceptar una solicitud de cancelación mientras una historia esté en cola o en ejecución y SHALL aplicarla en un punto seguro, conservando cualquier progreso de publicación ya registrado.

#### Scenario: Cancelación en cola
- **WHEN** se cancela una historia que aún no empieza
- **THEN** su estado pasa a cancelado sin ejecutar el flujo

#### Scenario: Cancelación después de iniciar publicación
- **WHEN** la publicación ya creó una rama o un Pull Request
- **THEN** el registro conserva esos datos y no oculta la publicación
