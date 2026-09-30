# conversation-review Specification

## Purpose

Permitir que la persona converse sobre una HU y revise el progreso, los artefactos y el código producidos en etapas, con decisiones vinculadas a versiones concretas.

## Requirements

### Requirement: Progreso conversacional por HU
La App SHALL mostrar en orden los mensajes humanos, preguntas y respuestas del agente, etapas OpenSpec, resultados de pruebas, artefactos generados o actualizados y costos estimados disponibles. Cada elemento SHALL conservar su relación con el intento y la versión del cambio.

#### Scenario: Artefacto producido
- **WHEN** `propose` o `update` guarda un spec o tarea nueva
- **THEN** la persona puede consultar su contenido y estado en la conversación sin esperar al PR

#### Scenario: Aclaración necesaria
- **WHEN** `explore` necesita información para concretar la HU
- **THEN** la App solicita una respuesta y conserva el contexto para continuar el mismo intento

### Requirement: Aprobación del plan antes de desarrollar
El harness SHALL detenerse tras validar la versión propuesta de los artefactos OpenSpec y requerir aprobación humana de esa versión antes de invocar `apply`. La persona SHALL poder pedir cambios, que generan una nueva versión y otra revisión.

#### Scenario: Plan aprobado
- **WHEN** la persona aprueba la versión vigente y validada del plan
- **THEN** el harness habilita `apply` para esa versión

#### Scenario: Plan devuelto con cambios
- **WHEN** la persona solicita una revisión del plan
- **THEN** el planner ejecuta `update`, la aprobación anterior pierde vigencia y el desarrollo permanece bloqueado

### Requirement: Aprobación del diff final
El harness SHALL mostrar el diff completo de código y OpenSpec, junto con la evidencia de `verify`, y requerir aprobación humana de su versión exacta antes de crear o actualizar una rama o PR. Cualquier modificación posterior SHALL invalidar la aprobación y exigir una nueva revisión.

#### Scenario: Diff aprobado
- **WHEN** la persona aprueba el diff vigente, validado y con pruebas aprobadas
- **THEN** el harness puede comenzar la publicación de esa versión exacta

#### Scenario: Diff cambiado tras aprobación
- **WHEN** cambia cualquier archivo del candidato aprobado
- **THEN** el harness bloquea la publicación hasta que se verifique y apruebe el nuevo diff

### Requirement: Decisiones humanas autorizadas y persistentes
Las respuestas, solicitudes de cambios y aprobaciones SHALL estar vinculadas a una identidad autorizada, etapa, intento y huella de contenido; los estados de espera SHALL sobrevivir a reinicios sin ocupar un trabajador de ejecución.

#### Scenario: Decisión desactualizada
- **WHEN** llega una aprobación para una versión distinta de la que espera revisión
- **THEN** el harness la rechaza y conserva la versión vigente sin publicarla
