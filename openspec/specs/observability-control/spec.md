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
