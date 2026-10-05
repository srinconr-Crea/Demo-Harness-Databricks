# Design

## Context

Ver `proposal.md` para la motivación. La base inspeccionada es `3938ac1c870171baef68dd3fb8d9d47c92e919c9` en `Db_Spec_Harness`; los cambios locales previos de preparación del cliente quedan fuera de este cambio.

El intento observado `bba782f8eb4b419d8240647006db0af5` terminó a las 19:15:04 UTC del 5 de octubre de 2026 con invalid_contract. La llamada `7f2e3136c657494f9fe054d5776a316d` usó 64000 tokens de presupuesto y finish_reason stop. Su manifiesto contiene dos operaciones de código/pruebas y una tercera sobre `openspec/changes/.../specs/bronze-ingestion/spec.md`. El rechazo fue correcto. Su content tiene 30 secuencias literales de barra invertida seguida de n y ningún LF real. La respuesta original está referenciada por `response_evidence_sha256`; las copias de diagnóstico en `.deployments/` son locales, no fuentes de instrucciones ni material que deba copiarse sin redacción a pruebas versionadas.

`config/defaults/prompts.yaml` pide content Markdown y manifiesto dentro del perfil, pero no explica expresamente la separación OpenSpec/código ni la serialización única. `propose_client_change()` presenta los campos summary/manifest en todos los prompts y valida el manifiesto de proposal con `profile.allows_code()`. `prompt_contracts.validate_output()` duplica parte de esa validación cuando interviene el gestor de contexto. `repo_context.planner_response_format()` usa un envelope opcional común para permitir rondas de contexto. La existencia de un schema JSON no garantiza semántica del manifiesto ni estructura Markdown.

El recorrido actual guarda cada artefacto y valida el plan completo al final. La recuperación de JSON mal formado está acotada y los contratos inválidos no se reparan automáticamente. Las specs vigentes conservan esa frontera; esta propuesta añade comprobaciones y claridad, no cambia la autorización de una HU.

## Goals / Non-Goals

**Goals:** Evitar la ambigüedad entre artefactos y operaciones de código; rechazar representación defectuosa antes del guardado aceptado; mantener escapes legítimos; producir un diagnóstico específico y equivalente en propose/update con y sin gestor.

**Non-Goals:** Cambiar permisos/perfiles, presupuestos/modelos, routing de capabilities o múltiples archivos delta, contratos del desarrollador, esquema de coordinación, modalidades de publicación o reglas de retry. Tampoco reparar automáticamente una violación de política ni modificar, cancelar o reintentar la HU real durante implementación/verificación. Un despliegue o push posterior requiere la solicitud correspondiente.

## Decisions

### 1. Contrato confiable específico por artefacto y estrategia

Reforzar el contrato versionado en prompts.yaml y la composición de los prompts de openspec.py. Proposal general_patch exige content/summary/manifest; el manifiesto contiene solo código y pruebas que admite el perfil. Declarar expresamente que las rutas de OpenSpec son gestionadas por el harness fuera de ese manifiesto, aun cuando la propuesta las describa en su impacto.

Los demás artefactos reciben sus campos obligatorios propios; silver_safe_ratio conserva strategy/code_path/expression. Si se especializa el schema en repo_context.py, preservar el envelope que admite context_request y no confundir lectura autorizada de una spec con una operación de código. Mantener las validaciones deterministas aunque el endpoint use esquema.

Alternativas descartadas: ampliar allows_code() para OpenSpec o filtrar la tercera entrada después de recibirla. Ambas ocultan un contrato incorrecto y cambian la frontera de edición/aprobación. Cambiar públicamente manifest a otro nombre añadiría una migración innecesaria.

### 2. Validar Markdown después de una sola interpretación JSON

Explicar al modelo que content contiene el documento, no otra cadena serializada: los saltos se escapan una vez en el JSON externo y deben convertirse en separadores reales después del parseo existente. Incluir un ejemplo construido con serialización estándar para que la propia instrucción no reproduzca el doble escape.

