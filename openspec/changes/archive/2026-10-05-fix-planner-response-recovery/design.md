# Design

## Context

Véase proposal.md para la motivación. Investigación local en `Db_Spec_Harness`, SHA `4225017d6f042b71f50b4dd0f8034b3e21f874d5`, con modificaciones previas de documentación/archivado ajenas al cambio. No se verificó de nuevo la ejecución remota reportada.

`openspec.py` fuerza `max_tokens=6000` en las dos rutas de planner. `agents.yaml` indica 12000; `ModelClient.complete` aplica el argumento explícito antes del default. `repo_context.contextual_answer` parsea estrictamente y convierte JSONDecodeError en ContextResponseError, sin recuperación. `models.py` acepta texto no vacío sin examinar finish_reason. `conversation.advance` libera el lease conservando la etapa/checkpoint anterior; `conversation_webapp.background` agrega un error al timeline sin cambiar el estado. La UI y retry dependen de running/queued más el último evento error. `progress.py` ya identifica fallos por eventos de la fase, aunque el estado global siga activo.

La reserva de salida del gestor de contexto ya considera max_tokens cuando está habilitado. Debe aplicar el límite efectivo resuelto, y validar presupuestos también al construir solicitudes sin gestor. Las specs requieren trazabilidad de fallo, pero no definen todavía su representación recuperable ni la reparación sintáctica.

## Goals / Non-Goals

**Goals:** Contratos estrictos con salida amplia, recuperación finita y una fuente persistente coherente del fallo/reintento. Separar éxito HTTP del endpoint de aceptación del contrato.

**Non-Goals:** Reparar semántica del plan, aceptar rutas nuevas, cambiar modelos, garantizar compatibilidad de 64.000 tokens por documentación genérica, reintentar la HU real o desplegar en este trabajo de planificación. La recuperación automática inicial se limita a respuestas finales del planner; errores de contexto y otros roles conservan rechazo explícito.

## Decisions

### 1. Resolver presupuesto por rol y endpoint

Extender la configuración de agentes con límites por rol; mantener `max_tokens` como fallback para configuración histórica. Planner propone 64000; los demás roles mantienen inicialmente 12000. Eliminar ambos overrides de 6000. Validar enteros positivos, límites declarados del endpoint y suma entrada/reserva antes de invocar; no reducir silenciosamente ni truncar instrucciones. Registrar límite solicitado y efectivo. Una instalación con incompatibilidad debe obtener diagnóstico antes de una llamada costosa y ajustar configuración confiable explícitamente.

El aumento es un techo; no obliga a emitir 64000 tokens. Conservar el logging resumido de 64000 caracteres: no confundir ese recorte con truncamiento del modelo. Los hashes y evidencia protegida de respuesta original/normalizada siguen disponibles con ACL existentes. No aumentar límites de archivo, skill o manifiesto por consecuencia del nuevo techo. Se descarta un límite global elevado para todos los roles por su impacto innecesario en presupuesto.

### 2. JSON por esquema y clasificación previa al parseo

Agregar soporte opcional de response_format en ModelClient con capacidad por endpoint definida en configuración confiable. Para planner, el esquema debe admitir la alternativa exclusiva context_request y el contrato final del artefacto, usando solamente la sintaxis admitida por el proveedor. Si no admite esa unión, generar el esquema simple de la ronda final después del contexto; nunca impedir lecturas necesarias. Soporte sin comprobar permanece deshabilitado; no hacer fallback silencioso después de un error HTTP. El esquema no sustituye validaciones de política, manifest ni OpenSpec.

ModelResponse y AgentCallContract incorporarán campos opcionales de finish_reason, límite efectivo y aceptación/clasificación. Mantener complete/failed para estado de invocación compatible, y un resultado de aceptación separado para la respuesta. Clasificar output_truncated antes de parsear cuando la terminación indica límite; JSON con sintaxis válida pero contrato incorrecto es invalid_contract; JSON no parseable sin señal de corte es malformed_json. Sin finish_reason, registrar ausencia; usage en el techo es evidencia de posible truncamiento, no prueba concluyente. Toda respuesta sospechosa debe superar las mismas validaciones antes de usarse.

Referencia de compatibilidad a verificar durante implementación: [API de Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/foundation-model-apis/api-reference) y [salidas estructuradas Claude](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/model-serving/structured-outputs). La documentación genérica no confirma las capacidades del endpoint concreto `databricks-claude-sonnet-5`.

### 3. Recuperación sintáctica conservadora

