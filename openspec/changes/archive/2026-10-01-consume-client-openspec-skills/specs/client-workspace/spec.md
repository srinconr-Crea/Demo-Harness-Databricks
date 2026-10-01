## MODIFIED Requirements

### Requirement: Preparación única de OpenSpec por cliente
La preparación inicial SHALL ser realizada manualmente por una persona en el repositorio cliente mediante `openspec init --tools agents --no-animation`, configuración de contexto y workflows requeridos, PR en rama permitida y merge humano. El harness SHALL admitir HUs solamente cuando la rama base contenga configuración OpenSpec y todas las skills requeridas válidas y compatibles. La App no SHALL ejecutar init, update, crear PR de preparación ni reparar automáticamente la preparación. Las actualizaciones SHALL coordinarse fuera de las HUs mediante mantenimiento y PR humano.

#### Scenario: Cliente pendiente de preparación
- **WHEN** la rama base carece de configuración OpenSpec válida o skills requeridas
- **THEN** el harness indica la preparación manual pendiente y no inicia explore, propose ni desarrollo

#### Scenario: Cliente preparado
- **WHEN** una persona integró el PR de preparación y la base contiene configuración y skills compatibles
- **THEN** la HU consume esos archivos sin reinicializarlos ni actualizarlos

#### Scenario: PR aún sin integrar
- **WHEN** los archivos preparados solo existen en una rama de preparación
- **THEN** el harness mantiene bloqueada la HU hasta que estén disponibles en la base autorizada

#### Scenario: Solicitud de inicialización a la App
- **WHEN** una HU solicita inicializar OpenSpec o generar su PR de preparación
- **THEN** la App informa el procedimiento manual y no realiza esas operaciones

#### Scenario: Actualización de skills
- **WHEN** una persona actualiza CLI y skills mediante mantenimiento y un PR integrado
- **THEN** los intentos posteriores sobre esa base consumen las nuevas skills y los intentos existentes conservan su procedencia original
