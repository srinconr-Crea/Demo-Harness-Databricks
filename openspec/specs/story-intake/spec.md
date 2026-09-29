# Story Intake Specification

## Purpose

Definir la entrada manual de historias de usuario y el seguimiento visible de sus ejecuciones.

## Requirements

### Requirement: Historia completa

El harness SHALL aceptar una historia solo si contiene ID, título, arquitectura, origen y destino, reglas de negocio, requisitos no funcionales y validación, con contenido no vacío.

#### Scenario: Entrada válida
- **WHEN** se envía una historia con todos los campos requeridos
- **THEN** el harness devuelve un identificador de ejecución y su estado

#### Scenario: Entrada incompleta
- **WHEN** falta un campo requerido o su valor está vacío
- **THEN** el harness rechaza la solicitud antes de ejecutar la historia

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
