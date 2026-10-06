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
El harness SHALL diferenciar en el diagnóstico un rechazo del manifiesto de un defecto de representación del contenido, manteniendo invalid_contract como categoría de aceptación y fallo. Para un manifiesto rechazado SHALL identificar la entrada y la restricción incumplida; SHALL mostrar su ruta solo cuando pueda exponerse de forma segura. Para contenido rechazado SHALL identificar el artefacto y motivo; cuando falten encabezados estructurales SHALL identificar los títulos requeridos ausentes de forma ordenada y acotada, según la redacción vigente, sin reproducir arbitrariamente títulos o texto recibidos del modelo. SHALL conservar el vínculo a llamada, intento, revisión y respuesta original protegida, sin exponer contenido restringido ni inventar campos en históricos.

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

#### Scenario: Encabezado traducido
- **WHEN** proposal contiene Qué cambia y la plantilla exige What Changes
- **THEN** el error identifica proposal y What Changes como encabezado requerido ausente, sin traducir o reescribir el documento ni habilitar apply

### Requirement: Diagnóstico y reintento de formato de contexto
Para respuestas nuevas con solicitudes de contexto mal formadas, el harness SHALL persistir acceptance=invalid_contract separado del estado de invocación, categoría invalid_contract en el fallo, etapa de origen, revisión, identidad del fallo y vínculo a call_id y evidencia original protegida. El diagnóstico SHALL distinguir objeto esperado/lista recibida, valor nulo, mezcla con salida final, operación o campos inválidos, y tipos o tamaños incompatibles, sin reproducir arbitrariamente valores del modelo. Estos fallos de formato SHALL permitir reintento humano de la etapa mediante los controles existentes de identidad, failure_id, revisión, perfil, contexto, procedencia, checkpoint íntegro y lease/CAS. SHALL detener el trabajador sin nueva llamada automática de reparación. SHALL conservar el tratamiento existente de denegaciones de política/acceso y presupuestos, sin convertirlas indiscriminadamente en fallos recuperables de formato. Los históricos SHALL conservar mensaje, aceptación y retryable originales.

#### Scenario: Invocación correcta con lista inválida
- **WHEN** el endpoint termina con stop y devuelve context_request como lista
- **THEN** la llamada conserva su invocación completa y uso real, acceptance pasa a invalid_contract, el intento falla indicando objeto esperado/lista recibida y no se realiza ninguna lectura

#### Scenario: Reinicio tras fallo nuevo
- **WHEN** la App reinicia después de persistir un fallo recuperable de formato
- **THEN** mantiene failed sin llamadas nuevas y permite mostrar Reintentar etapa solo con las comprobaciones vigentes

#### Scenario: Reintento humano vigente
- **WHEN** una persona autorizada solicita retry con failure_id y revisión vigentes, y perfil, contexto y checkpoint compatibles
- **THEN** se conserva evidencia anterior, se restaura la etapa desde su checkpoint, se registran nuevas llamadas con identificadores propios y el plan resultante exige aprobación vigente

#### Scenario: Reintento obsoleto o incompatible
- **WHEN** retry presenta una revisión/fallo obsoletos, identidad no autorizada, procedencia incompatible o checkpoint alterado
- **THEN** se rechaza sin llamadas nuevas ni sobrescribir el estado de coordinación posterior

#### Scenario: Denegación de una ruta
- **WHEN** una solicitud individual intenta acceder a una ruta denegada por el perfil
- **THEN** conserva la respuesta controlada de rechazo y su tratamiento vigente, sin leer contenido ni habilitar permisos mediante retry

#### Scenario: Ejecución histórica no reintentable
- **WHEN** se consulta la ejecución fa0d8173517049358f53871d45c49117 después de actualizar el producto
- **THEN** conserva el error y retryable=false originales; no se reescribe para ofrecer reintento retroactivo

### Requirement: Evidencia específica de migración de modelo
La instalación de Sonnet 5.5 SHALL conservar evidencia separada de disponibilidad, compatibilidad de solicitudes, permisos de la App y smoke funcional. SHALL identificar endpoint, configuración de capacidades, límites efectivos, finish_reason cuando exista y usage/costo estimado propio por llamada. SHALL configurar tarifas de Sonnet 5.5 con fuente y fecha como supuestos estimados, sin atribuirle automáticamente tarifas de Sonnet 5; tarifas no verificadas SHALL bloquear la activación operativa hasta configurar una estimación documentada. SHALL mantener costo ausente cuando no haya usage. La consulta histórica no SHALL recalcular costos previos con las tarifas nuevas.

