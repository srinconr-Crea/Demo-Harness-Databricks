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
Las operaciones de contexto autorizadas SHALL declarar argumentos, tipos, campos permitidos, tamaños, respuestas, errores y truncamientos junto a su contrato. SHALL validar antes de lectura y conservar acceso según perfil. SHALL limitarse a list_tree/search_text/read_file cuando el rol/fase tiene retrieval habilitado; skills no SHALL habilitar shell ni tools adicionales.

#### Scenario: Lectura válida
- **WHEN** read_file recibe ruta relativa autorizada de archivo regular
- **THEN** entrega contenido/hash y estado de truncamiento explícito

#### Scenario: Solicitud inválida
- **WHEN** context_request contiene traversal, campos desconocidos, tipos inválidos u operación no autorizada
- **THEN** se rechaza sin leer rutas externas ni exponer contenido denegado

#### Scenario: Evidencia truncada
- **WHEN** búsqueda o lectura excede límites
- **THEN** informa truncamiento y no afirma haber inspeccionado contenido omitido

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
