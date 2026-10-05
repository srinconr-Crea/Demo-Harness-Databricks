# Spec Delta

## ADDED Requirements

### Requirement: Presentación y reintento de fallo recuperable
La App SHALL mostrar un fallo recuperable como fallido con causa comprensible y fase de origen, y SHALL ofrecer Reintentar etapa a identidades autorizadas cuando el fallo sea vigente. Retry SHALL comprobar revisión, identidad del fallo, perfil, contexto y procedencia, y coordinar una sola reanudación desde evidencia íntegra. SHALL conservar aclaraciones e historial, sin reutilizar aprobación obsoleta ni repetir publicaciones confirmadas. Los históricos con evento de error y estado activo SHALL seguir consultables y admitirse para recuperación solo bajo los controles vigentes.

#### Scenario: Reintento sin reenviar la HU
- **WHEN** el creador solicita retry de un fallo vigente de planificación con revisión coincidente y procedencia válida
- **THEN** se retoma la etapa de origen con aclaraciones guardadas, se registra el reintento y se solicita aprobación cuando exista un nuevo plan válido

#### Scenario: Doble clic o concurrencia
- **WHEN** dos solicitudes intentan reanudar la misma identidad de fallo
- **THEN** se acepta una sola transición y no se ejecutan dos trabajadores del mismo intento

#### Scenario: Revisión o autorización inválida
- **WHEN** llega retry de revisión obsoleta o de una identidad sin acceso
- **THEN** se rechaza sin invocar modelos ni cambiar evidencia

#### Scenario: Fallo no recuperable o perfil cambiado
- **WHEN** el fallo no admite retry o el perfil/contexto/procedencia no permiten continuidad
- **THEN** no se reanuda la etapa bajo aprobaciones anteriores y se aplican los controles existentes de bloqueo o nuevo intento explícito

#### Scenario: Checklist coherente
- **WHEN** planificación falla y no hay trabajador activo
- **THEN** el resumen global muestra fallo, la fase de origen aparece fallida y las posteriores no aparecen completadas
