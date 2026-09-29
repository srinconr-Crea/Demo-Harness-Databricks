# Change Planning Specification

## Purpose

Definir la planificación OpenSpec que convierte cada historia autorizada en artefactos verificables antes de editar código cliente.

## Requirements

### Requirement: Inicialización previa en el repositorio cliente

El harness SHALL inicializar o cargar OpenSpec en un workspace del repositorio cliente fijado a la rama base antes de invocar al desarrollador, y SHALL incluir los archivos nuevos de inicialización en el cambio publicable del mismo repositorio.

#### Scenario: Cliente sin OpenSpec
- **WHEN** el repositorio cliente no contiene una raíz OpenSpec
- **THEN** el harness la inicializa antes de generar el plan y de invocar al desarrollador

#### Scenario: Cliente con OpenSpec
- **WHEN** el repositorio cliente ya contiene configuración y especificaciones OpenSpec
- **THEN** el harness las carga sin reemplazar el contexto del cliente y prepara un cambio nuevo en esa raíz

#### Scenario: Inicialización fallida
- **WHEN** la inicialización o carga de OpenSpec falla
- **THEN** el desarrollador no se invoca y no se publica código cliente

### Requirement: Modelo del planner

El harness SHALL usar `databricks-claude-sonnet-5` para las llamadas del planner y SHALL impedir que la historia o el repositorio cliente cambien esa selección.

#### Scenario: Generación del plan
- **WHEN** el planner genera un artefacto OpenSpec
- **THEN** la llamada se envía al endpoint `databricks-claude-sonnet-5`

### Requirement: Cambio de planificación por intento

El harness SHALL generar un cambio OpenSpec separado por intento, con propuesta, especificaciones delta, diseño y tareas, a partir de la historia y del contexto autorizado del perfil.

#### Scenario: Historia admitida
- **WHEN** una historia supera el análisis determinista de su estrategia
- **THEN** el planner produce los cuatro tipos de artefacto para ese intento

#### Scenario: Reintento
- **WHEN** una historia fallida se reintenta
- **THEN** el nuevo cambio tiene identidad propia y conserva trazabilidad hacia el intento anterior

### Requirement: Validación previa a la edición

El harness SHALL exigir validación estructural estricta de OpenSpec y comprobación determinista de que el manifiesto de los artefactos coincide con la estrategia, el archivo y la expresión autorizados por el perfil. El contenido narrativo de los artefactos no SHALL conferir autoridad para editar ni publicar rutas adicionales.

#### Scenario: Artefactos válidos y acotados
- **WHEN** OpenSpec valida los artefactos y la política los admite
- **THEN** el harness habilita la fase de desarrollo

#### Scenario: Manifiesto que solicita un archivo adicional
- **WHEN** el manifiesto de un artefacto generado señala una ruta no autorizada
- **THEN** el harness rechaza el cambio antes de invocar al desarrollador

#### Scenario: Validación estructural fallida
- **WHEN** falta un artefacto requerido o OpenSpec reporta un error
- **THEN** el intento falla sin editar ni publicar archivos cliente

### Requirement: Artefactos disponibles para revisión

El harness SHALL conservar los artefactos validados y exponer su identidad y resultado de validación junto con el intento para revisión humana.

#### Scenario: Intento planificado
- **WHEN** el planner termina correctamente
- **THEN** el registro del intento permite recuperar los artefactos y sus hashes
