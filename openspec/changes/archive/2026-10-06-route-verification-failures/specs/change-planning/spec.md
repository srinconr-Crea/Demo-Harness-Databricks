## ADDED Requirements

### Requirement: Destinos delta por capacidad declarada
El harness SHALL generar cada delta en la ruta exacta de su capacidad declarada en la propuesta, dentro del cambio cliente. Una capacidad modificada SHALL existir en las specs de la base preparada; una capacidad nueva SHALL declararse explícitamente y cumplir las reglas de ruta y política. SHALL comprobar correspondencia entre propuesta, destinos reales y operaciones delta antes de revisar el plan, y conservarla en update y publicación. No SHALL sustituir la ruta de capacidad por el nombre del cambio ni aceptar instrucciones narrativas como autorización de traversal o escritura adicional. SHALL gestionar por separado los artefactos OpenSpec y el manifiesto de código.

#### Scenario: Capacidad existente
- **WHEN** la propuesta modifica bronze-ingestion sin introducir capacidades nuevas
- **THEN** guarda el delta en specs/bronze-ingestion/spec.md dentro del cambio y valida su aplicación a openspec/specs/bronze-ingestion/spec.md

#### Scenario: Varias capacidades
- **WHEN** la propuesta declara dos capacidades existentes y una nueva
- **THEN** conserva un delta por ruta declarada y valida que las modificaciones correspondan a requisitos existentes

#### Scenario: Capacidad inexistente o ruta inválida
- **WHEN** el planner declara modificar una capacidad ausente o devuelve una ruta fuera de la raíz permitida
- **THEN** rechaza antes de aprobación y apply sin crear una capacidad implícita

### Requirement: Contrato aprobado estable durante corrección
Una corrección de implementación SHALL conservar los bytes/hash de los artefactos aprobados, revisión y manifiesto, usando una versión separada para el candidato. El harness SHALL invocar update solo si debe cambiar el contrato autorizado, con hallazgos específicos, justificación de archivos/operaciones o criterios afectados y evidencia pertinente. Un cambio del plan SHALL invalidar su aprobación y esperar revisión humana; una corrección del candidato dentro del plan SHALL invalidar su verificación anterior, sin inventar una nueva aprobación. La evidencia de implementación y pruebas SHALL registrarse separadamente de los bytes aprobados hasta la finalización determinista ya prevista.

#### Scenario: Corrección sin cambios del plan
- **WHEN** el candidato se corrige para cumplir el mismo criterio y manifiesto
- **THEN** mantiene revisión/hash y aprobación del plan, incrementa versión del candidato y no genera nuevos artefactos por planner

#### Scenario: Update justificado
- **WHEN** una reparación requiere una ruta adicional autorizable por el perfil
- **THEN** planner recibe la ruta, operación, motivo y hallazgo real, y el nuevo plan espera aprobación antes de desarrollar

#### Scenario: Mensaje genérico frente a operaciones vacías
- **WHEN** developer no solicita rutas adicionales y devuelve cobertura de archivos ya conformes
- **THEN** el harness no atribuye al developer una ampliación inexistente mediante feedback genérico
