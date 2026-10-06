# agent-prompt-contracts Specification

## Purpose

Proporcionar prompts y contratos confiables por rol/fase y herramientas acotadas, con salidas verificadas sin elevar a autoridad la HU o contenido recuperado.

## Requirements

### Requirement: Prompts versionados en todas las rutas
El harness SHALL componer cada system prompt desde base confiable y contrato de rol/fase con responsabilidad, restricciones y salida; SHALL fijar versión/hash por intento y registrarlos por llamada. SHALL cubrir explorer, planner, developer, openspec_verifier obligatorio y verifier asesor, incluida ruta asesora independiente. Ningún contenido recuperado SHALL sustituir base confiable o elegir modelos.

#### Scenario: Planner por artefacto
- **WHEN** planner propone o actualiza un artefacto
- **THEN** recibe contrato específico de artefacto/estrategia y base confiable con procedencia, sin manifest obligatorio cuando no corresponde

#### Scenario: Contrato ausente
- **WHEN** rol/fase carece de contrato compatible
- **THEN** se bloquea esa invocación sin fallback genérico silencioso; ausencia asesora conserva su carácter no bloqueante

#### Scenario: Revisión asesora independiente
- **WHEN** se invoca verifier por su ruta independiente
- **THEN** recibe contrato asesor y prompt confiable registrados sin convertir su resultado en autorización

### Requirement: Contratos de herramientas acotados
Las operaciones de contexto autorizadas SHALL declarar argumentos, tipos, campos permitidos, tamaños, respuestas, errores y truncamientos junto a su contrato. SHALL validar antes de lectura y conservar acceso según perfil. SHALL limitarse a list_tree/search_text/read_file cuando el rol/fase tiene retrieval habilitado; skills no SHALL habilitar shell ni tools adicionales. Con gestor de contexto habilitado o deshabilitado, el prompt SHALL declarar el mismo contrato de una operación por turno: una respuesta de contexto contiene exclusivamente context_request como objeto; list_tree admite exclusivamente op, read_file admite op y path, y search_text admite op y query. SHALL proporcionar ejemplos exactos, exigir path relativo autorizado de hasta 500 caracteres y query string de 1 a 200 caracteres, y conservar los límites del perfil. Tras cada resultado el modelo SHALL poder solicitar otra operación individual o entregar el contrato final propio del rol.

#### Scenario: Lectura válida
- **WHEN** read_file recibe ruta relativa autorizada de archivo regular
- **THEN** entrega contenido/hash y estado de truncamiento explícito

#### Scenario: Solicitud inválida
- **WHEN** context_request contiene traversal, campos desconocidos, tipos inválidos u operación no autorizada
- **THEN** se rechaza antes de leer y sin exponer contenido denegado

#### Scenario: Evidencia truncada
- **WHEN** búsqueda o lectura excede límites
- **THEN** informa truncamiento y no afirma haber inspeccionado contenido omitido

#### Scenario: Lista de solicitudes
- **WHEN** una respuesta contiene context_request como lista de varias operaciones
- **THEN** se rechaza la respuesta completa sin ejecutar ningún elemento ni convertirla automáticamente en turnos individuales

#### Scenario: Campo adicional de alcance
- **WHEN** list_tree o search_text incluye path
- **THEN** se rechaza el formato antes de inventariar, buscar o leer archivos

#### Scenario: Solicitud nula o mezclada
- **WHEN** context_request está presente con valor null o junto a campos de salida final
- **THEN** se rechaza como solicitud inválida sin interpretarla como respuesta final

#### Scenario: Lecturas sucesivas
- **WHEN** el modelo entrega read_file válido, recibe su resultado y después entrega search_text válido
- **THEN** se procesa una operación por llamada, se acumulan los resultados autorizados dentro de los presupuestos y se acepta la salida final solo tras su validación

#### Scenario: Modalidades equivalentes
- **WHEN** el mismo rol y perfil solicita contexto con el gestor habilitado o deshabilitado
- **THEN** recibe las mismas formas, ejemplos, límites de argumentos y prohibición de lotes, con las mismas validaciones de solicitud

