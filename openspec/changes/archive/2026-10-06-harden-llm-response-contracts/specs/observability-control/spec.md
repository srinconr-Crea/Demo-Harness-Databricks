# Spec Delta

## MODIFIED Requirements

### Requirement: Diagnóstico específico del contrato de planificación rechazado
El harness SHALL diferenciar en el diagnóstico un rechazo del manifiesto de un defecto de representación del contenido, manteniendo invalid_contract como categoría de aceptación y fallo. Para un manifiesto rechazado SHALL identificar la entrada y la restricción incumplida; SHALL mostrar su ruta solo cuando pueda exponerse de forma segura. Para contenido rechazado SHALL identificar el artefacto y motivo; cuando falten encabezados estructurales SHALL identificar los títulos requeridos ausentes de forma ordenada y acotada, según la redacción vigente, sin reproducir arbitrariamente títulos o texto recibidos del modelo. SHALL conservar el vínculo a llamada, intento, revisión y respuesta original protegida, sin exponer contenido restringido ni inventar campos en históricos.

#### Scenario: Entrada OpenSpec rechazada
- **WHEN** la tercera entrada del manifiesto intenta modificar una delta OpenSpec
- **THEN** el error identifica esa entrada y que OpenSpec se gestiona fuera del manifiesto de código, con ruta segura o referencia protegida al detalle

#### Scenario: Representación inválida del documento
- **WHEN** el JSON es válido pero content no cumple la estructura Markdown por serialización adicional
- **THEN** el error identifica el artefacto y ese motivo sin presentarlo como JSON mal formado ni respuesta truncada

#### Scenario: Error con datos restringidos
- **WHEN** una entrada o respuesta rechazada contiene datos que la redacción vigente no permite exponer
- **THEN** el diagnóstico público conserva índice y motivo seguro y el detalle permanece en evidencia protegida

#### Scenario: Histórico anterior
- **WHEN** se consulta un rechazo anterior sin diagnóstico específico
- **THEN** conserva su mensaje y evidencia originales sin atribuirle una validación nueva

#### Scenario: Encabezado traducido
- **WHEN** proposal contiene Qué cambia y la plantilla exige What Changes
- **THEN** el error identifica proposal y What Changes como encabezado requerido ausente, sin traducir o reescribir el documento ni habilitar apply

## ADDED Requirements

### Requirement: Reintento humano de presentación de artefactos
Para fallos nuevos, el harness SHALL distinguir defectos de presentación Markdown de denegaciones de política, manifiesto inválido o incompatibilidad de configuración. Los defectos de encabezados o representación del contenido SHALL conservar acceptance y categoría invalid_contract y permitir reintento humano de la etapa fallida mediante los controles vigentes de identidad autorizada, failure_id, revisión, perfil, contexto, procedencia, checkpoint íntegro y lease/CAS. SHALL conservar artefactos parciales y evidencias de llamadas, restaurar el checkpoint y requerir aprobación vigente del plan resultante antes de apply. SHALL detener el trabajador sin corrección automática del contrato y mantener failed tras reinicios. La consulta histórica SHALL conservar su mensaje y retryable originales. Esta capacidad SHALL no convertir indiscriminadamente errores de política, presupuesto o configuración en fallos recuperables de presentación.

#### Scenario: Propuesta rechazada por un título ausente
- **WHEN** una ejecución nueva falla porque un artefacto carece de un encabezado requerido
- **THEN** persiste failed con etapa de origen, identidad del fallo y recuperabilidad humana, sin llamadas automáticas adicionales ni éxito de fases posteriores

#### Scenario: Artefacto anterior válido
- **WHEN** proposal es válido y un artefacto posterior falla su presentación
- **THEN** se conserva proposal en el checkpoint como evidencia parcial y retry restaura el estado íntegro sin tratar ese documento como plan aprobado

#### Scenario: Reintento humano autorizado
- **WHEN** una persona autorizada solicita retry con fallo y revisión vigentes y procedencia, perfil, contexto y checkpoint compatibles
- **THEN** se restaura la etapa, se conserva la evidencia anterior y las llamadas nuevas tienen identificadores propios; el plan corregido requiere aprobación vigente

#### Scenario: Reintento obsoleto o competidor
- **WHEN** retry presenta failure_id o revisión obsoletos, identidad no autorizada, checkpoint alterado o un lease ya reclamado
- **THEN** se rechaza sin nuevas llamadas ni sobrescribir una transición posterior

#### Scenario: Reinicio sin reintento humano
- **WHEN** la App reinicia tras un fallo de presentación persistido
- **THEN** conserva failed y su diagnóstico sin invocar el modelo ni reanudar la etapa automáticamente

#### Scenario: Denegación de política
- **WHEN** el manifiesto excede rutas u operaciones autorizadas
- **THEN** conserva su tratamiento de política y no recibe recuperabilidad por la clasificación de presentación

#### Scenario: Intento histórico analizado
- **WHEN** se consulta 9f4d553d17ea406ca596600875735656 después de activar el cambio
- **THEN** conserva el mensaje original y retryable=false; repetir la HU requiere una ejecución nueva con planificación y aprobación propias
