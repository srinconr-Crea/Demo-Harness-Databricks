# Spec Delta

## MODIFIED Requirements

### Requirement: Estrategia registrada
El harness SHALL editar código cliente solo mediante una estrategia registrada en el perfil. La estrategia `general_patch` SHALL permitir que el agente desarrollador proponga y aplique cambios generales en archivos autorizados, con controles deterministas de rutas, tipo de archivo, operaciones, tamaño, estructura y validación; la estrategia `silver_safe_ratio` conserva su comportamiento específico.

#### Scenario: Estrategia ausente
- **WHEN** el perfil no configura una estrategia o su tipo no está registrado
- **THEN** el harness detiene el flujo antes de publicar

#### Scenario: Parche general admitido
- **WHEN** la HU requiere un cambio distinto de una razón segura y el perfil autoriza `general_patch`
- **THEN** el desarrollador puede modificar únicamente archivos y operaciones admitidos dentro del checkout

#### Scenario: Parche general fuera de política
- **WHEN** el parche intenta escribir fuera de las rutas, tipos u operaciones permitidos
- **THEN** el harness rechaza el parche sin incorporarlo al candidato publicable

### Requirement: Validación del resultado
El harness SHALL validar el resultado con los controles de la estrategia registrada y SHALL comparar el diff real con los archivos y operaciones autorizados antes de la revisión humana.

#### Scenario: Edición divergente
- **WHEN** la expresión propuesta o el resultado `silver_safe_ratio` difiere de la razón validada
- **THEN** el harness detiene el flujo sin publicar

#### Scenario: Código general inválido
- **WHEN** el parche general viola formato, sintaxis, estructura o límites exigidos para los archivos afectados
- **THEN** el harness bloquea `verify` y la publicación hasta corregirlo
