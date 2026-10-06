# Design

## Context

Véase proposal.md, Why, para el incidente. Base inspeccionada: `c1208cbae21eba7ecd1a933d70a02bb74fc6b4b6`. El diseño se incluye porque cruza composición de prompts, tipos del editor, validación y trazabilidad.

`conversation.py` declara inicialmente op/path/content/expected_sha256, pero el payload de classified-corrections-v1 reemplaza task por una descripción genérica. `prompts.yaml` tampoco enumera los campos de operaciones. `patch.py` ya define FileOperation y ManifestCoverage con reglas de hash/contenido; validate_manifest_coverage verifica alcance acumulado y evidencia antes de escribir. En `repo_context.py`, contextual_answer valida ambas modalidades, pero la rama sin gestor no marca el rechazo como la rama con gestor. El editor no necesita aceptar nombres alternativos para resolver el incidente.

La reproducción sintética previa rechazó base_sha256 y aceptó expected_sha256 en el validador de salida. Esa aceptación no demostró edición, pruebas ni éxito de la HU. El endpoint de Sonnet 5.5 conserva json_schema=false; el contrato propuesto se transmite como instrucciones confiables, no como garantía del proveedor.

## Goals / Non-Goals

**Goals:**
- Hacer que el modelo reciba el mismo contrato que aplica el validador y que ningún cambio de task lo elimine.
- Mantener cobertura, hash de edición y estado de verificación con significados distintos.
- Mejorar diagnóstico y aceptación registrada sin exponer contenido ni alterar la autoridad del editor.

**Non-Goals:**
- Migrar modelos, habilitar structured output remoto, añadir corrección automática o reinterpretar aliases.
- Cambiar la HU cliente, su manifiesto, perfiles, límites, aprobación, publicación o política de retry.
- Reescribir históricos, reejecutar la HU ni desplegar durante la implementación local sin autorización operativa correspondiente.

## Decisions

### 1. Descriptor canónico derivado de los tipos existentes

Añadir en prompt_contracts.py un constructor de contrato del desarrollador que tome estrategia, modalidad y límites confiables. Derivar campos/tipos y enums desde FileOperation y ManifestCoverage; complementar con reglas condicionales y ejemplos que los propios modelos validan. Compartir reglas de forma con el editor si se necesita extracción, sin duplicar un segundo validador ni cambiar formas ya válidas. Mantener hash ausente/null para create y content ausente/null para delete, compatibles con el modelo actual. Los ejemplos omiten esos campos opcionales.

El descriptor describe operations, notes opcional con su límite actual y coverage solo en la modalidad clasificada. Incluye límites del perfil y límites vigentes de salida, rechazo de extras, path relativo, contenido completo y SHA-256 de bytes actuales. Los hashes de ejemplos son sintéticos y se identifican como ilustrativos: el modelo debe usar la evidencia real de lectura. Las operaciones mostradas se limitan a las admitidas por el perfil; un ejemplo no autoriza un manifiesto nuevo.

Alternativa descartada: añadir únicamente expected_sha256 a task. Corrige esta frase, pero deja otras ramas y futuras sustituciones sin una fuente compartida. Tampoco se hará una refactorización general de contratos de todos los roles.

### 2. Adjuntar el contrato en la frontera común de invocación

En contextual_answer, antes de serializar o llamar a ContextManager.prepare, resolver el perfil confiable y añadir developer_output_contract para developer. Aplicar el mismo punto a payloads de applying/correcting y a cada ronda de retrieval. Componer desde el producto, sin tomar un contrato definido por la HU o contenido cliente. conversation.py conserva task como descripción del trabajo, sin duplicar las formas JSON.

Actualizar el catálogo versionado para referenciar el contrato explícito y sus reglas clave. El payload preparado y sus snapshots/hashes capturan el descriptor cuando el gestor está activo; sin gestor, conservar procedencia de prompt y evidencia de entrada/call existentes. No introducir almacenamiento público del prompt completo. Confirmar que el incremento cabe en los presupuestos configurados, sin reducir contexto obligatorio ni aumentar límites.

Alternativa descartada: depender de response_format. json_schema=false sigue configurado y los controles locales son obligatorios incluso si un proveedor admite schema.

### 3. Cobertura y continuidad compatibles

Para la modalidad clasificada, describir exactamente una entrada por ruta del manifiesto y correspondencia applied/operación. Aclarar que applied significa propuesta, que already_conformant requiere evidencia vigente y que blocked necesita reason. coverage.sha256 no reemplaza expected_sha256: este último siempre protege los bytes actuales de modify/delete. Un delete ya conforme usa evidencia de los bytes de base exactos según la implementación vigente. Un archivo creado durante el intento puede corregirse mediante modify con hash actual si el efecto acumulado continúa siendo la creación aprobada.

