## ADDED Requirements

### Requirement: Diagnóstico y reintento de formato de contexto
Para respuestas nuevas con solicitudes de contexto mal formadas, el harness SHALL persistir acceptance=invalid_contract separado del estado de invocación, categoría invalid_contract en el fallo, etapa de origen, revisión, identidad del fallo y vínculo a call_id y evidencia original protegida. El diagnóstico SHALL distinguir objeto esperado/lista recibida, valor nulo, mezcla con salida final, operación o campos inválidos, y tipos o tamaños incompatibles, sin reproducir arbitrariamente valores del modelo. Estos fallos de formato SHALL permitir reintento humano de la etapa mediante los controles existentes de identidad, failure_id, revisión, perfil, contexto, procedencia, checkpoint íntegro y lease/CAS. SHALL detener el trabajador sin nueva llamada automática de reparación. SHALL conservar el tratamiento existente de denegaciones de política/acceso y presupuestos, sin convertirlas indiscriminadamente en fallos recuperables de formato. Los históricos SHALL conservar mensaje, aceptación y retryable originales.

#### Scenario: Invocación correcta con lista inválida
- **WHEN** el endpoint termina con stop y devuelve context_request como lista
- **THEN** la llamada conserva su invocación completa y uso real, acceptance pasa a invalid_contract, el intento falla indicando objeto esperado/lista recibida y no se realiza ninguna lectura

#### Scenario: Reinicio tras fallo nuevo
- **WHEN** la App reinicia después de persistir un fallo recuperable de formato
- **THEN** mantiene failed sin llamadas nuevas y permite mostrar Reintentar etapa solo con las comprobaciones vigentes

#### Scenario: Reintento humano vigente
- **WHEN** una persona autorizada solicita retry con failure_id y revisión vigentes, y perfil, contexto y checkpoint compatibles
- **THEN** se conserva evidencia anterior, se restaura la etapa desde su checkpoint, se registran nuevas llamadas con identificadores propios y el plan resultante exige aprobación vigente

#### Scenario: Reintento obsoleto o incompatible
- **WHEN** retry presenta una revisión/fallo obsoletos, identidad no autorizada, procedencia incompatible o checkpoint alterado
- **THEN** se rechaza sin llamadas nuevas ni sobrescribir el estado de coordinación posterior

#### Scenario: Denegación de una ruta
- **WHEN** una solicitud individual intenta acceder a una ruta denegada por el perfil
- **THEN** conserva la respuesta controlada de rechazo y su tratamiento vigente, sin leer contenido ni habilitar permisos mediante retry

#### Scenario: Ejecución histórica no reintentable
- **WHEN** se consulta la ejecución fa0d8173517049358f53871d45c49117 después de actualizar el producto
- **THEN** conserva el error y retryable=false originales; no se reescribe para ofrecer reintento retroactivo

### Requirement: Evidencia específica de migración de modelo
La instalación de Sonnet 5.5 SHALL conservar evidencia separada de disponibilidad, compatibilidad de solicitudes, permisos de la App y smoke funcional. SHALL identificar endpoint, configuración de capacidades, límites efectivos, finish_reason cuando exista y usage/costo estimado propio por llamada. SHALL configurar tarifas de Sonnet 5.5 con fuente y fecha como supuestos estimados, sin atribuirle automáticamente tarifas de Sonnet 5; tarifas no verificadas SHALL bloquear la activación operativa hasta configurar una estimación documentada. SHALL mantener costo ausente cuando no haya usage. La consulta histórica no SHALL recalcular costos previos con las tarifas nuevas.

#### Scenario: Endpoint disponible
- **WHEN** una consulta de operador confirma READY en Sonnet 5.5
- **THEN** se registra como disponibilidad sin presentarla como prueba de permisos de la App, JSON Schema, límite aceptado o éxito de una HU

#### Scenario: Smoke sintético del endpoint
- **WHEN** una prueba breve comprueba límite efectivo de 64.000 y, si se pretende habilitar, JSON Schema
- **THEN** registra la solicitud efectiva y respuesta con terminación, uso, duración y costo estimado cuando existan, sin exigir generar 64.000 tokens ni usar datos cliente

#### Scenario: Tarifas específicas e histórico
- **WHEN** se activan tarifas estimadas documentadas para Sonnet 5.5 y se consultan llamadas previas de Sonnet 5
- **THEN** las nuevas llamadas usan su fuente configurada y las anteriores conservan sus costos y procedencia originales

#### Scenario: Uso ausente
- **WHEN** el endpoint nuevo no entrega uso de tokens
- **THEN** el costo queda ausente y no se presenta como cero facturado
