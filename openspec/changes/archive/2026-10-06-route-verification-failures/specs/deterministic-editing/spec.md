## MODIFIED Requirements

### Requirement: Validación del resultado
El harness SHALL validar el resultado con controles de su estrategia y comparar el diff real acumulado respecto de la base con archivos y operaciones del manifiesto aprobado, además de la política. Las operaciones generales SHALL ser tipadas, de texto, limitadas y con hash previo para modificación o borrado; SHALL rechazarse conjuntos inválidos antes de aplicar archivos. El candidato SHALL quedar vinculado a la revisión del plan aprobado, su propia versión y evidencia de verificación. El desarrollo SHALL poder proponer un subconjunto de operaciones y declarar cobertura verificable de los archivos ya conformes; una omisión no SHALL conferir conformidad ni una lista vacía SHALL interpretarse por sí sola como ampliación de alcance. La cobertura sin escritura SHALL comprobar bytes/hashes actuales y su correspondencia con el contrato aprobado, seguida de pruebas y Sonnet. Las correcciones de un archivo creado durante el intento SHALL poder modificar sus bytes actuales con hash previo si su efecto acumulado sigue siendo la creación aprobada respecto de la base; esto no SHALL autorizar nuevas operaciones sobre archivos de base ni otras rutas. El conjunto de archivos sujetos a pruebas SHALL conservar todos los cambios acumulados y no reducirse a la última respuesta del developer.

#### Scenario: Edición divergente
- **WHEN** la expresión o resultado silver_safe_ratio difiere de la razón validada
- **THEN** se detiene el flujo sin publicar

#### Scenario: Código general inválido
- **WHEN** el parche viola formato, sintaxis, estructura o límites
- **THEN** se bloquean verify y publicación hasta corregir dentro de la autorización vigente o detener el intento

#### Scenario: Archivo adicional
- **WHEN** el parche admite una ruta por política pero no por el manifiesto aprobado
- **THEN** se solicita revisión del plan antes de editar esa ruta

#### Scenario: Hash previo divergente
- **WHEN** una modificación o eliminación no coincide con los bytes esperados
- **THEN** se rechaza el conjunto sin aplicar parcialmente operaciones

#### Scenario: Archivos ya conformes
- **WHEN** developer devuelve operaciones vacías y cobertura vigente de todos los archivos previstos
- **THEN** el harness valida cobertura y diff acumulado y pasa a verify sin scope_changed ni reescrituras artificiales

#### Scenario: Omisión sin cobertura
- **WHEN** developer no propone operaciones ni explica con evidencia vigente un archivo requerido
- **THEN** el harness rechaza la cobertura incompleta sin declarar el alcance ampliado o el candidato verificado

#### Scenario: Corrección parcial
- **WHEN** la reparación afecta solo uno de los dos archivos del manifiesto
- **THEN** valida esa operación y la cobertura restante, mantiene ambos cambios acumulados y ejecuta las pruebas pertinentes

#### Scenario: Archivo creado en el intento
- **WHEN** el manifiesto aprobó crear un test ausente en la base y correcting modifica ese test ya creado
- **THEN** exige hash actual y política, conserva creación como efecto respecto de la base y no requiere cambiar el manifiesto a modify

#### Scenario: Operación acumulada distinta
- **WHEN** el manifiesto autorizó modificar un archivo de base y developer propone eliminarlo
- **THEN** no aplica la operación y solicita aprobación del cambio real de alcance
