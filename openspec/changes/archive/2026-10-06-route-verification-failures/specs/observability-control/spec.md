## ADDED Requirements

### Requirement: Trazabilidad y continuidad de correcciones clasificadas
Para intentos nuevos el harness SHALL persistir la categoría del fallo, evidencia de origen, motivo de la ruta elegida, revisión/hash del plan, versión/hash del candidato, contador de correcciones y referencias de progreso. SHALL mostrar correcting como fase distinguible de update, con causa comprensible y controles técnicos/semánticos pendientes separados del éxito anterior. SHALL registrar notas del developer y procedencia de lecturas/pruebas en almacenamiento protegido, aplicando redacción vigente a mensajes públicos. SHALL conservar cada llamada y su costo estimado cuando exista usage, sin ampliar el contrato asesor Haiku. Checkpoints y coordinación SHALL permitir una sola continuación consistente después de un reinicio, sin duplicar correcciones lógicas ni publicaciones, reiniciar el presupuesto o considerar vigente una verificación de otros bytes. Históricos SHALL conservar modalidad, registros y mensajes sin completar retroactivamente campos ausentes; intentos activos con contrato anterior SHALL continuar bajo su contrato compatible o detenerse con indicación de nuevo intento explícito.

#### Scenario: Corrección visible
- **WHEN** un fallo de implementación inicia correcting
- **THEN** la App muestra la corrección y su causa sin mostrar una nueva revisión del plan ni verify aprobado para el candidato pendiente

#### Scenario: Reinicio durante corrección
- **WHEN** un intento nuevo reinicia con checkpoint compatible de correcting
- **THEN** recupera plan, candidato, contador y fallo vigentes mediante coordinación sin dos trabajadores ni consumo duplicado de la misma corrección lógica

#### Scenario: Ciclo sin progreso
- **WHEN** el harness detiene un bloqueo repetido
- **THEN** muestra la causa y conserva referencias a resultados equivalentes sin convertirlo en un nuevo alcance solicitado por el developer

#### Scenario: Consulta histórica
- **WHEN** se consulta f9c8efe4b82449b98e0de1ea749c6a0e tras el cambio
- **THEN** conserva sus eventos originales, un verify y cuatro scope_changed, sin reescribirlos como correcting o atribuir nuevas verificaciones
