# Spec Delta

## ADDED Requirements

### Requirement: Trazabilidad de la planificación

El harness SHALL registrar por intento el identificador del cambio OpenSpec, el estado de validación, las rutas o referencias de los artefactos y sus hashes, enlazados con las llamadas del planner.

#### Scenario: Planificación aprobada
- **WHEN** el planner produce artefactos válidos
- **THEN** el intento registra sus referencias, hashes y el resultado de validación

#### Scenario: Planificación fallida
- **WHEN** el planner o la CLI falla
- **THEN** el intento registra el fallo y conserva las llamadas y artefactos disponibles para diagnóstico, sin tratarlos como aprobados