#### Scenario: Endpoint disponible
- **WHEN** una consulta de operador confirma READY en Sonnet 5.5
- **THEN** se registra como disponibilidad sin presentarla como prueba de permisos de la App, JSON Schema, límite aceptado o éxito de una HU

#### Scenario: Smoke sintético del endpoint
- **WHEN** una prueba breve comprueba límite efectivo de 64.000 y, si se pretende habilitar, JSON Schema
- **THEN** registra la solicitud efectiva y respuesta con terminación, uso, duración y costo estimado cuando existan, sin exigir generar 64.000 tokens ni usar datos cliente

#### Scenario: Tarifas específicas e histórico
- **WHEN** se activan tarifas estimadas documentadas para Sonnet 5.5 y se consultan llamadas previas de Sonnet 5
- **THEN** las nuevas llamadas usan su fuente configurada y las anteriores conservan sus costos y procedencia originales

#### Scenario: Uso ausente
- **WHEN** el endpoint nuevo no entrega uso de tokens
- **THEN** el costo queda ausente y no se presenta como cero facturado

### Requirement: Reintento humano de presentación de artefactos
Para fallos nuevos, el harness SHALL distinguir defectos de presentación Markdown de denegaciones de política, manifiesto inválido o incompatibilidad de configuración. Los defectos de encabezados o representación del contenido SHALL conservar acceptance y categoría invalid_contract y permitir reintento humano de la etapa fallida mediante los controles vigentes de identidad autorizada, failure_id, revisión, perfil, contexto, procedencia, checkpoint íntegro y lease/CAS. SHALL conservar artefactos parciales y evidencias de llamadas, restaurar el checkpoint y requerir aprobación vigente del plan resultante antes de apply. SHALL detener el trabajador sin corrección automática del contrato y mantener failed tras reinicios. La consulta histórica SHALL conservar su mensaje y retryable originales. Esta capacidad SHALL no convertir indiscriminadamente errores de política, presupuesto o configuración en fallos recuperables de presentación.

#### Scenario: Propuesta rechazada por un título ausente
- **WHEN** una ejecución nueva falla porque un artefacto carece de un encabezado requerido
- **THEN** persiste failed con etapa de origen, identidad del fallo y recuperabilidad humana, sin llamadas automáticas adicionales ni éxito de fases posteriores

#### Scenario: Artefacto anterior válido
- **WHEN** proposal es válido y un artefacto posterior falla su presentación
- **THEN** se conserva proposal en el checkpoint como evidencia parcial y retry restaura el estado íntegro sin tratar ese documento como plan aprobado

#### Scenario: Reintento humano autorizado
- **WHEN** una persona autorizada solicita retry con fallo y revisión vigentes y procedencia, perfil, contexto y checkpoint compatibles
- **THEN** se restaura la etapa, se conserva la evidencia anterior y las llamadas nuevas tienen identificadores propios; el plan corregido requiere aprobación vigente

#### Scenario: Reintento obsoleto o competidor
- **WHEN** retry presenta failure_id o revisión obsoletos, identidad no autorizada, checkpoint alterado o un lease ya reclamado
- **THEN** se rechaza sin nuevas llamadas ni sobrescribir una transición posterior

#### Scenario: Reinicio sin reintento humano
- **WHEN** la App reinicia tras un fallo de presentación persistido
- **THEN** conserva failed y su diagnóstico sin invocar el modelo ni reanudar la etapa automáticamente

#### Scenario: Denegación de política
- **WHEN** el manifiesto excede rutas u operaciones autorizadas
- **THEN** conserva su tratamiento de política y no recibe recuperabilidad por la clasificación de presentación

#### Scenario: Intento histórico analizado
- **WHEN** se consulta 9f4d553d17ea406ca596600875735656 después de activar el cambio
- **THEN** conserva el mensaje original y retryable=false; repetir la HU requiere una ejecución nueva con planificación y aprobación propias
