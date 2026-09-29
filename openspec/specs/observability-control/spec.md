# Observability and Control Specification

## Purpose

Conservar evidencia enlazable de ejecuciones, intentos y llamadas a modelos, y ofrecer controles operativos de la App.

## Requirements

### Requirement: Registros enlazables

El harness SHALL registrar cada ejecución, intento y llamada al modelo con identificadores que permitan unir la evidencia de una historia sin confundir reintentos.

#### Scenario: Varias llamadas en un intento
- **WHEN** un intento invoca varios roles
- **THEN** cada llamada conserva `run_id`, `attempt_id` y un `call_id` propio

### Requirement: Uso y costo estimado

El harness SHALL guardar los tokens informados por el endpoint y un costo estimado cuando los datos de uso estén disponibles, distinguiendo esa estimación de facturación real.

#### Scenario: Uso no reportado
- **WHEN** el endpoint no entrega tokens
- **THEN** el costo estimado queda ausente y no se presenta como cero facturado

### Requirement: Recuperación de ejecuciones interrumpidas

El harness SHALL marcar como interrumpidos los intentos activos de un proceso anterior al iniciar la App, preservando sus registros.

#### Scenario: Reinicio durante ejecución
- **WHEN** la App inicia y encuentra una ejecución en cola o activa de otra instancia
- **THEN** registra el estado interrumpido y permite un reintento trazable

### Requirement: Parada autorizada de la App

El harness SHALL aceptar la solicitud de parada solo tras un estado final, sin otras historias activas y con autorización del operador, y SHALL registrar la solicitud antes de llamar a Databricks.

#### Scenario: Historia todavía activa
- **WHEN** se solicita parar la App mientras existe una historia en ejecución
- **THEN** la solicitud se rechaza

### Requirement: Trazabilidad de la planificación

El harness SHALL registrar por intento el identificador del cambio OpenSpec, el estado de validación, las rutas o referencias de los artefactos y sus hashes, enlazados con todas las llamadas del planner a `databricks-claude-sonnet-5` en los JSON actuales de `agent_calls`, con tokens y costo estimado cuando el endpoint informe uso.

#### Scenario: Planificación aprobada
- **WHEN** el planner produce artefactos válidos
- **THEN** el intento registra sus referencias, hashes y el resultado de validación

#### Scenario: Planificación fallida
- **WHEN** el planner o la CLI falla
- **THEN** el intento registra el fallo y conserva las llamadas y artefactos disponibles para diagnóstico, sin tratarlos como aprobados

#### Scenario: Uso de tokens no informado
- **WHEN** una llamada del planner no informa tokens
- **THEN** su JSON conserva el rol y modelo, deja ausente el costo estimado y no lo presenta como facturación real