Añadir una comprobación compartida antes de escribir cada artefacto. Se comprueban elementos estructurales requeridos para ese artefacto por contrato/instrucciones confiables, como encabezados reales de la propuesta y checkboxes de tareas; no se derivan reglas de la HU ni de la respuesta. Los encabezados dentro de bloques de código o de una única cadena con separadores literales no satisfacen la estructura del documento. La detección no se basa únicamente en encontrar una secuencia literal: un documento correctamente estructurado puede contenerla en ejemplos. Conservar finales LF/CRLF legítimos, comillas, barras y Unicode. La validación estricta CLI del plan completo sigue siendo obligatoria.

El resultado inválido conserva categoría invalid_contract y su evidencia original. No se aplican replace global de barra invertida+n, unicode_escape, json.loads(content) o una llamada adicional para corregir el contrato. Esta decisión mantiene el alcance aprobado de recuperación sintáctica del cambio anterior y evita transformar contenido legítimo. Mejorar prompts reduce el defecto; la comprobación local lo detecta, no garantiza que toda salida de un modelo sea correcta.

### 3. Una política de validación y mensajes específicos en ambas rutas

Compartir el diagnóstico y comprobación del manifiesto entre prompt_contracts.py y openspec.py para evitar diferencias entre gestor habilitado/deshabilitado. Validar tipos/campos, operación, ruta relativa, pertenencia a OpenSpec, política del perfil, extensión, duplicados y límites sin omitir los controles actuales. Primero identificar una entrada OpenSpec permite explicar correctamente el incidente aunque también esté declarada read_only.

El diagnóstico usa artefacto, índice de entrada y motivo estable; añade ruta solo después de validación lexical y redacción vigente. No vuelca el documento ni el perfil en el error público. Mantener el enlace a respuesta protegida, hashes, call_id, attempt_id y revisión ya existentes, sin nuevo almacén, costo ficticio ni modificación de históricos. El engine sigue siendo dueño de failed/checkpoint bajo lease/CAS.

Alternativa descartada: conservar solo «excede la política». Impide distinguir la confusión OpenSpec/código de una operación realmente fuera de alcance y de un problema del Markdown.

## Risks / Trade-offs

- Falsos rechazos de Markdown válido: usar la estructura realmente exigida por el artefacto, excluir bloques de código del reconocimiento de encabezados y probar LF, CRLF, acentos y escapes legítimos. No exigir un formato inventado a partir del texto de la HU.
- Divergencia de contratos: compartir comprobaciones y probar propose/update con ambas modalidades de contexto y silver_safe_ratio.
- Contratos inválidos siguen siendo posibles: fallo explícito y evidencia íntegra; no prometer recuperación automática ni modificar aprobaciones.
- Exposición de una ruta maliciosa: redacción y validación de ruta antes de presentarla; conservar el detalle completo solo en evidencia protegida.
- Fixtures remotos con información cliente: generar una reproducción mínima sintética de la forma del manifiesto y del doble escape; no versionar respuestas/prompt completos.

## Migration Plan

No hay migración de datos, perfil ni acciones API. Versionar el prompt/contrato y conservar sus hashes por llamada; no reasignar procedencia a llamadas anteriores. Verificar localmente antes de cualquier publicación. El cambio anterior de 64000 y schema permanece.

Para un eventual despliegue autorizado, preparar un paquete y comprobar que no hay trabajadores activos; los intentos de contrato inválido no se reactivan en startup. Conservar el paquete previo para rollback y mantener consulta de históricos. La continuidad o creación de otro intento de la HU seguirá los controles existentes y requerirá una acción humana explícita; esta propuesta no agrega una excepción de retry.

## Verification

Crear fixtures para: manifiesto correcto con código/pruebas, entrada OpenSpec mezclada, ruta prohibida/traversal/extensión/duplicado, contenido con doble escape, Markdown válido con secuencias literales en bloques y comillas/Unicode/CRLF. Comprobar salida por artefacto/estrategia y lecturas context_request. Un fixture de conversación debe demostrar que el artefacto rechazado no se escribe como aceptado, se conserva el previo, se persiste failed y no hay developer/PR ni llamada automática extra. Ejecutar la suite local completa y registrar comandos/resultados; no invocar la HU real como prueba.
