# Design

## Context

Véase `proposal.md`, sección Why, para la motivación y evidencia del intento. El código examinado corresponde a `71d13dd9dd1e3831e18a7862128be8177737d32a`; los cambios locales de documentación y archivo OpenSpec existentes quedan fuera de este cambio.

`validate_artifact_content` extrae encabezados de segundo nivel fuera de bloques cercados y compara literalmente con la plantilla. El planner recibe dicha plantilla, pero no una lista explícita que prohíba traducir títulos. `SkillCatalog.compose` entrega `MEDIATED_SYSTEM`; `ContextManager.prepare` lo sustituye por el catálogo por rol cuando está activo. La validación posterior al parseo también tiene recorridos diferentes según ese gestor.

`parse_response` distingue truncamiento, duplicados y JSON mal formado. La normalización y corrección de serialización existen solo para respuestas finales completas del planner que comienzan y terminan como objeto. Un prefijo XML impide ese reconocimiento. `ConversationEngine` persiste recuperabilidad según tipos de excepción: un `ValueError` ordinario de Markdown queda no recuperable, mientras `ContextResponseError` habilita retry. El retry existente restaura checkpoint y usa coordinación; los endpoints autorizan identidad y la interfaz muestra el control cuando failure.retryable lo permite.

Las specs actuales prohíben reparar contratos inválidos y solicitudes de contexto. La delta amplía exclusivamente la elegibilidad de serialización final con texto externo; los defectos de Markdown continúan sin reparación automática. JSON Schema permanece deshabilitado según configuración confiable de la instalación.

## Goals / Non-Goals

**Goals:**
- Compartir la extracción de estructura entre prompt y validador para evitar divergencias.
- Distinguir formato recuperable de política/configuración sin ensanchar genéricamente las excepciones recuperables.
- Tener los mismos gates para corrección y diagnóstico en ambos recorridos del gestor de contexto.
- Reutilizar evidencia y controles de retry existentes, conservando históricos.

**Non-Goals:**
- Añadir un rol, endpoint o mecanismo de aprobación.
- Traducir encabezados recibidos o recortar texto externo para aceptar directamente una respuesta.
- Incorporar infraestructura, dependencias o migraciones de registros.

## Decisions

### 1. Contrato estructural derivado de la plantilla

Centralizar en `prompt_contracts.py` la extracción de encabezados requeridos usando las mismas reglas de Markdown que la validación actual. `openspec.py` incluirá esa lista y la obligación explícita de conservarla en el payload de cada artefacto. Specs y tasks conservarán sus formas propias; no se inventará una lista de títulos de proposal para todos. Reforzar la instrucción en `config/defaults/prompts.yaml` y el recorrido mediado de `skills.py`, sin precargar documentos adicionales ni truncar instrucciones para hacerlas caber.

El contenido seguirá en español. Elegimos exigir estructura canónica sobre aceptar alias traducidos: mantiene la plantilla CLI como referencia y evita una tabla de equivalencias dependiente de idioma. La extracción de títulos no puede conferir autoridad a contenido cliente. Actualizar versión/hash de prompts afectados y aplicar las comprobaciones de compatibilidad de procedencia existentes.

### 2. Error específico de presentación

Introducir un tipo de error de presentación, separado de errores del manifiesto y de configuración. Llevará categoría `invalid_contract`, artefacto y motivo seguro; faltantes calculados desde la plantilla, ordenados y limitados por tamaño. Aplicar la redacción existente a títulos antes de exponerlos, sin copiar títulos arbitrarios del modelo. Si el detalle no puede exponerse, mantener motivo genérico y referencia protegida.

`conversation.py` reconocerá explícitamente ese tipo como recuperable. Los recorridos de `context_manager.py`, `repo_context.py` y el decorador de planificación preservarán la clasificación en lugar de perderla al envolverla en otra excepción. Validar contrato y política antes de clasificar una respuesta completa como defecto recuperable de presentación, de forma que un manifiesto prohibido combinado con un título ausente mantenga el rechazo de política.

No convertir todo `ValueError` en recuperable. `context_manager` activo/inactivo debe producir la misma categoría y elegibilidad. Los eventos existentes transportarán el diagnóstico; no se necesita un contrato de persistencia nuevo ni cambio de UI si la interfaz actual muestra correctamente el mensaje y retry.

