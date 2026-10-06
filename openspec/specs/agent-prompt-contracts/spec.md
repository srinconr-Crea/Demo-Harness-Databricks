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

### Requirement: Contrato explícito de operaciones del desarrollador
El harness SHALL entregar en cada llamada del desarrollador general_patch un contrato confiable de salida que declare campos, tipos, restricciones condicionales y ejemplos de create, modify y delete, coherente con el editor. SHALL exigir op y path; create requiere content y hash previo ausente o null, modify requiere content y expected_sha256, y delete requiere expected_sha256 y content ausente o null. content SHALL representar el archivo completo como texto UTF-8, serializado una sola vez, y expected_sha256 SHALL identificar los bytes actuales previamente leídos con 64 caracteres hexadecimales minúsculos. SHALL declarar que nombres alternativos como base_sha256 y otros campos desconocidos se rechazan. El contrato SHALL mantenerse separado de la descripción de tareas, presente en aplicación y corrección y después de cada lectura, con el gestor habilitado o deshabilitado. El contrato SHALL conservar los límites y operaciones autorizados del perfil, sin garantizar conformidad semántica por aceptación de formato.

#### Scenario: Modificación canónica
- **WHEN** el desarrollador propone modificar una ruta aprobada
- **THEN** recibe un ejemplo que usa expected_sha256 obtenido de la lectura actual y content de archivo completo; la salida canónica pasa a los controles de hash, manifiesto y política antes de escribir

#### Scenario: Creación y borrado
- **WHEN** se construye el contrato para operaciones autorizadas de creación o borrado
- **THEN** los ejemplos de creación exigen archivo ausente y contenido completo sin hash previo, y los de borrado exigen archivo existente con hash previo y sin contenido

#### Scenario: Instrucción de corrección no elimina el contrato
- **WHEN** la tarea de applying se reemplaza por la descripción de correcting
- **THEN** el contrato conserva los mismos campos y reglas de operaciones, incluidos expected_sha256 y rechazo de aliases

#### Scenario: Contexto y modalidades equivalentes
- **WHEN** el desarrollador solicita una lectura individual antes de entregar operaciones, con el gestor habilitado o deshabilitado
- **THEN** la llamada siguiente conserva el contrato final completo y la solicitud de contexto mantiene su forma exclusiva sin operaciones ni cobertura mezcladas

#### Scenario: Hash obsoleto o alcance no aprobado
- **WHEN** una respuesta canónica contiene un hash distinto de los bytes actuales o una ruta fuera del manifiesto
- **THEN** los controles deterministas rechazan el conjunto antes de escribir o publicar sin corregir automáticamente hash o alcance

### Requirement: Cobertura explícita según modalidad de desarrollo
Para general_patch con workflow_version classified-corrections-v1, el harness SHALL declarar operations como lista, coverage como lista con exactamente una entrada por ruta del manifiesto aprobado y notes como texto opcional acotado. SHALL explicar applied como una operación propuesta pendiente de aplicación y pruebas; already_conformant como ausencia de edición con hash de evidencia vigente; y blocked como impedimento justificado mediante reason. SHALL distinguir coverage.sha256 de expected_sha256 y mantener la evidencia de borrado ya realizado conforme al contrato vigente. SHALL permitir operations vacío solo con cobertura completa verificable y no SHALL convertir ese caso en pruebas superadas. Para históricos sin esa modalidad SHALL conservar operations y notes sin imponer coverage nueva; silver_safe_ratio SHALL recibir su contrato expression y notes sin operaciones generales.

#### Scenario: Operación propuesta no es prueba superada
- **WHEN** una entrada declara applied
- **THEN** debe corresponder a una operación propuesta sobre esa ruta y no acredita ejecución, conformidad semántica ni éxito de pruebas

#### Scenario: Archivo conforme sin edición
- **WHEN** una ruta declara already_conformant sin operación
- **THEN** requiere sha256 de la evidencia vigente y la aceptación continúa a las pruebas y verificación obligatorias

#### Scenario: Borrado ya conforme
- **WHEN** una ruta aprobada para delete ya está ausente y declara already_conformant
- **THEN** el contrato exige el hash de sus bytes de base exactos conforme a los controles vigentes y no permite inventar un hash del archivo ausente

#### Scenario: Cobertura incompleta o bloqueo
- **WHEN** faltan rutas, hay duplicados, applied no coincide con operaciones o blocked carece de motivo
- **THEN** se rechaza la cobertura antes de aplicar archivos; un bloqueo justificado conserva el tratamiento de fallo vigente sin ampliar permisos

#### Scenario: Contratos históricos y estrategia acotada
- **WHEN** se invoca developer de un histórico sin la modalidad clasificada o de silver_safe_ratio
- **THEN** el prompt declara el contrato de esa modalidad sin exigir coverage ni mezclar expression con operaciones generales

### Requirement: Diagnóstico seguro de contrato de operaciones
Los nuevos rechazos de formato de operaciones SHALL identificar de manera acotada el índice de entrada y el campo o regla infringida, con categoría invalid_contract, antes de cualquier escritura. SHALL mencionar nombres canónicos conocidos y representar campos desconocidos mediante etiquetas seguras o referencia genérica, sin incluir sus valores, contenido del archivo, rutas arbitrarias ni secretos. SHALL conservar respuesta original, aceptación rechazada, identificadores, hashes y uso/costo en la evidencia protegida conforme al almacenamiento vigente, en ambas modalidades del gestor. No SHALL renombrar aliases, suprimir campos ni realizar llamadas automáticas de reparación. Las denegaciones de política y los fallos de hash SHALL conservar su clasificación y controles vigentes; registros históricos SHALL mantener sus mensajes y retryable originales.

#### Scenario: Alias observado en la ejecución fallida
- **WHEN** operations[0] de modify incluye base_sha256 y omite expected_sha256
- **THEN** el diagnóstico identifica operations[0], base_sha256 como campo no admitido y expected_sha256 como obligatorio, conserva invalid_contract y la respuesta rechazada sin escritura ni llamada correctora

#### Scenario: Campo desconocido contiene información sensible
- **WHEN** un campo o valor arbitrario podría contener texto sensible o caracteres de control
- **THEN** el mensaje público usa una referencia segura acotada sin reflejar ese texto y el original queda solo en la evidencia protegida

#### Scenario: Rechazo con gestor deshabilitado
- **WHEN** una salida inválida se recibe sin gestor de contexto
- **THEN** se registra aceptación rechazada y el mismo diagnóstico seguro que con el gestor habilitado, sin devolver un estado de éxito por haberse interpretado el JSON

#### Scenario: Histórico consultado o reinicio
- **WHEN** se consulta un fallo histórico o se reinicia la App tras un rechazo
- **THEN** no se reescriben mensajes ni retryable históricos ni se inicia una llamada de reparación; cualquier continuación conserva el reintento humano y sus controles vigentes
