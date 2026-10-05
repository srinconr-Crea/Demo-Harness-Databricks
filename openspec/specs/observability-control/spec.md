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

### Requirement: Trazabilidad de selección y prompts
El harness SHALL registrar por HU/intento/revisión/etapa/llamada política, versión/hash de prompt/contrato, fuentes/hash, decisión de contexto, razones de inclusión/exclusión, bytes completos antes/después, estimación identificada y cache hit/miss/invalidaciones. SHALL conservar evidencia protegida sin exponer memoria/prompts restringidos ni inventar históricos.

#### Scenario: Contexto reducido
- **WHEN** una llamada reutiliza cache y elimina duplicados
- **THEN** sus fuentes, decisiones preservadas, exclusiones y bytes enviados son auditables sin revelar contenido protegido en hilo público

#### Scenario: Histórico anterior
- **WHEN** una llamada no contiene campos nuevos
- **THEN** aparecen ausentes y no se presentan como decisiones observadas

### Requirement: Medición comparable sin ahorro ficticio
La evaluación SHALL comparar escenarios con mismas entradas, respuestas y solicitudes de contexto, registrando llamadas, bytes enviados, latencia y usage/costo estimado solo cuando existe. Cache/reducción local no SHALL generar llamadas ficticias ni presentarse como ahorro facturado. SHALL verificar preservación de decisiones y controles, separando mediciones locales de pruebas remotas.

#### Scenario: Cache sin reducción de entrada
- **WHEN** un hit evita lectura local pero envía los mismos bytes al modelo
- **THEN** se informa reutilización de I/O sin atribuir reducción de tokens

#### Scenario: Uso ausente
- **WHEN** endpoint no proporciona usage
- **THEN** costo queda ausente, no cero, y no se afirma ahorro de costo comprobado

#### Scenario: Comparación y estrés
- **WHEN** se ejecutan fixtures comparables y estrés acotado de múltiples turnos
- **THEN** se conservan decisiones/autorizaciones requeridas o se bloquea correctamente por presupuesto, sin promesa universal de duración

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

### Requirement: Diagnóstico específico del contrato de planificación rechazado
El harness SHALL diferenciar en el diagnóstico un rechazo del manifiesto de un defecto de representación del contenido, manteniendo invalid_contract como categoría de aceptación y fallo. Para un manifiesto rechazado SHALL identificar la entrada y la restricción incumplida; SHALL mostrar su ruta solo cuando pueda exponerse de forma segura. Para contenido rechazado SHALL identificar el artefacto y motivo. SHALL conservar el vínculo a llamada, intento, revisión y respuesta original protegida, sin exponer contenido restringido ni inventar campos en históricos.

#### Scenario: Entrada OpenSpec rechazada
- **WHEN** la tercera entrada del manifiesto intenta modificar una delta OpenSpec
- **THEN** el error identifica esa entrada y que OpenSpec se gestiona fuera del manifiesto de código, con ruta segura o referencia protegida al detalle

#### Scenario: Representación inválida del documento
- **WHEN** el JSON es válido pero content no cumple la estructura Markdown por serialización adicional
- **THEN** el error identifica el artefacto y ese motivo sin presentarlo como JSON mal formado ni respuesta truncada

#### Scenario: Error con datos restringidos
- **WHEN** una entrada o respuesta rechazada contiene datos que la redacción vigente no permite exponer
- **THEN** el diagnóstico público conserva índice y motivo seguro y el detalle permanece en evidencia protegida

#### Scenario: Histórico anterior
- **WHEN** se consulta un rechazo anterior sin diagnóstico específico
- **THEN** conserva su mensaje y evidencia originales sin atribuirle una validación nueva
