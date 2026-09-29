# Deterministic Editing Specification

## Purpose

Definir cómo una estrategia registrada transforma una historia en un cambio acotado y verificable.

## Requirements

### Requirement: Estrategia registrada

El harness SHALL editar código cliente solo mediante una estrategia registrada con análisis, edición y validación específicos.

#### Scenario: Estrategia ausente
- **WHEN** el perfil no configura una estrategia o su tipo no está registrado
- **THEN** el harness detiene el flujo antes de publicar

### Requirement: Razón segura vigente

La estrategia `silver_safe_ratio` SHALL aceptar exactamente una razón `columna = numerador / denominador` para la tabla y el notebook configurados, con columnas de origen autorizadas por el perfil.

#### Scenario: Razón autorizada
- **WHEN** la historia contiene una razón válida con columnas permitidas
- **THEN** el editor produce una única columna derivada mediante división segura

#### Scenario: Origen no autorizado
- **WHEN** un operando no pertenece a las columnas de origen permitidas
- **THEN** el harness rechaza la historia antes de editar

### Requirement: Validación del resultado

El harness SHALL comprobar que el código editado compila y contiene exactamente la expresión esperada en la columna de salida.

#### Scenario: Edición divergente
- **WHEN** la expresión propuesta o el resultado editado difiere de la razón validada
- **THEN** el harness detiene el flujo sin publicar
