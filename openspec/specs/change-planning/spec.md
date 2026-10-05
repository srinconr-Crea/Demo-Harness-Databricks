# Change Planning Specification

## Purpose

Definir la planificación OpenSpec que convierte cada historia autorizada en artefactos verificables antes de editar código cliente.

## Requirements

### Requirement: Inicialización previa en el repositorio cliente
El harness SHALL exigir que OpenSpec ya esté inicializado y versionado en la rama base del repositorio cliente antes de procesar una HU. SHALL cargar su configuración y specs desde el checkout del intento sin ejecutar una nueva inicialización.

#### Scenario: Cliente sin OpenSpec
- **WHEN** la rama base no contiene una raíz y configuración OpenSpec válidas
- **THEN** el harness detiene la HU y señala la preparación única pendiente

#### Scenario: Cliente con OpenSpec
- **WHEN** el checkout contiene configuración y specs OpenSpec válidos
- **THEN** el harness los conserva y prepara un cambio nuevo en esa raíz

#### Scenario: Inicialización fallida
- **WHEN** el PR de preparación de OpenSpec no se completó o su configuración no está en la rama base
- **THEN** el harness bloquea la HU hasta que la preparación sea válida y esté integrada

#### Scenario: Configuración ilegible
- **WHEN** la configuración OpenSpec de la base no se puede cargar o viola la política del perfil
- **THEN** el desarrollador no se invoca y no se publica código cliente

### Requirement: Modelo del planner
El harness SHALL usar `databricks-claude-sonnet-5-5` para las llamadas que generan o actualizan artefactos OpenSpec. SHALL exigir ese mismo endpoint a explorer, developer y openspec_verifier en la configuración confiable del producto, conservando `databricks-claude-haiku-4-5` como verifier asesor. SHALL impedir que la historia o el repositorio cliente cambien esa selección. La instalación SHALL alinear routing y permiso CAN_QUERY de la App al endpoint nuevo antes de admitir HUs. SHALL conservar los límites actuales de 64.000 tokens del planner y fallback de 12.000 de los otros roles, así como los presupuestos actuales de contexto; una mayor capacidad anunciada no SHALL aumentarlos automáticamente. SHALL declarar soporte JSON Schema y límites del endpoint solo con evidencia específica de compatibilidad y conservar validaciones deterministas posteriores. Una incompatibilidad SHALL bloquear la habilitación sin fallback silencioso a otro modelo.

#### Scenario: Generación del plan
- **WHEN** el planner genera o actualiza un artefacto OpenSpec
- **THEN** la llamada se envía al endpoint `databricks-claude-sonnet-5-5`

#### Scenario: Roles obligatorios y asesor
- **WHEN** la configuración actual del producto se carga para una HU nueva
- **THEN** explorer, planner, developer y openspec_verifier usan Sonnet 5.5 y verifier conserva Haiku 4.5 asesor

#### Scenario: Modelo ajeno o configuración anterior
- **WHEN** la configuración del producto nuevo asigna otro endpoint a uno de los cuatro roles obligatorios
- **THEN** se rechaza explícitamente y no se degrada a un modelo distinto

#### Scenario: Mayor capacidad anunciada
- **WHEN** el endpoint anuncia hasta 128.000 tokens de salida
- **THEN** el producto conserva 64.000 para planner y los límites actuales de otros roles, registrando el límite efectivo por llamada

#### Scenario: Endpoint listo sin compatibilidad comprobada
- **WHEN** el endpoint aparece READY pero no se ha comprobado JSON Schema para esa instalación
- **THEN** no se declara soporte verificado y la activación conserva el contrato textual y sus validaciones o queda bloqueada si no cumple los requisitos de instalación

#### Scenario: Permiso o capacidad insuficiente
- **WHEN** la identidad de la App carece de CAN_QUERY o el endpoint no acepta el presupuesto requerido
- **THEN** la migración no se declara verificada ni admite HUs con la instalación incompleta

#### Scenario: Intento anterior a la migración
- **WHEN** se consulta un intento realizado con Sonnet 5
- **THEN** se conserva el modelo original de sus llamadas y no se atribuye a Sonnet 5.5 ejecución o aprobación histórica

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

