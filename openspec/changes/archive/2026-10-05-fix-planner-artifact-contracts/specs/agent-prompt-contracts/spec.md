# Spec Delta

## ADDED Requirements

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
