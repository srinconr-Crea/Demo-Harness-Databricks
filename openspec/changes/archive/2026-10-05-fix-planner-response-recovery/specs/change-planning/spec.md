# Spec Delta

## ADDED Requirements

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