#### Scenario: Manifiesto que solicita un archivo adicional
- **WHEN** el manifiesto de un artefacto generado señala un archivo no autorizado por el perfil
- **THEN** el harness rechaza el cambio antes de invocar al desarrollador

#### Scenario: Validación estructural fallida
- **WHEN** falta un artefacto requerido o OpenSpec reporta un error
- **THEN** el intento queda pendiente de corrección o falla sin editar ni publicar archivos cliente

#### Scenario: Ruta adicional no autorizada
- **WHEN** un artefacto solicita editar una ruta fuera del perfil
- **THEN** el harness rechaza el plan antes de invocar al desarrollador

### Requirement: Artefactos disponibles para revisión
El harness SHALL conservar cada versión de los artefactos y exponer su contenido, identidad, huellas y resultado de validación junto con el intento para revisión humana.

#### Scenario: Intento planificado
- **WHEN** el planner termina una versión del plan
- **THEN** la App permite recuperar sus artefactos, hashes y validación antes de solicitar aprobación

### Requirement: Propuesta comprensible y manifiesto aprobado
La propuesta SHALL mostrar objetivo, comportamiento esperado, archivos y operaciones previstos, pruebas requeridas y que su aprobación autoriza crear automáticamente el PR. SHALL distinguir cambios previstos del diff real posterior. El manifiesto SHALL limitar el desarrollo dentro de la política; los comentarios generan nueva revisión y aprobación. Ninguna descripción narrativa SHALL ampliar permisos ni sustituir pruebas del perfil.

#### Scenario: Aprobación informada
- **WHEN** la persona revisa una propuesta válida
- **THEN** ve alcance, pruebas y autorización de publicación antes de aprobar su hash

#### Scenario: Cambio de propuesta
- **WHEN** la persona solicita ajustes
- **THEN** se actualizan artefactos y manifiesto, invalidando aprobación anterior

#### Scenario: Código mostrado antes de apply
- **WHEN** la propuesta incluye ejemplos o cambios de código previstos
- **THEN** se identifican como previstos sin afirmar que son el diff ejecutado

### Requirement: Presupuesto efectivo de salida del planner
El harness SHALL resolver el límite de salida desde configuración confiable por rol y capacidades del endpoint, sin topes ocultos en propose/update o planificación acotada. SHALL reservar ese límite al comprobar el presupuesto de contexto, rechazar incompatibilidades explícitamente y conservar el límite efectivo como evidencia. El default propuesto del planner SHALL ser 64.000 tokens, sujeto a compatibilidad comprobada del endpoint de instalación.

#### Scenario: Respuesta extensa permitida
- **WHEN** una instalación compatible configura planner con 64.000 tokens y el contexto cabe
- **THEN** la solicitud usa ese límite, incluso cuando el artefacto supera los anteriores 6.000 tokens

#### Scenario: Presupuesto incompatible
- **WHEN** el límite excede la capacidad declarada del endpoint o entrada más reserva exceden el presupuesto
- **THEN** se rechaza antes de invocar sin reducir el límite ni truncar instrucciones silenciosamente

#### Scenario: Configuración histórica
- **WHEN** una configuración solo define el límite global válido
- **THEN** se usa como fallback sin añadir un tope fijo de planificación

### Requirement: Clasificación y aceptación de respuestas del planner
El harness SHALL distinguir output_truncated, malformed_json e invalid_contract. SHALL rechazar una respuesta con terminación por límite antes de usarla como artefacto, conservar ausencia de finish_reason en históricos y comprobar JSON, contrato, política y OpenSpec antes de aceptar una planificación. SHALL solicitar salida por esquema únicamente con soporte comprobado en configuración confiable, sin impedir solicitudes de contexto autorizadas.

#### Scenario: JSON incompleto por límite
- **WHEN** el endpoint informa terminación por límite con un JSON sin cerrar
- **THEN** se registra output_truncated y el contenido no se completa ni se acepta como artefacto final

