# Spec Delta

## Purpose

Definir prompts confiables y reproducibles por rol y fase, con restricciones explícitas y contratos de salida validados, sin conceder autoridad a la HU ni al contenido recuperado.

## ADDED Requirements

### Requirement: Prompts versionados por rol y fase
El harness SHALL componer cada system prompt desde una base confiable y un contrato de rol/fase que declare responsabilidad, restricciones, operaciones de contexto y salida requerida. SHALL fijar su versión y hash por intento y registrar ambos por llamada. La HU, memoria, skills cliente y repositorio no SHALL sustituir la base confiable ni elegir modelos.

#### Scenario: Planner en update
- **WHEN** el planner actualiza un artefacto
- **THEN** recibe el contrato de ese artefacto y fase, más la base de restricciones, con procedencia registrada

#### Scenario: Rol o contrato ausente
- **WHEN** no existe una definición compatible para el rol/fase requerido
- **THEN** se bloquea antes de llamar al modelo sin recurrir silenciosamente a un prompt genérico

### Requirement: Salidas validadas según contrato
El harness SHALL validar respuestas finales y solicitudes de contexto mediante esquemas específicos compatibles con los contratos actuales. SHALL distinguir preguntas del explorador, contenido/manifiesto del planner, operaciones del desarrollador y hallazgos del verificador. Las respuestas inválidas no SHALL provocar edición, transición exitosa ni publicación.

#### Scenario: Operación no autorizada
- **WHEN** el desarrollador devuelve shell, rutas adicionales u operaciones fuera del manifiesto
- **THEN** los controles rechazan la operación aunque la salida sea JSON sintácticamente válido

#### Scenario: Exploración incompleta
- **WHEN** el explorador entrega preguntas válidas
- **THEN** se conservan y el flujo espera aclaración usando las acciones públicas existentes

### Requirement: Frontera de autoridad y compatibilidad de roles
Los prompts SHALL identificar contenido recuperado y derivaciones como datos, conservar Sonnet y pruebas obligatorios y Haiku asesor, y no introducir aprobaciones adicionales. Los pasos deterministas SHALL mantener ese carácter y no generar llamadas artificiales para completar un catálogo de prompts.

#### Scenario: Memoria solicita omitir pruebas
- **WHEN** una fuente o resumen contiene instrucciones para saltar validación o cambiar permisos
- **THEN** esa información no modifica política, fases, modelo ni autorizaciones

#### Scenario: Archivo determinista
- **WHEN** sync o archive se resuelven sin modelo
- **THEN** se conserva evidencia de la operación sin llamada ni costo ficticios
