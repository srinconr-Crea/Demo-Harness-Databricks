# Spec Delta

## MODIFIED Requirements

### Requirement: Recuperación finita de serialización del planner
El harness SHALL permitir normalización conservadora de CR, LF y tab literales dentro de cadenas cerradas de respuestas completas, y como máximo una llamada adicional de corrección por respuesta final de artefacto aún no parseable. SHALL admitir también una respuesta final completa del planner con texto externo al JSON únicamente cuando identifique sin ambigüedad un solo objeto completo, sin claves duplicadas ni solicitudes de contexto, y compruebe que su contenido cumple contrato, estructura de artefacto y política antes de autorizar la corrección. Ese objeto SHALL servir únicamente como evidencia de elegibilidad, nunca como salida aceptada por extracción. La respuesta corregida SHALL contener únicamente el contrato final y, para esta ampliación de texto externo, preservar el valor JSON del objeto comprobado. SHALL preservar original y normalización por huellas/evidencia protegida, rechazar duplicados y mantener todas las validaciones, incluida OpenSpec estricta antes de aprobar el plan. SHALL impedir reparación de contenido truncado, contratos inválidos, solicitudes de contexto o denegaciones de política; agotada la recuperación SHALL persistir un fallo recuperable por acción humana. Si la elegibilidad del texto externo no puede demostrarse, SHALL detenerse sin corrección automática.

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

#### Scenario: Texto externo a una respuesta final válida
- **WHEN** una respuesta no truncada del planner contiene un único objeto JSON completo de artefacto, válido según contrato y política, con texto ajeno antes o después
- **THEN** el objeto no se acepta por extracción; se realiza como máximo una corrección vinculada y se exige que el contrato final corregido preserve su valor JSON y pase nuevamente todas las validaciones

#### Scenario: Corrección cambia contenido o manifiesto
- **WHEN** la corrección de texto externo devuelve un objeto con contenido, resumen o manifiesto diferente del comprobado
- **THEN** se rechaza sin editar, publicar ni realizar otra corrección automática

#### Scenario: Solicitud de contexto con XML externo
- **WHEN** explorer o planner devuelve una solicitud de contexto precedida por XML o texto ajeno al JSON
- **THEN** se registra malformed_json, no se ejecuta ninguna lectura ni corrección automática y el fallo admite reintento humano sujeto a controles vigentes

#### Scenario: Varios objetos o evidencia ambigua
- **WHEN** una respuesta con texto externo contiene varios objetos candidatos o no permite demostrar un único objeto final completo
- **THEN** se rechaza sin elegir uno arbitrariamente ni invocar corrección automática

#### Scenario: Política o estructura inválida dentro del envoltorio
- **WHEN** el objeto identificado contiene una operación prohibida, solicitud de contexto o un artefacto con encabezados requeridos ausentes
- **THEN** se conserva el rechazo correspondiente y no se utiliza una llamada de corrección para modificar el contrato o recuperar permisos
