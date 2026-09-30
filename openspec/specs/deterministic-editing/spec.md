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
El harness SHALL validar el resultado con controles de su estrategia y comparar el diff real con archivos y operaciones del manifiesto aprobado, además de la política. Las operaciones generales SHALL ser tipadas, de texto, limitadas y con hash previo para modificación o borrado; SHALL rechazarse conjuntos inválidos antes de aplicar archivos. El candidato SHALL quedar vinculado a la versión del plan y evidencia de verificación.

#### Scenario: Edición divergente
- **WHEN** la expresión o resultado silver_safe_ratio difiere de la razón validada
- **THEN** se detiene el flujo sin publicar

#### Scenario: Código general inválido
- **WHEN** el parche viola formato, sintaxis, estructura o límites
- **THEN** se bloquean verify y publicación hasta corregir

#### Scenario: Archivo adicional
- **WHEN** el parche admite una ruta por política pero no por el manifiesto aprobado
- **THEN** se solicita revisión del plan antes de editar esa ruta

#### Scenario: Hash previo divergente
- **WHEN** una modificación o eliminación no coincide con los bytes esperados
- **THEN** se rechaza el conjunto sin aplicar parcialmente operaciones