#### Scenario: JSON válido con contrato incorrecto
- **WHEN** la respuesta parsea pero carece de campos obligatorios o excede el manifiesto permitido
- **THEN** se registra invalid_contract y se bloquea planificación sin recuperar permisos mediante otra llamada

#### Scenario: Capacidad de esquema no comprobada
- **WHEN** la instalación no declara soporte verificado para esquemas del endpoint
- **THEN** usa el contrato textual y las mismas validaciones estrictas sin afirmar garantía de salida estructurada

#### Scenario: Solicitud legítima de contexto
- **WHEN** planner necesita una lectura autorizada antes de devolver el artefacto
- **THEN** el modo de esquema permite ese recorrido sin ampliar operaciones o rutas

### Requirement: Recuperación finita de serialización del planner
El harness SHALL permitir normalización conservadora de CR, LF y tab literales dentro de cadenas cerradas de respuestas completas, y como máximo una llamada adicional de corrección por respuesta final de artefacto aún no parseable. SHALL preservar original y normalización por huellas/evidencia protegida, rechazar duplicados y mantener todas las validaciones. SHALL impedir reparación de contenido truncado, contratos inválidos o denegaciones de política; agotada la recuperación SHALL persistir un fallo recuperable por acción humana.

#### Scenario: Saltos de línea literales
- **WHEN** una respuesta completa contiene LF sin escapar dentro de una cadena cerrada y el resto del JSON es válido
- **THEN** se escapa sintácticamente, se conserva el texto decodificado y solo se acepta tras validar el contrato

#### Scenario: Corrección por modelo exitosa
- **WHEN** una respuesta completa sigue siendo no parseable tras la normalización admisible
- **THEN** se permite una llamada de corrección trazable y solo se acepta su contrato final validado

#### Scenario: Corrección agotada
- **WHEN** la llamada adicional vuelve a fallar
- **THEN** se detiene sin nuevas llamadas automáticas y queda evidencia de ambos resultados

#### Scenario: Duplicados o contenido incompleto
- **WHEN** la respuesta contiene claves duplicadas o la reparación exigiría inventar valores o cerrar una cadena incompleta
- **THEN** la normalización no acepta ese contenido ni lo completa artificialmente

### Requirement: Aceptación de Markdown antes de guardar el artefacto
El harness SHALL comprobar la representación y estructura requerida del contenido de cada artefacto conforme a su contrato e instrucciones confiables antes de guardarlo como artefacto aceptado. SHALL rechazar como invalid_contract el contenido doblemente serializado que no cumple esa estructura. SHALL preservar bytes semánticos de contenido válido, sin reemplazos globales de escapes, decodificación adicional arbitraria ni llamadas automáticas de reparación de contratos inválidos. El plan completo SHALL seguir pasando validación OpenSpec estricta y política antes de revisión y apply.

#### Scenario: Documento completo con separadores literales
- **WHEN** una respuesta JSON válida contiene una propuesta con separadores literales de barra invertida seguida de n y no presenta sus secciones requeridas como líneas Markdown reales
- **THEN** se rechaza con diagnóstico de representación del contenido antes de registrar ese artefacto como aceptado

#### Scenario: Documento válido con escapes y Unicode
- **WHEN** un artefacto válido contiene saltos reales, acentos, comillas, rutas y escapes literales legítimos en sus ejemplos
- **THEN** se conserva su contenido sin una segunda decodificación ni modificaciones a los ejemplos

#### Scenario: Error después de un artefacto correcto
- **WHEN** un artefacto previo fue aceptado y el siguiente falla su representación o manifiesto
- **THEN** se conserva el artefacto previo y la evidencia del rechazo, se persiste failed y no se habilita apply ni publicación

#### Scenario: Manifiesto con operación prohibida
- **WHEN** proposal declara código válido junto con una operación OpenSpec o una ruta prohibida por el perfil
- **THEN** se rechaza el manifiesto completo sin filtrar entradas para aparentar éxito ni invocar al desarrollador

#### Scenario: Recorridos de planificación equivalentes
- **WHEN** se ejecuta propose o update con el gestor de contexto habilitado o deshabilitado
- **THEN** se aplican las mismas comprobaciones de representación y política, conservando los contratos propios de cada estrategia
