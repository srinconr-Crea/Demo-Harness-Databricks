# Spec Delta

## ADDED Requirements

### Requirement: Evidencia de terminación y recuperación de respuesta
Cada llamada nueva SHALL conservar límite efectivo, finish_reason cuando exista y resultado de aceptación separado del estado de invocación. Una llamada de corrección SHALL tener call_id propio, vínculo a la original, mismo run_id/attempt_id/revisión y procedencia, y usage/costo estimado propio cuando exista. La normalización local SHALL registrarse sin inventar llamadas o costos. La respuesta original y el resultado normalizado SHALL conservar hashes y evidencia protegida; el truncamiento del log resumido SHALL distinguirse del corte del modelo.

#### Scenario: HTTP correcto y respuesta truncada
- **WHEN** el endpoint responde correctamente pero termina por límite
- **THEN** la evidencia diferencia invocación completa de respuesta rechazada por output_truncated

#### Scenario: Recuperación con dos llamadas
- **WHEN** una respuesta mal formada requiere una llamada de corrección
- **THEN** ambas llamadas quedan enlazadas con sus tokens y costos respectivos sin duplicar uso

#### Scenario: Log resumido truncado
- **WHEN** una respuesta completa supera el límite de caracteres del log
- **THEN** se señala el recorte del resumen sin clasificarlo como output_truncated

#### Scenario: Histórico sin nuevos campos
- **WHEN** se consulta una llamada anterior sin motivo de terminación ni aceptación registrada
- **THEN** esos campos quedan ausentes y el histórico permanece legible

### Requirement: Fallo recuperable persistente y coordinado
Un fallo de etapa SHALL finalizar el trabajador y persistir estado failed coherente entre ejecución, intento y coordinación, con categoría, etapa de origen, revisión, identidad del fallo y recuperabilidad explícitas. SHALL conservar aclaraciones, llamadas, artefactos disponibles y último checkpoint íntegro, sin aprobación implícita ni éxito de fases posteriores. El reinicio SHALL mantener el fallo y no reintentarlo automáticamente. Una pérdida de lease o de almacenamiento SHALL impedir una transición falsa y conservar la evidencia íntegra disponible.

#### Scenario: Planner falla después de proposal
- **WHEN** se genera proposal y falla un artefacto posterior
- **THEN** el estado es failed, el error identifica la fase de planificación y proposal queda disponible como evidencia parcial sin habilitar apply

#### Scenario: Reinicio después del fallo
- **WHEN** la App reinicia tras persistir un fallo recuperable
- **THEN** conserva failed, la etapa de origen y evidencia sin ejecutar llamadas nuevas hasta retry autorizado

#### Scenario: Fallo de almacenamiento
- **WHEN** no se puede persistir íntegramente el fallo o se pierde el lease
- **THEN** no se sobrescribe una transición más reciente ni se declara persistencia exitosa; se conserva el checkpoint íntegro previo y se diagnostica la inconsistencia
