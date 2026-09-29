# Spec Delta

## MODIFIED Requirements

### Requirement: Secuencia de controles

El harness SHALL exigir que la inicialización OpenSpec en el workspace cliente, la planificación validada, la propuesta del desarrollador, la validación del editor, la prueba remota y la revisión del verificador terminen satisfactoriamente antes de publicar. El desarrollador y el verificador SHALL recibir los artefactos de planificación validados del mismo intento.

#### Scenario: Todos los controles aprobados
- **WHEN** cada control produce un resultado válido y aprobatorio
- **THEN** el flujo puede iniciar la publicación

#### Scenario: Control rechazado
- **WHEN** cualquier control falla o entrega una salida inválida
- **THEN** el flujo se detiene sin iniciar la publicación

#### Scenario: Planificación rechazada
- **WHEN** el cambio OpenSpec no valida o contradice la política del perfil
- **THEN** el desarrollador no se invoca y no se publica código cliente

#### Scenario: Inicialización rechazada
- **WHEN** OpenSpec no puede inicializarse en el workspace cliente
- **THEN** el desarrollador no se invoca y no se publica código cliente

#### Scenario: Verificación contra la especificación
- **WHEN** el cambio editado pasa la prueba sintética
- **THEN** el verificador compara el diff y la evidencia con las especificaciones delta validadas antes de aprobar