#### Scenario: Rol sin retrieval
- **WHEN** un rol/fase sin retrieval habilitado solicita una operación de contexto
- **THEN** se rechaza sin habilitar herramientas por influencia del prompt o de una skill

### Requirement: Salidas validadas según contrato
El harness SHALL validar outputs finales y context_requests específicos por rol/artefacto/estrategia, incluidos campos/tipos/tamaños y política/manifiesto posteriores al schema. SHALL distinguir preguntas, contenido/manifiesto, operaciones y hallazgos. Output inválido no SHALL provocar edición, transición exitosa ni publicación.

#### Scenario: Operación prohibida en JSON válido
- **WHEN** developer devuelve shell/rutas/operaciones fuera del manifiesto
- **THEN** se rechaza o vuelve a revisión según flujo vigente sin ejecutar la operación

#### Scenario: Preguntas válidas
- **WHEN** explorer entrega preguntas conformes al contrato
- **THEN** se conservan y se espera aclaración mediante acciones existentes

### Requirement: Frontera de autoridad y roles conservados
Los prompts SHALL identificar fuentes/memoria como datos y conservar Sonnet/pruebas obligatorios y Haiku asesor sin nuevas aprobaciones. Sync/archive SHALL seguir deterministas. El gestor no SHALL introducir rol compactor ni llamadas auxiliares de resumen.

#### Scenario: Memoria pide omitir pruebas
- **WHEN** fuente o decisión contiene instrucciones para cambiar permisos o saltar validación
- **THEN** política, modelos, fases y autorizaciones permanecen sujetos a controles originales

#### Scenario: Fase determinista
- **WHEN** sync/archive o reducción local ocurren sin modelo
- **THEN** se conserva evidencia sin llamada ni costo ficticio

### Requirement: Separación explícita de las salidas de planificación
El contrato confiable del planner SHALL distinguir el contenido del artefacto OpenSpec de las operaciones del manifiesto de código. SHALL indicar que los artefactos OpenSpec se gestionan por el recorrido de planificación y no pertenecen al manifiesto del desarrollador. SHALL solicitar los campos obligatorios según artefacto y estrategia, manteniendo lecturas autorizadas de contexto y la política del perfil.

#### Scenario: Propuesta de código general
- **WHEN** planner genera o actualiza proposal para general_patch
- **THEN** recibe un contrato que exige content, summary y un manifiesto exclusivo de operaciones de código y pruebas permitidas por el perfil

#### Scenario: Otros artefactos y estrategia acotada
- **WHEN** planner genera specs, design o tasks, o planifica la estrategia silver_safe_ratio
- **THEN** recibe el contrato de esa salida sin heredar campos obligatorios exclusivos de proposal general_patch ni ampliar rutas u operaciones

#### Scenario: Artefacto OpenSpec en el manifiesto
- **WHEN** una salida incluye una operación sobre un artefacto OpenSpec dentro del manifiesto de código
- **THEN** el harness rechaza ese manifiesto sin trasladar, eliminar ni ejecutar silenciosamente la operación

### Requirement: Representación única del contenido del artefacto
El contrato confiable SHALL solicitar content como texto Markdown serializado una sola vez en el JSON externo. Después de interpretar el JSON, los separadores del documento SHALL ser saltos reales; las secuencias literales legítimas SHALL conservarse en el contenido. El schema de salida SHALL complementar, sin sustituir, las validaciones del artefacto y del manifiesto.

#### Scenario: Markdown correctamente serializado
- **WHEN** la respuesta contiene saltos JSON escapados una vez y el contenido interpretado cumple la estructura del artefacto
- **THEN** el contenido aceptado conserva sus saltos de línea reales

#### Scenario: Escape literal en un ejemplo
- **WHEN** un documento válido incluye secuencias literales como barra invertida seguida de n dentro de un ejemplo de código
- **THEN** esas secuencias se conservan y no se convierten indiscriminadamente en saltos

#### Scenario: Lectura de contexto previa
- **WHEN** planner devuelve una solicitud de contexto autorizada antes de producir content
- **THEN** se valida como solicitud de contexto y no se le exige estructura Markdown de un artefacto final

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
