# Spec Delta

## ADDED Requirements

### Requirement: Aceptación de Markdown antes de guardar el artefacto
El harness SHALL comprobar la representación y estructura requerida del contenido de cada artefacto conforme a su contrato e instrucciones confiables antes de guardarlo como artefacto aceptado. SHALL rechazar como invalid_contract el contenido doblemente serializado que no cumple esa estructura. SHALL preservar bytes semánticos de contenido válido, sin reemplazos globales de escapes, decodificación adicional arbitraria ni llamadas automáticas de reparación de contratos inválidos. El plan completo SHALL seguir pasando validación OpenSpec estricta y política antes de revisión y apply.

#### Scenario: Documento completo con separadores literales
- **WHEN** una respuesta JSON válida contiene una propuesta con separadores literales de barra invertida seguida de n y no presenta sus secciones requeridas como líneas Markdown reales
- **THEN** se rechaza con diagnóstico de representación del contenido antes de registrar ese artefacto como aceptado

#### Scenario: Documento válido con escapes y Unicode
- **WHEN** un artefacto válido contiene saltos reales, acentos, comillas, rutas y escapes literales legítimos en sus ejemplos
- **THEN** se conserva su contenido sin una segunda decodificación ni modificaciones a los ejemplos

#### Scenario: Error después de un artefacto correcto
- **WHEN** un artefacto previo fue aceptado y el siguiente falla su representación o manifiesto
- **THEN** se conserva el artefacto previo y la evidencia del rechazo, se persiste failed y no se habilita apply ni publicación

#### Scenario: Manifiesto con operación prohibida
- **WHEN** proposal declara código válido junto con una operación OpenSpec o una ruta prohibida por el perfil
- **THEN** se rechaza el manifiesto completo sin filtrar entradas para aparentar éxito ni invocar al desarrollador

#### Scenario: Recorridos de planificación equivalentes
- **WHEN** se ejecuta propose o update con el gestor de contexto habilitado o deshabilitado
- **THEN** se aplican las mismas comprobaciones de representación y política, conservando los contratos propios de cada estrategia
