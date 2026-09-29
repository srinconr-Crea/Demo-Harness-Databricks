# Spec Delta

## ADDED Requirements

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
