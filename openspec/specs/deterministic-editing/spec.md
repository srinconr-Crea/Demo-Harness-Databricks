# Deterministic Editing Specification

## Purpose

Definir cómo una estrategia registrada transforma una historia en un cambio acotado y verificable.

## Requirements

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

### Requirement: Razón segura vigente

La estrategia `silver_safe_ratio` SHALL aceptar exactamente una razón `columna = numerador / denominador` para la tabla y el notebook configurados, con columnas de origen autorizadas por el perfil.

#### Scenario: Razón autorizada
- **WHEN** la historia contiene una razón válida con columnas permitidas
- **THEN** el editor produce una única columna derivada mediante división segura

#### Scenario: Origen no autorizado
- **WHEN** un operando no pertenece a las columnas de origen permitidas
- **THEN** el harness rechaza la historia antes de editar

### Requirement: Validación del resultado
El harness SHALL validar el resultado con los controles de la estrategia registrada y SHALL comparar el diff real con los archivos y operaciones autorizados antes de la revisión humana.

#### Scenario: Edición divergente
- **WHEN** la expresión propuesta o el resultado `silver_safe_ratio` difiere de la razón validada
- **THEN** el harness detiene el flujo sin publicar

#### Scenario: Código general inválido
- **WHEN** el parche general viola formato, sintaxis, estructura o límites exigidos para los archivos afectados
- **THEN** el harness bloquea `verify` y la publicación hasta corregirlo
