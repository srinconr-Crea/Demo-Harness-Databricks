# Spec Delta

## ADDED Requirements

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