Orden: clasificación de terminación, parseo estricto, normalización limitada, como máximo una llamada de corrección, validación determinista del resultado. La normalización reconoce estados de cadena/escape y únicamente escapa CR, LF o tab literales dentro de cadenas cerradas; permite quitar un fence completo como hoy. No cerrar comillas/llaves faltantes, eliminar caracteres, extraer objetos arbitrarios, usar strict=False ni admitir claves duplicadas. Detectar duplicados en el parser original y normalizado.

Una respuesta completa todavía no parseable puede recibir una llamada de corrección del mismo planner con contrato, instrucciones confiables y respuesta original delimitada como dato. Se conserva procedencia y se vinculan parent_call_id/recovery_index. La llamada no habilita herramientas ni rutas y debe devolver el contrato final. No recuperar automáticamente invalid_contract, denegaciones de política, errores de almacenamiento ni output_truncated; estos quedan disponibles para reintento humano. El contador pertenece a la respuesta de artefacto y no se reinicia por rondas; máximo una llamada adicional y sin bucles recursivos. Revalidar JSON, contrato del artefacto, rutas, manifiesto y OpenSpec antes de aprobar el plan. Una normalización sin llamada no genera uso ni costo ficticios.

### 4. Fallo coherente bajo coordinación

Usar state/stage `failed` con metadatos `failure` que identifiquen categoría, failed_stage, revisión, evento/identidad del fallo, checkpoint recuperable y retryable. Distinguirlo de fallos finales no recuperables por metadata explícita. Persistir eventos y snapshot permitido de artefactos parciales dentro del checkout temporal, antes de destruirlo, sin tratarlos como artefactos aprobados. Comprobar identidad/hashes del perfil, skills y contexto al restaurar.

El engine será responsable de finalizar el fallo con el mismo lease y CAS de coordinación que un éxito; el worker solo registrará fallos secundarios que impidan esa persistencia, sin fabricar éxito ni sobrescribir un estado más reciente. Metadata/checkpoint y fila deben coincidir para que get/reinicio reconstruyan el fallo. Fallos de I/O o pérdida de lease preservan el último checkpoint íntegro y bloquean continuación hasta recuperación consistente; no se puede prometer persistencia si el almacén está caído.

Retry del mismo intento transiciona de failed a la etapa de origen únicamente si el fallo es vigente, recuperable, revisión coincide y perfil/contexto/procedencia siguen válidos. Reclamar mediante coordinación una única transición por identidad del fallo; peticiones duplicadas no lanzan múltiples trabajadores. Conservar las aclaraciones, revisión/historial y checkpoints; quitar finished_at activo al retomar y guardar evento de reintento. Reiniciar la etapa puede regenerar artefactos ya producidos; no prometer continuar dentro de una respuesta ni reutilizar aprobación obsoleta. Las reglas vigentes de nuevo intento por cambio de perfil/legado y de idempotencia de PR siguen aplicando.

### 5. Interfaz y compatibilidad

UI y checklist mostrarán fallo en su fase de origen y posteriores pendientes, con Reintentar etapa cuando retryable. No inferir recuperación por el último evento solamente. Lectura de históricos con running/queued más error seguirá disponible y se admitirá el retry histórico mediante las comprobaciones existentes, sin inventar finish_reason ni migrar todos los registros. La representación nueva de fallo y los campos opcionales se cubren con contratos estrictos y round trips; actualizar versión de contrato si lo exige el formato persistido y lectores antes de habilitar escrituras.

## Risks / Trade-offs

- [64.000 tokens no admitidos o alta latencia] -> Verificar capacidades reales de la instalación y timeout con evidencia sintética separada, sin llamadas a recursos cliente. Bloquear configuración incompatible y registrar límites.
- [Reparación altera contenido] -> Normalización con lista cerrada, bytes/hash originales preservados y validación completa; la corrección por modelo puede cambiar el texto y sigue requiriendo revisión humana del plan.
- [Fallo durante persistencia o solicitudes concurrentes] -> CAS/lease, snapshot íntegro, diagnóstico secundario y pruebas de carreras, reinicio y divergencia.
- [Logs largos o costos adicionales] -> Resumen redactado separado de evidencia protegida; usage/costo por cada llamada real, ausente si no reportado.
- [Despliegue revierte lectores nuevos] -> Mantener lectores compatibles antes de activar formato y no sobrescribir históricos.

## Migration Plan

Implementar primero lectores compatibles y tests; configurar defaults y capacidades verificadas por instalación. Ejecutar suite local y smoke sintético autorizado antes de proponer despliegue; sin cambios de bundle previstos. Drenar trabajadores antes de actualizar. Conservar paquete previo y datos/checkpoints; rollback debe usar lectores compatibles con los registros nuevos o deshabilitar nuevas ejecuciones hasta resolver compatibilidad. No activar retry de la HU real como parte del rollout.
