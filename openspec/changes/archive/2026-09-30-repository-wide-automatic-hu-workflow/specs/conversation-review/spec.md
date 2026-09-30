# Spec Delta

## MODIFIED Requirements

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

### Requirement: Aprobación del diff final
El harness SHALL sustituir la espera de aprobación final del diff por continuación automática autorizada mediante el plan vigente. SHALL conservar el diff completo y evidencia para consulta y revisión en el PR sin registrar aprobaciones humanas ficticias. Una ampliación del alcance o ambigüedad funcional SHALL devolver el flujo a revisión de propuesta.

#### Scenario: Diff aprobado
- **WHEN** el candidato corresponde al plan vigente y pasó controles, sync y archive
- **THEN** continúa a creación del PR sin acción humana adicional

#### Scenario: Diff cambiado tras aprobación
- **WHEN** se alteran bytes del candidato verificado
- **THEN** se bloquea publicación hasta nueva verificación y nueva aprobación del plan si cambia su alcance
