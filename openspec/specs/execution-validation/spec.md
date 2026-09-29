# Execution Validation Specification

## Purpose

Establecer los controles que deben pasar antes de publicar un cambio de código cliente.

## Requirements

### Requirement: Secuencia de controles

El harness SHALL exigir que el análisis de alcance, la propuesta del desarrollador, la validación del editor, la prueba remota y la revisión del verificador terminen satisfactoriamente antes de publicar.

#### Scenario: Todos los controles aprobados
- **WHEN** cada control produce un resultado válido y aprobatorio
- **THEN** el flujo puede iniciar la publicación

#### Scenario: Control rechazado
- **WHEN** cualquier control falla o entrega una salida inválida
- **THEN** el flujo se detiene sin iniciar la publicación

### Requirement: Sandbox sintético aislado

La validación remota de `silver_safe_ratio` SHALL comprobar tres filas sintéticas en el SQL warehouse configurado: denominador positivo, cero y NULL.

#### Scenario: Resultados esperados
- **WHEN** la expresión devuelve el cociente para un denominador positivo y NULL para cero o NULL
- **THEN** la prueba remota aprueba

#### Scenario: Resultado incompleto o erróneo
- **WHEN** faltan filas, la consulta falla o el resultado no coincide
- **THEN** la prueba remota rechaza el cambio

### Requirement: Alcance explícito de la prueba

El reporte de validación SHALL distinguir la prueba SQL sintética de una ejecución completa del notebook del cliente.

#### Scenario: Resumen previo al PR
- **WHEN** el harness prepara el resumen de publicación
- **THEN** informa que la prueba SQL no ejecutó el notebook completo
