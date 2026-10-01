## Purpose

Consumir el workflow OpenSpec versionado en cada repositorio cliente con instrucciones reproducibles por fase y límites de ejecución controlados por el Harness.

## ADDED Requirements

### Requirement: Skills del checkout preparado
El harness SHALL consumir las skills OpenSpec requeridas desde `.agents/skills/` del SHA base del cliente, sin copias alternativas en la App ni descargas o regeneración durante una HU. SHALL comprobar archivos regulares UTF-8, nombres permitidos, ubicación dentro del checkout, metadatos compatibles y presupuestos configurados; SHALL rechazar enlaces, traversal, contenido ilegible y skills excedidas sin truncar silenciosamente instrucciones.

#### Scenario: Cliente completo
- **WHEN** la base contiene las skills requeridas compatibles
- **THEN** cada fase usa la skill del checkout y conserva su identidad y huella

#### Scenario: Archivo peligroso o excesivo
- **WHEN** una skill requerida es un enlace, escapa del checkout, no es UTF-8 o supera el presupuesto
- **THEN** la HU se detiene antes de una llamada de fase y registra la causa sin leer rutas externas

#### Scenario: Versión incompatible
- **WHEN** los metadatos de una skill no son compatibles con el CLI y contrato soportados
- **THEN** se solicita mantenimiento humano sin actualizar archivos automáticamente

### Requirement: Instrucciones compuestas por fase
El harness SHALL usar las skills de explore, propose, update, apply, verify, sync y archive según la fase. Para planificación SHALL combinar skill, instruction, template, context, rules y contenido de dependencias indicadas por el CLI. Para apply SHALL consultar instrucciones específicas de aplicación y sus archivos de contexto. SHALL distinguir workflows de agente de comandos CLI reales y validar esquema, raíces, rutas y disponibilidad antes de consumir sus resultados.

#### Scenario: Planificación con dependencias
- **WHEN** se genera o revisa un artefacto
- **THEN** el modelo recibe la skill correspondiente, las instrucciones CLI y las dependencias existentes autorizadas

#### Scenario: Apply bloqueado
- **WHEN** las instrucciones de aplicación indican prerrequisitos ausentes o archivos de contexto fuera del alcance
- **THEN** no se invoca al desarrollador ni se aplican operaciones

#### Scenario: Workflow sin subcomando CLI
- **WHEN** se ejecuta explore, verify o sync
- **THEN** el harness usa la skill y las consultas CLI soportadas sin intentar ejecutar un comando homónimo inexistente

### Requirement: Autoridad del Harness
Las skills, configuración y salidas CLI SHALL orientar el trabajo sin conceder autoridad sobre modelos, rutas, comandos, ejecución ni aprobaciones. El harness SHALL conservar los contratos JSON y las herramientas de lectura acotadas; SHALL validar y aplicar las operaciones propuestas. La estrategia silver_safe_ratio SHALL conservar su editor y prueba SQL, y general_patch SHALL conservar manifiesto aprobado, límites y sandbox separado. Sonnet y pruebas SHALL continuar obligatorios y Haiku SHALL permanecer asesor.

#### Scenario: Skill solicita otra herramienta o modelo
- **WHEN** una instrucción importada solicita shell arbitrario, rutas adicionales, otro modelo o aprobación adicional
- **THEN** esa solicitud no habilita capacidades ni cambia la política o el flujo aprobado

#### Scenario: Edición directa solicitada
- **WHEN** la skill de apply describe modificar archivos
- **THEN** el modelo entrega el contrato permitido y solo el harness aplica operaciones validadas

#### Scenario: Sync y archive
- **WHEN** el candidato pasó pruebas y verificación vigentes
- **THEN** el harness consume las guías de sync y archive, ejecuta la sincronización y archivo controlados y conserva evidencia de ambas operaciones sin delegar publicación o merge
