# conversation-review Specification

## Purpose

Permitir que la persona converse sobre una HU y revise el progreso, los artefactos y el código producidos en etapas, con decisiones vinculadas a versiones concretas.

## Requirements

### Requirement: Progreso conversacional por HU
La App SHALL mostrar preguntas necesarias, respuestas humanas y propuesta vigente en lenguaje natural con acceso al detalle técnico bajo demanda. SHALL ocultar por defecto comandos, JSON y artefactos intermedios, conservando trazabilidad por intento y revisión. SHALL mantener comentarios y borradores durante revisión y actualización sin borrarlos por polling. Costos y artefactos SHALL seguir consultables.

#### Scenario: Artefacto producido
- **WHEN** propose o update guarda un artefacto
- **THEN** se conserva consultable sin insertar su salida técnica completa en el hilo principal

#### Scenario: Aclaración necesaria
- **WHEN** explore necesita información
- **THEN** se solicitan respuestas y se permanece en exploración hasta resolver ambigüedad

#### Scenario: HU clara
- **WHEN** explore dispone de información suficiente
- **THEN** continúa a propose sin pedir respuestas innecesarias

#### Scenario: Comentario en edición
- **WHEN** llega una actualización de estado mientras la persona escribe
- **THEN** el comentario conserva su contenido

### Requirement: Aprobación del plan antes de desarrollar
El harness SHALL detenerse tras validar la versión propuesta de los artefactos OpenSpec y requerir aprobación humana de esa versión antes de invocar `apply`. La persona SHALL poder pedir cambios, que generan una nueva versión y otra revisión.

#### Scenario: Plan aprobado
- **WHEN** la persona aprueba la versión vigente y validada del plan
- **THEN** el harness habilita `apply` para esa versión

#### Scenario: Plan devuelto con cambios
- **WHEN** la persona solicita una revisión del plan
- **THEN** el planner ejecuta `update`, la aprobación anterior pierde vigencia y el desarrollo permanece bloqueado

### Requirement: Aprobación del diff final
El harness SHALL sustituir la espera de aprobación final del diff por continuación automática autorizada mediante el plan vigente. SHALL conservar el diff completo y evidencia para consulta y revisión en el PR sin registrar aprobaciones humanas ficticias. Una ampliación del alcance o ambigüedad funcional SHALL devolver el flujo a revisión de propuesta.

#### Scenario: Diff aprobado
- **WHEN** el candidato corresponde al plan vigente y pasó controles, sync y archive
- **THEN** continúa a creación del PR sin acción humana adicional

#### Scenario: Diff cambiado tras aprobación
- **WHEN** se alteran bytes del candidato verificado
- **THEN** se bloquea publicación hasta nueva verificación y nueva aprobación del plan si cambia su alcance

### Requirement: Decisiones humanas autorizadas y persistentes
Las respuestas, solicitudes de cambios y aprobaciones SHALL estar vinculadas a una identidad autorizada, etapa, intento y huella de contenido; los estados de espera SHALL sobrevivir a reinicios sin ocupar un trabajador de ejecución.

#### Scenario: Decisión desactualizada
- **WHEN** llega una aprobación para una versión distinta de la que espera revisión
- **THEN** el harness la rechaza y conserva la versión vigente sin publicarla

### Requirement: Continuidad de la conversación al importar skills
El harness SHALL conservar estados, acciones y contratos públicos de la conversación de HU al consumir skills. SHALL mostrar resumen y preguntas necesarias, propuesta revisable y aprobación vigente del plan; SHALL continuar automáticamente hasta el PR tras verificar, sincronizar y archivar para intentos de publicación por plan aprobado. Las instrucciones internas no SHALL introducir aprobaciones adicionales, comandos o JSON en el hilo principal. Los históricos SHALL conservar su modalidad y seguir consultables sin inventar evidencia. El texto generado puede variar sin alterar el recorrido.

#### Scenario: HU clara
- **WHEN** explore no identifica preguntas necesarias
- **THEN** continúa a propuesta sin agregar una confirmación para cargar skills

#### Scenario: Aclaración y revisión
- **WHEN** la persona responde preguntas o solicita cambios al plan
- **THEN** se conservan mensajes y borradores, se usan las mismas acciones y una revisión nueva invalida la aprobación anterior

#### Scenario: Plan aprobado
- **WHEN** el candidato corresponde al plan aprobado y supera controles vigentes
- **THEN** se crea el PR automáticamente sin pedir aprobación humana adicional del diff

#### Scenario: Preparación incompleta
- **WHEN** faltan configuración o skills compatibles en la base
- **THEN** se muestra un error comprensible que identifica la preparación manual pendiente, sin abrir un onboarding dentro del chat

#### Scenario: Histórico
- **WHEN** se consulta una ejecución anterior al consumo de skills
- **THEN** permanece legible con su modalidad y evidencia original sin atribuirle instrucciones nuevas
