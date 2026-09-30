# Spec Delta

## MODIFIED Requirements

### Requirement: Recuperación de ejecuciones interrumpidas
El harness SHALL conservar los intentos en espera de aclaración o aprobación y sus borradores durante reinicios. Para una etapa activa interrumpida SHALL preservar el último punto de control íntegro y permitir reanudación segura o un reintento trazable, sin repetir publicaciones ya confirmadas.

#### Scenario: Reinicio durante ejecución
- **WHEN** la App inicia y encuentra una etapa activa de otro proceso
- **THEN** conserva el último punto de control, marca la etapa como interrumpida y permite reanudarla de forma controlada

#### Scenario: Reinicio durante aprobación
- **WHEN** la App inicia y encuentra un intento esperando una decisión humana
- **THEN** mantiene la espera y la versión revisable sin crear un nuevo intento

### Requirement: Trazabilidad de la planificación
El harness SHALL registrar por intento y revisión el identificador del cambio OpenSpec, etapa, validación, referencias de artefactos y sus hashes, enlazados con las llamadas de `explore`, planner, desarrollador y verificador en los JSON actuales de `agent_calls`, con modelo, tokens y costo estimado cuando el endpoint informe uso.

#### Scenario: Planificación aprobada
- **WHEN** el planner produce artefactos válidos
- **THEN** el intento registra sus referencias, hashes, versión y resultado de validación

#### Scenario: Planificación fallida
- **WHEN** el planner o la CLI falla
- **THEN** el intento registra el fallo y conserva las llamadas y artefactos disponibles para diagnóstico, sin tratarlos como aprobados

#### Scenario: Uso de tokens no informado
- **WHEN** una llamada de cualquier etapa no informa tokens
- **THEN** su JSON conserva rol, etapa y modelo, deja ausente el costo estimado y no lo presenta como facturación real

## ADDED Requirements

### Requirement: Eventos y decisiones reproducibles
El harness SHALL registrar mensajes, transiciones de etapa, revisiones, decisiones humanas, hashes aprobados, pruebas y estado de publicación en orden, asociados a `run_id` y `attempt_id`. SHALL exponer ese progreso incremental a la App y conservar los JSON históricos legibles.

#### Scenario: Aprobación registrada
- **WHEN** una persona aprueba un plan o diff vigente
- **THEN** el registro identifica quién aprobó, cuándo y qué huella de contenido aprobó

#### Scenario: Historial previo
- **WHEN** se consulta una ejecución creada con el contrato anterior
- **THEN** sus intentos y llamadas siguen siendo legibles sin atribuirles aprobaciones inexistentes