### 3. Corrección de texto externo con evidencia de elegibilidad

Extender `repo_context.py` con análisis léxico acotado por los límites actuales de respuesta. Respetar cadenas, escapes y anidamiento; encontrar un único objeto completo de nivel superior y rechazar múltiples candidatos, cierres incompletos o ambigüedad. No usar una expresión regular para elegir el primer bloque ni permitir crecimiento sin límite. Ante dudas, fallar sin llamada adicional.

Para la nueva ruta, parsear el candidato con rechazo de claves duplicadas solamente para demostrar elegibilidad. Exigir rol planner, artefacto final conocido, ausencia de context_request, terminación no truncada y validez del contrato, Markdown y política. Este chequeo debe funcionar también sin ContextManager; reutilizar gates propios de cada estrategia, evitando imponer campos de general_patch a silver_safe_ratio. No guardar el candidato como artefacto aceptado ni efectuar lecturas.

Invocar como máximo una corrección de serialización con el prompt y presupuestos vigentes. El texto externo y la respuesta original son datos, no instrucciones. Solicitar solo eliminación del texto ajeno, conservar todos los valores y mantener parent_call_id/recovery_index y procedencia. Parsear la corrección sin recuperación recursiva, exigir un contrato final sin contexto, comparar el valor JSON con el candidato comprobado y ejecutar nuevamente todos los gates. La comparación será sensible a tipos JSON, sin tratar booleanos como números equivalentes. Solo el resultado validado podrá continuar a artefactos y validación CLI del plan.

La ruta existente para coma final o controles literales conserva su alcance y pruebas; el tope es una corrección total por respuesta, compartido entre rutas. No se amplía la recuperación del explorador ni se corrigen encabezados con el modelo. Las solicitudes de contexto con prefijo XML se mantienen como malformed_json recuperable por acción humana.

### 4. Persistencia, costos e históricos

Usar `ModelResponse`, `AgentCallContract` y snapshots actuales: llamada original malformed_json, corrección con call_id propio, parent_call_id y recovery_index=1, usage y costo propios si existen. La aceptación de la corrección solo se confirma tras los gates; no reemplazar la aceptación original. Si la invocación correctora falla, preservar ambas evidencias disponibles y el último checkpoint. La normalización local mantiene hashes sin llamadas ficticias.

El fallo de presentación conserva failed, etapa original, revisión y failure_id. Retry exige identidad autorizada en la frontera HTTP y controles de revisión, perfil, procedencia, checkpoint y CAS existentes. Un plan regenerado requiere aprobación vigente; alcanzar planning no autoriza apply por sí solo. Histórico `9f4d553d17ea406ca596600875735656` conserva retryable=false, sin migración automática ni reejecución.

## Risks / Trade-offs

- Una respuesta ambigua puede ser recuperable para una persona pero no para el detector. Mitigación: rechazo conservador y retry humano disponible; no prometer recuperación universal.
- Una corrección añade latencia y costo. Mitigación: una sola llamada, mismos presupuestos, uso propio registrado y sin llamadas para políticas o contexto.
- Un texto externo puede contener instrucciones. Mitigación: no otorgarle autoridad y exigir igualdad del objeto final validado.
- Cambiar prompts puede impedir continuar intentos con procedencia incompatible. Mitigación: conservar el bloqueo vigente, explicar la incompatibilidad y usar una HU nueva cuando corresponda.
- Un encabezado correcto no prueba calidad del plan. Mitigación: mantener validación CLI estricta, manifiesto, aprobación humana y pruebas obligatorias.

## Migration Plan

1. Implementar y comprobar fixtures sintéticos de ambos recorridos, estrategias, retry y persistencia; ejecutar suite completa y validación OpenSpec estricta.
2. Actualizar documentación operativa y revisar versión/hash de prompts; conservar paquete anterior para rollback.
3. La activación operativa será una acción posterior explícita, tras revisar intentos activos y compatibilidad. Realizar smoke en la App del harness con una HU sintética nueva y medir evidencia real antes de atribuir éxito remoto.
4. Rollback mediante paquete anterior. No reescribir fallos o aprobaciones persistidos ni repetir publicaciones confirmadas. Ningún paso requiere tocar recursos NaturaPet.
