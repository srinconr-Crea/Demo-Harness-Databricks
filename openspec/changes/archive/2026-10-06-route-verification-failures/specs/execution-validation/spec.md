## MODIFIED Requirements

### Requirement: Verificación específica y ciclo de corrección
Cada tipo e impacto de cambio SHALL disponer de controles deterministas y pruebas funcionales pertinentes configurados por el operador, además de verificación OpenSpec obligatoria Sonnet. SHALL seleccionar adaptadores sobre el diff acumulado del candidato respecto de la base y sus componentes afectados. Un descuadre obligatorio SHALL conservar evidencia y clasificarse antes de continuar: implementación dentro del contrato aprobado, especificación/alcance, infraestructura/evidencia o defecto del harness. La clasificación del modelo SHALL ser una propuesta validada por el harness, sin conferir permisos. Un error de implementación corregible dentro del plan y manifiesto vigentes SHALL pasar a correcting y después a validación técnica y verificación Sonnet, sin planner ni nueva aprobación. Un cambio requerido del contrato autorizado SHALL pasar a update, validar una nueva revisión y esperar aprobación humana antes de apply. Infraestructura indisponible, evidencia insuficiente, clasificación ambigua y defectos del harness SHALL admitir solo recuperación acotada compatible con los controles existentes o detenerse con diagnóstico, sin publicar ni generar planes repetidos. Hallazgos mezclados que requieran cambiar lo autorizado SHALL impedir la corrección dependiente hasta nueva aprobación. Denegaciones de política y respuestas inválidas SHALL mantener sus controles de rechazo y no convertirse en correcciones de implementación por conveniencia.

#### Scenario: Descuadre corregible
- **WHEN** verify encuentra diferencias entre código, specs y pruebas
- **THEN** conserva los hallazgos y clasifica su causa antes de continuar sin publicar: implementación autorizada pasa a correcting, cambio del contrato pasa a revisión del plan, y falta de evidencia o defecto del harness pasa a recuperación acotada o diagnóstico bloqueante

#### Scenario: Error técnico dentro del manifiesto
- **WHEN** la validación identifica un import incorrecto en un archivo autorizado y la reparación conserva el contrato aprobado
- **THEN** se invoca correcting con evidencia del fallo y se vuelve a verificar sin update ni aprobación adicional

#### Scenario: Incumplimiento semántico de implementación
- **WHEN** Sonnet detecta que el candidato no preserva las mayúsculas exigidas por la spec aprobada y puede corregirse dentro del manifiesto
- **THEN** se corrige el candidato y se repiten controles técnicos y Sonnet sobre sus bytes actuales

#### Scenario: Alcance adicional necesario
- **WHEN** resolver el fallo exige una tabla, archivo, operación o criterio no autorizado
- **THEN** se conserva la justificación, se actualiza el plan y no se edita el alcance adicional antes de su aprobación humana

#### Scenario: Hallazgos mezclados
- **WHEN** existen fallos de implementación y otro hallazgo obliga a cambiar la especificación aprobada
- **THEN** se replanifica y la corrección dependiente espera la nueva aprobación

#### Scenario: Prueba no disponible
- **WHEN** una comprobación obligatoria no puede ejecutarse por indisponibilidad del sandbox
- **THEN** se informa no verificado, se bloquea publicación y no se manda automáticamente al developer a modificar código ni al planner a replanificar

#### Scenario: Evidencia insuficiente
- **WHEN** falta confirmar un consumidor mediante una lectura permitida
- **THEN** se obtiene evidencia acotada o se detiene con causa explícita, sin inventar un cambio de alcance

#### Scenario: Defecto del harness
- **WHEN** el runtime impone un destino OpenSpec que contradice la capacidad aprobada
- **THEN** se detiene indicando defecto del producto sin delegar al cliente una reparación que no puede ejecutar

#### Scenario: Configuración con impacto funcional
- **WHEN** un YAML modifica comportamiento de un componente Python
- **THEN** se valida YAML y se ejecuta la suite funcional configurada

#### Scenario: Eliminación
- **WHEN** se elimina un archivo de un componente
- **THEN** se ejecutan las pruebas configuradas de ese componente y se comprueban referencias pertinentes

## ADDED Requirements

### Requirement: Correcciones automáticas finitas y con progreso
El harness SHALL admitir como máximo dos invocaciones automáticas de corrección de implementación por intento, compartidas entre validación técnica y Sonnet, con contador persistente que no se reinicia por update, cambio de etapa o reinicio. SHALL detenerse antes de una tercera corrección. SHALL detectar la repetición del mismo bloqueo sin cambios pertinentes del candidato, contrato autorizado o evidencia nueva relevante, incluyendo ciclos de apply/update, y detenerse antes de otra regeneración o corrección equivalente. Una redacción distinta, timestamp, nueva aprobación del mismo alcance o nuevo identificador de llamada no SHALL contar como progreso. La recuperación acotada de evidencia SHALL conservar los presupuestos existentes y no permitir llamadas indefinidas. El rechazo asesor Haiku no SHALL consumir este presupuesto.

#### Scenario: Presupuesto compartido
- **WHEN** hubo una corrección técnica y otra por incumplimiento detectado por Sonnet y el candidato sigue rechazado
- **THEN** se detiene sin tercera invocación automática ni publicación

#### Scenario: Reinicio o replanificación
- **WHEN** el intento reinicia o actualiza el plan después de una corrección
- **THEN** conserva el número consumido y la evidencia de progreso

#### Scenario: Repetición sin progreso
- **WHEN** reaparece el mismo bloqueo y solo cambió la redacción del plan
- **THEN** se detiene con referencias a ambos resultados sin otra regeneración equivalente

### Requirement: Evidencia vigente entre desarrollo y verificación
El harness SHALL entregar al developer y verificador el contrato aprobado, hallazgos pendientes, notas y lecturas pertinentes con ruta/hash/origen, y pruebas vinculadas al candidato que las produjo. Las notas del modelo SHALL conservarse como afirmaciones, sin convertirse en pruebas o decisiones humanas. El verificador SHALL poder solicitar lecturas autorizadas bajo los presupuestos existentes. Todo cambio de bytes SHALL invalidar aprobaciones semánticas y resultados de pruebas usados para publicar el candidato anterior y exigir controles técnicos y Sonnet sobre el candidato actual. Las tareas SHALL distinguir implementación, verificación y acciones posteriores de publicación sin marcar pruebas o PR como completados por inferencia.

#### Scenario: Lectura realizada por developer
- **WHEN** developer confirmó io.py mediante lectura autorizada con hash vigente
- **THEN** el verificador recibe esa evidencia o su referencia recuperable y puede comprobarla sin declararla ausente por falta de transferencia

#### Scenario: Notas sin ejecución
- **WHEN** developer afirma que las pruebas pasan sin evidencia del runner
- **THEN** se conserva la nota sin considerarla aprobación de pruebas

#### Scenario: Candidato corregido
- **WHEN** correcting modifica un archivo tras un resultado técnico exitoso previo
- **THEN** el resultado previo queda histórico y se verifican los bytes actuales antes de publicar

#### Scenario: Tareas de publicación pendientes
- **WHEN** implementación y pruebas están verificadas pero sync, archive y PR no han ocurrido
- **THEN** esas tareas permanecen pendientes sin impedir verify por su posición posterior en el workflow
