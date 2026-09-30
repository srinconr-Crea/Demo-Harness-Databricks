# Spec Delta

## MODIFIED Requirements

### Requirement: Secuencia de controles
El harness SHALL exigir checkout autorizado, OpenSpec preexistente, plan validado y aprobado por una persona, desarrollo registrado, pruebas pertinentes y verificación Sonnet contra los specs. La aprobación vigente del plan SHALL autorizar publicación automática después de sync y archive, sin aprobación humana adicional del diff. Desarrollador y verificador SHALL usar la misma revisión aprobada; apply SHALL ejecutar tareas aprobadas.

#### Scenario: Todos los controles aprobados
- **WHEN** pasan controles obligatorios y existe autorización vigente del plan
- **THEN** el flujo continúa automáticamente a publicación

#### Scenario: Control rechazado
- **WHEN** un control obligatorio falla o entrega salida inválida
- **THEN** no se publica y se registra corrección o fallo

#### Scenario: Planificación rechazada
- **WHEN** el plan no valida, contradice política o carece de aprobación
- **THEN** no se invoca al desarrollador

#### Scenario: Inicialización rechazada
- **WHEN** la base carece de OpenSpec válido
- **THEN** no se desarrolla ni publica

#### Scenario: Verificación contra la especificación
- **WHEN** el código supera controles de estrategia
- **THEN** Sonnet contrasta diff y pruebas con los specs de la revisión aprobada

### Requirement: Verificación específica y ciclo de corrección
Cada tipo e impacto de cambio SHALL disponer de controles deterministas y pruebas funcionales pertinentes configurados por el operador, además de verificación OpenSpec obligatoria. SHALL seleccionar adaptadores sobre archivos creados, modificados o eliminados y sus componentes afectados. Un descuadre obligatorio SHALL conservarse y permitir corrección trazable con nueva revisión y aprobación del plan, sin aprobar resultados inconclusos ni comandos de la HU.

#### Scenario: Descuadre corregible
- **WHEN** verify encuentra diferencias entre código, specs y pruebas
- **THEN** el intento conserva hallazgos y vuelve a revisión del plan sin publicar

#### Scenario: Prueba no disponible
- **WHEN** una comprobación obligatoria no puede ejecutarse
- **THEN** se informa no verificado y se bloquea publicación

#### Scenario: Configuración con impacto funcional
- **WHEN** un YAML modifica comportamiento de un componente Python
- **THEN** se valida YAML y se ejecuta la suite funcional configurada

#### Scenario: Eliminación
- **WHEN** se elimina un archivo de un componente
- **THEN** se ejecutan las pruebas configuradas de ese componente y se comprueban referencias pertinentes

## ADDED Requirements

### Requirement: Adaptadores pertinentes y aislados
El harness SHALL soportar python_compile, pytest_sandbox, sql_lint, yaml_validate, json_validate, notebook_validate, databricks_bundle_validate, toml_validate, markdown_structure y validación básica de texto. SHALL validar SQL con dialecto Databricks, notebooks según lenguaje y magias, y datos contra esquemas cuando se configuren. Código cliente y herramientas capaces de ejecutar su configuración SHALL operar en el Job con identidad separada, comandos confiables, límites y sin secretos de la App. Validar un bundle no SHALL desplegarlo. Pruebas remotas SHALL usar exclusivamente recursos demo_harness_* y el warehouse sintético autorizado.

#### Scenario: Notebook con magias
- **WHEN** un notebook usa Python, SQL o magias admitidas
- **THEN** se valida su estructura y lenguaje sin compilar indiscriminadamente todas las celdas como Python

#### Scenario: Bundle afectado
- **WHEN** cambian databricks.yml, includes o recursos referenciados
- **THEN** se valida el bundle completo del target autorizado sin deploy

#### Scenario: Sintaxis sin prueba funcional
- **WHEN** un cambio ejecutable compila pero su prueba funcional requerida falta o falla
- **THEN** no se considera suficiente la sintaxis para publicar

### Requirement: Revisión Haiku asesora
La revisión independiente con Haiku 4.5 SHALL ser asesora. Hallazgos, rechazo, timeout, respuesta inválida o indisponibilidad SHALL registrarse sin impedir continuación ni consumir correcciones. SHALL conservar llamadas y uso disponible; la ausencia de revisión no SHALL presentarse como aprobación.

#### Scenario: Recomendaciones
- **WHEN** Haiku rechaza un candidato que pasa controles obligatorios
- **THEN** continúa el flujo y conserva recomendaciones visibles

#### Scenario: Fallo de Haiku
- **WHEN** la llamada falla o devuelve JSON inválido
- **THEN** se registra estado no disponible o error sin bloquear la HU

#### Scenario: Fallo obligatorio con Haiku favorable
- **WHEN** Haiku aprueba pero fallan pruebas o Sonnet
- **THEN** se bloquea publicación
