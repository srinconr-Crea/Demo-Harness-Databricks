# Spec Delta

## ADDED Requirements

### Requirement: Procedencia del perfil por intento y llamada
Cada nuevo intento y llamada SHALL registrar nombre, versión, repositorio, modo de carga y SHA-256 de los bytes del perfil activado. SHALL conservar una copia protegida del perfil por referencia para reproducibilidad, separada de prompts y respuestas públicas, sin secretos. Los históricos SHALL admitir estos campos ausentes sin asignarles hashes o aprobaciones ficticios.

#### Scenario: Perfil activado para un intento
- **WHEN** se crea un intento y este invoca modelos
- **THEN** el intento y cada llamada contienen el mismo hash del perfil activado y su procedencia

#### Scenario: Consulta de histórico
- **WHEN** se consulta un registro anterior sin procedencia de perfil
- **THEN** el registro sigue legible y muestra esa procedencia como ausente

### Requirement: Continuación vinculada al perfil original
Antes de ejecutar una etapa, aprobar, reintentar o publicar, el harness SHALL comprobar que el perfil activo corresponde al repositorio y hash del intento. SHALL bloquear continuación del intento y acciones dependientes de su aprobación si el perfil difiere o falta procedencia, conservando consulta y cancelación autorizadas. Como excepción explícita, SHALL permitir crear un nuevo intento del mismo repositorio bajo el perfil vigente mediante una solicitud de reintento humano, sin continuar el candidato anterior. Un cambio aprobado de política SHALL requerir planificación y aprobación nuevas y no SHALL heredar la autorización del intento anterior.

#### Scenario: Reinicio con el mismo perfil
- **WHEN** se restaura un intento con el mismo repositorio y hash de perfil
- **THEN** se permite continuar con sus controles y checkpoints existentes

#### Scenario: Reinicio con otro perfil
- **WHEN** la App recupera un intento cuyo perfil difiere del activo
- **THEN** bloquea continuación, aprobaciones y publicación sin borrar el historial

#### Scenario: Intento previo sin hash
- **WHEN** se intenta continuar un intento histórico sin procedencia de perfil
- **THEN** se exige un reintento explícito bajo el perfil actual y nueva aprobación del plan

#### Scenario: Reintento tras actualizar política
- **WHEN** el usuario solicita explícitamente un nuevo intento del mismo repositorio tras un cambio de perfil
- **THEN** el nuevo intento fija el perfil vigente, vuelve a planificar y exige aprobación sin reutilizar el plan anterior

#### Scenario: Reintento en otro repositorio
- **WHEN** el repositorio activo no coincide con el del registro recuperado
- **THEN** se rechaza el reintento de esa HU en esa instalación
