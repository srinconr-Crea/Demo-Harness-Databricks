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
El harness SHALL conservar los intentos en espera de aclaración o aprobación y sus borradores durante reinicios. Para una etapa activa interrumpida SHALL preservar el último punto de control íntegro y permitir reanudación segura o un reintento trazable, sin repetir publicaciones ya confirmadas.

#### Scenario: Reinicio durante ejecución
- **WHEN** la App inicia y encuentra una etapa activa de otro proceso
- **THEN** conserva el último punto de control, marca la etapa como interrumpida y permite reanudarla de forma controlada

#### Scenario: Reinicio durante aprobación
- **WHEN** la App inicia y encuentra un intento esperando una decisión humana
- **THEN** mantiene la espera y la versión revisable sin crear un nuevo intento

### Requirement: Parada autorizada de la App

El harness SHALL aceptar la solicitud de parada solo tras un estado final, sin otras historias activas y con autorización del operador, y SHALL registrar la solicitud antes de llamar a Databricks.

#### Scenario: Historia todavía activa
- **WHEN** se solicita parar la App mientras existe una historia en ejecución
- **THEN** la solicitud se rechaza

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

### Requirement: Eventos y decisiones reproducibles
El harness SHALL registrar mensajes, transiciones de etapa, revisiones, decisiones humanas, hashes aprobados, pruebas y estado de publicación en orden, asociados a `run_id` y `attempt_id`. SHALL exponer ese progreso incremental a la App y conservar los JSON históricos legibles.

#### Scenario: Aprobación registrada
- **WHEN** una persona aprueba un plan o diff vigente
- **THEN** el registro identifica quién aprobó, cuándo y qué huella de contenido aprobó

#### Scenario: Historial previo
- **WHEN** se consulta una ejecución creada con el contrato anterior
- **THEN** sus intentos y llamadas siguen siendo legibles sin atribuirles aprobaciones inexistentes

### Requirement: Checklist de fases con evidencia
La App SHALL mostrar explore, propose, update cuando aplique, apply, verify, sync, archive y PR con estados y fechas derivados de eventos persistidos del intento y revisión. SHALL conservar tiempos UTC y presentarlos en America/Bogota. SHALL distinguir pendiente, en curso, correcto, fallido, bloqueado y no aplicable; ningún OK SHALL inferirse solo por alcanzar una etapa posterior. La creación del PR y sus checks SHALL mostrarse por separado.

#### Scenario: HU completa
- **WHEN** se confirma creación del PR
- **THEN** se muestra checklist de fases completadas, fechas y enlace al PR con checks reales

#### Scenario: Fallo parcial
- **WHEN** falla archive o publicación
- **THEN** la fase fallida se identifica y las posteriores no aparecen OK

#### Scenario: Reinicio o nueva revisión
- **WHEN** se recupera un intento o se actualiza el plan
- **THEN** el resumen conserva historia y no reutiliza éxitos obsoletos como evidencia vigente

#### Scenario: Recomendación o check pendiente
- **WHEN** Haiku tiene hallazgos o los checks están pending o unavailable
- **THEN** se distinguen de fallos obligatorios y de creación exitosa del PR

### Requirement: Procedencia de instrucciones por fase
El harness SHALL registrar por intento, revisión y llamada la fase, SHA base, ruta relativa y SHA-256 de skills consumidas, versión CLI e identidad y hash de instrucciones CLI aplicables. SHALL vincular evidencia con run_id, attempt_id y call_id, incluidos fallos y rondas de contexto, preservando tokens y costos existentes. Los históricos SHALL admitir procedencia ausente sin rellenarla artificialmente. El registro resumido no SHALL sustituir bytes o referencias protegidas necesarias para reproducir instrucciones.

#### Scenario: Varias rondas del modelo
- **WHEN** un rol realiza solicitudes de contexto antes de devolver su respuesta final
- **THEN** cada llamada registra la misma procedencia de fase y su propio call_id, tokens y costo cuando estén disponibles

#### Scenario: Fase determinista
- **WHEN** sync o archive se ejecutan sin invocar un modelo
- **THEN** su evento registra las skills e instrucciones consumidas y la evidencia real sin inventar llamadas o costos

#### Scenario: Recuperación
- **WHEN** un intento se restaura desde un checkpoint
- **THEN** se comprueban hashes de skills y compatibilidad del runtime con la procedencia guardada antes de continuar

#### Scenario: Instrucciones cambiadas
- **WHEN** los bytes de las skills o el runtime requerido no coinciden con lo registrado
- **THEN** se bloquea la continuación sin actualizar instrucciones ni reutilizar una aprobación como si nada hubiera cambiado

#### Scenario: Lectura histórica
- **WHEN** se consulta un registro sin campos de procedencia
- **THEN** se conserva legible y la procedencia aparece ausente

### Requirement: Procedencia del perfil por intento y llamada
Cada nuevo intento y llamada SHALL registrar nombre, versión, repositorio, modo de carga y SHA-256 de los bytes del perfil activado. SHALL conservar una copia protegida del perfil por referencia para reproducibilidad, separada de prompts y respuestas públicas, sin secretos. Los históricos SHALL admitir estos campos ausentes sin asignarles hashes o aprobaciones ficticios.

#### Scenario: Perfil activado para un intento
- **WHEN** se crea un intento y este invoca modelos
- **THEN** el intento y cada llamada contienen el mismo hash del perfil activado y su procedencia

#### Scenario: Consulta de histórico
- **WHEN** se consulta un registro anterior sin procedencia de perfil
- **THEN** el registro sigue legible y muestra esa procedencia como ausente

### Requirement: Continuación vinculada al perfil original
Antes de ejecutar una etapa, aprobar, reintentar o publicar, el harness SHALL comprobar que el perfil activo corresponde al repositorio y hash del intento. SHALL bloquear continuación del intento y acciones dependientes de su aprobación si el perfil difiere o falta procedencia, conservando consulta y cancelación autorizadas. Como excepción explícita, SHALL permitir crear un nuevo intento del mismo repositorio bajo el perfil vigente mediante una solicitud de reintento humano, sin continuar el candidato anterior. Un cambio aprobado de política SHALL requerir planificación y aprobación nuevas y no SHALL heredar la autorización del intento anterior.

#### Scenario: Reinicio con el mismo perfil
- **WHEN** se restaura un intento con el mismo repositorio y hash de perfil
- **THEN** se permite continuar con sus controles y checkpoints existentes

#### Scenario: Reinicio con otro perfil
- **WHEN** la App recupera un intento cuyo perfil difiere del activo
- **THEN** bloquea continuación, aprobaciones y publicación sin borrar el historial

#### Scenario: Intento previo sin hash
- **WHEN** se intenta continuar un intento histórico sin procedencia de perfil
- **THEN** se exige un reintento explícito bajo el perfil actual y nueva aprobación del plan

#### Scenario: Reintento tras actualizar política
- **WHEN** el usuario solicita explícitamente un nuevo intento del mismo repositorio tras un cambio de perfil
- **THEN** el nuevo intento fija el perfil vigente, vuelve a planificar y exige aprobación sin reutilizar el plan anterior

#### Scenario: Reintento en otro repositorio
- **WHEN** el repositorio activo no coincide con el del registro recuperado
- **THEN** se rechaza el reintento de esa HU en esa instalación
