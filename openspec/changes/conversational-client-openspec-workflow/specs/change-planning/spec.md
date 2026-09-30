# Spec Delta

## MODIFIED Requirements

### Requirement: Inicialización previa en el repositorio cliente
El harness SHALL exigir que OpenSpec ya esté inicializado y versionado en la rama base del repositorio cliente antes de procesar una HU. SHALL cargar su configuración y specs desde el checkout del intento sin ejecutar una nueva inicialización.

#### Scenario: Cliente sin OpenSpec
- **WHEN** la rama base no contiene una raíz y configuración OpenSpec válidas
- **THEN** el harness detiene la HU y señala la preparación única pendiente

#### Scenario: Cliente con OpenSpec
- **WHEN** el checkout contiene configuración y specs OpenSpec válidos
- **THEN** el harness los conserva y prepara un cambio nuevo en esa raíz

#### Scenario: Configuración ilegible
- **WHEN** la configuración OpenSpec de la base no se puede cargar o viola la política del perfil
- **THEN** el desarrollador no se invoca y no se publica código cliente

#### Scenario: Inicialización fallida
- **WHEN** el PR de preparación de OpenSpec no se completó o su configuración no está en la rama base
- **THEN** el harness bloquea la HU hasta que la preparación sea válida y esté integrada

### Requirement: Modelo del planner
El harness SHALL usar `databricks-claude-sonnet-5` para las llamadas que generan o actualizan artefactos OpenSpec y SHALL impedir que la historia o el repositorio cliente cambien esa selección.

#### Scenario: Generación del plan
- **WHEN** el planner genera o actualiza un artefacto OpenSpec
- **THEN** la llamada se envía al endpoint `databricks-claude-sonnet-5`

### Requirement: Cambio de planificación por intento
El harness SHALL generar un cambio OpenSpec separado por intento, con propuesta, especificaciones delta, diseño y tareas aplicables a la HU y al contexto autorizado del checkout. SHALL conservar versiones sucesivas durante revisión y corrección sin confundirlas con reintentos.

#### Scenario: Historia admitida
- **WHEN** `explore` obtiene información suficiente para planificar una HU admitida por el perfil
- **THEN** `propose` produce los artefactos requeridos para ese intento

#### Scenario: Reintento
- **WHEN** una historia fallida se reintenta
- **THEN** el nuevo cambio tiene identidad propia y conserva trazabilidad hacia el intento anterior

#### Scenario: Actualización solicitada
- **WHEN** la persona solicita cambios sobre los artefactos
- **THEN** `update` conserva una versión nueva y se vuelven a comprobar sus dependencias y validez

### Requirement: Validación previa a la edición
El harness SHALL exigir validación estructural estricta de OpenSpec y comprobación determinista de que los archivos y acciones previstos permanecen dentro del perfil. El contenido narrativo de los artefactos no SHALL conferir autoridad para editar, probar ni publicar rutas adicionales.

#### Scenario: Artefactos válidos y acotados
- **WHEN** OpenSpec valida los artefactos, la política los admite y la persona aprueba su versión
- **THEN** el harness habilita la fase de desarrollo

#### Scenario: Ruta adicional no autorizada
- **WHEN** un artefacto solicita editar una ruta fuera del perfil
- **THEN** el harness rechaza el plan antes de invocar al desarrollador

#### Scenario: Manifiesto que solicita un archivo adicional
- **WHEN** el manifiesto de un artefacto generado señala un archivo no autorizado por el perfil
- **THEN** el harness rechaza el cambio antes de invocar al desarrollador

#### Scenario: Validación estructural fallida
- **WHEN** falta un artefacto requerido o OpenSpec reporta un error
- **THEN** el intento queda pendiente de corrección o falla sin editar ni publicar archivos cliente

### Requirement: Artefactos disponibles para revisión
El harness SHALL conservar cada versión de los artefactos y exponer su contenido, identidad, huellas y resultado de validación junto con el intento para revisión humana.

#### Scenario: Intento planificado
- **WHEN** el planner termina una versión del plan
- **THEN** la App permite recuperar sus artefactos, hashes y validación antes de solicitar aprobación
