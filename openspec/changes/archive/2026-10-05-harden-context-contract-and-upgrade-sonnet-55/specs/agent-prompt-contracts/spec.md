## MODIFIED Requirements

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
