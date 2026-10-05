# Spec Delta

## ADDED Requirements

### Requirement: Diagnóstico específico del contrato de planificación rechazado
El harness SHALL diferenciar en el diagnóstico un rechazo del manifiesto de un defecto de representación del contenido, manteniendo invalid_contract como categoría de aceptación y fallo. Para un manifiesto rechazado SHALL identificar la entrada y la restricción incumplida; SHALL mostrar su ruta solo cuando pueda exponerse de forma segura. Para contenido rechazado SHALL identificar el artefacto y motivo. SHALL conservar el vínculo a llamada, intento, revisión y respuesta original protegida, sin exponer contenido restringido ni inventar campos en históricos.

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
