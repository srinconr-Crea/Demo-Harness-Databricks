# Spec Delta

## ADDED Requirements

### Requirement: Encabezados canónicos explícitos del planner
El harness SHALL proporcionar al planner los encabezados estructurales requeridos por las instrucciones CLI del artefacto solicitado e indicar que los conserve literalmente, sin traducirlos, aunque el cuerpo narrativo se redacte en español. SHALL proporcionar estas instrucciones en propose y update, con el gestor de contexto habilitado o deshabilitado y para las estrategias admitidas, sin cambiar los campos propios de cada contrato ni exigir encabezados de proposal a otros artefactos. Las solicitudes de contexto SHALL conservar su contrato individual sin requerir contenido Markdown final.

#### Scenario: Propuesta en español con estructura canónica
- **WHEN** la plantilla de proposal exige Why, What Changes, Capabilities e Impact
- **THEN** el prompt identifica esos títulos literales, exige conservarlos y permite el cuerpo en español

#### Scenario: Actualización y modalidades equivalentes
- **WHEN** planner genera o actualiza un mismo artefacto con el gestor habilitado o deshabilitado
- **THEN** recibe las mismas obligaciones de encabezados y serialización del artefacto, dentro de sus presupuestos y con procedencia registrada

#### Scenario: Artefactos con estructura propia
- **WHEN** planner recibe specs, design o tasks
- **THEN** recibe la estructura propia del artefacto y no hereda encabezados ni manifiesto exclusivos de proposal

#### Scenario: Lectura previa al documento
- **WHEN** planner solicita una operación individual de contexto conforme al contrato
- **THEN** la respuesta se valida como solicitud de contexto antes de exigir estructura Markdown final