Sin workflow_version clasificada, publicar el contrato histórico operations/notes y no exigir coverage. Para silver_safe_ratio, publicar expression/notes sin operaciones generales. No cambiar WORKFLOW_VERSION ni los contratos persistidos de ejecución por una mejora del prompt. Las compatibilidades de procedencia y recuperación vigentes pueden exigir un nuevo intento; no se promete que una ejecución previa continúe automáticamente tras actualizar prompts.

### 4. Diagnóstico de forma seguro y común

Identificar índice, campos canónicos faltantes y regla incumplida antes de FileOperation.model_validate; convertir errores de forma restantes a mensajes acotados que nunca impriman el input de Pydantic. Para el alias conocido base_sha256, informar literalmente el campo rechazado y expected_sha256 requerido. Para claves arbitrarias, usar etiqueta genérica y nunca su valor ni ruta/contenido. Limitar el número de problemas y longitud del diagnóstico.

Envolver de manera común los rechazos finales del desarrollador en ambas modalidades de contextual_answer: marcar acceptance=invalid_contract, conservar la evidencia y emitir ContextResponseError para el formato. No ampliar este tratamiento a denegaciones de rutas, operaciones autorizadas, manifiesto o hashes; esas rutas conservan excepciones, categorías y retry vigentes. No capturar errores de persistencia como defectos recuperables de formato. Históricos ya guardados no se recalculan.

Alternativas descartadas: aceptar base_sha256 como alias o pedir otra llamada correctora. Ocultarían el incumplimiento o consumirían llamadas adicionales sin resolver la omisión del contrato.

### 5. Validación del diseño

Añadir pruebas que capturen messages/payload reales en mocks de la frontera del modelo, cubriendo applying/correcting, gestor on/off y solicitud read_file seguida de salida final. No limitar la comprobación a probar el helper de contrato. Validar ejemplos contra tipos reales y comprobar su rechazo con campos desconocidos, hashes ausentes y combinaciones inválidas.

Usar el incidente como fixture sintético reducido, sin copiar código ni datos cliente: base_sha256 debe fallar sin escrituras/publicación/llamadas correctoras y expected_sha256 debe pasar a controles de hash/manifiesto. El recorrido positivo continúa por pruebas y Sonnet simulados con runner sintético; el resultado se documenta como local, no como HU remota. Verificar acceptance y evidencia para ambas modalidades, errores de almacenamiento, continuidad histórica y el tratamiento original de denegaciones.

## Risks / Trade-offs

- El descriptor añade tokens de entrada → medir crecimiento y verificar presupuestos actuales; no aumentar reservas ni añadir llamadas. La reducción de fallos es un objetivo, no ahorro garantizado.
- Schema y ejemplos podrían divergir de los validadores → derivar estructura de los tipos y ejecutar pruebas de ejemplos y reglas condicionales.
- Mejorar errores podría cambiar retry para casos no relacionados → aislar fallos de forma y comprobar clasificación/retry de política, hash y almacenamiento.
- Datos del modelo podrían filtrarse en un mensaje → usar nombres canónicos o etiquetas genéricas; probar valores y claves sensibles sintéticos.
- Prompts nuevos pueden ser incompatibles con procedencia de intentos activos → comprobar compatibilidad existente y no saltarla para recuperar la HU observada.
- Sonnet puede seguir incumpliendo el contrato explícito → conservar rechazo previo a escritura y reintento humano; esta mejora no garantiza obediencia del modelo.

## Migration Plan

Implementar y verificar localmente contrato/prompts/pruebas sin tocar configuraciones cliente ni recursos externos. Actualizar docs/operacion.md y evidencia local, registrar versión/hash de catálogo y mantener JSON/costos históricos. La suite completa y validación OpenSpec estricta deben pasar antes de publicación del producto.

Un despliegue posterior requiere revisar intentos activos, conservar el paquete completo anterior y seguir el procedimiento de actualización de la App del harness. Verificar después identidad/configuración y un smoke sintético por el mismo endpoint, registrando llamadas y costos reales si se autoriza. No reintentar automáticamente `4684261fbd554fea87185a765dc754f8`. Para rollback restaurar el paquete anterior completo, preservando registros/checkpoints y dejando actuar a los controles de procedencia. Despliegue y smoke remoto no forman parte de la autorización de esta propuesta.
