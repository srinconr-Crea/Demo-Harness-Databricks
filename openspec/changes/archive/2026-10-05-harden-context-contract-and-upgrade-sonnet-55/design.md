# Design

## Context

Véase `proposal.md` para motivación. La investigación se realizó en la rama `Db_Spec_Harness`, revisión `fb1a2b8e818533bb4b215898cf79d2fa1c17be43`, conservando cambios locales previos de documentación y archivo OpenSpec. No hay implementación de este cambio.

La llamada `367079dd8d7248da80bfc1c5fdc937f1` del intento `6b22159ccc334a73bc5c055b54544b5b` devolvió una lista con read_file, list_tree con path y search_text con path. Terminó con stop y quedó marcada parsed, pero `contextual_answer` levantó ValueError antes de leer. El fallo persistido es invalid_contract, en exploring, revision 0 y retryable=false; no modificó archivos ni publicó PR. La evidencia protegida tiene SHA-256 `84504a6bb75a20bcd50f16f4c5993ca5bb45cc892e0b2646059a9214cdc6aebe`.

`prompt_contracts.py` ya define TOOLS y validate_request. `RepoContext.request` valida antes de lectura; `contextual_answer` declara solo nombres de herramientas y una frase breve cuando no usa ContextManager. Con gestor, prepare agrega TOOLS. El default de contexto está deshabilitado. `context_request` se busca con get, por lo que null no se distingue de ausencia. Los errores de formato dentro de request se agrupan actualmente con rechazos de política/presupuesto como feedback genérico.

`ModelClient.mark_response` puede actualizar aceptación de una llamada y persistirla mediante on_call sin crear otra llamada. El motor ya permite retry para ContextResponseError, conserva checkpoints y usa failure_id, revisión y CAS/lease; la API y UI existentes exponen la acción. El cambio puede usar esos mecanismos sin migración del esquema de almacenamiento.

`load_model_config` exige literalmente Sonnet 5 a planner, explorer y openspec_verifier; el routing actual también asigna developer a Sonnet 5. Las tarifas se exigen por endpoint. El bundle usa la variable sonnet_endpoint para CAN_QUERY y el ejemplo de entorno apunta a Sonnet 5. El 5 de octubre de 2026, con CREA_DEV, consultas read-only confirmaron Sonnet 5.5 READY y permisos del operador. Su metadata anuncia 1 millón de contexto y hasta 128.000 de salida; no se hicieron invocaciones ni se verificaron permisos de la App, JSON Schema o tarifas para ese modelo.

## Goals / Non-Goals

**Goals:** unificar contrato declarado y validación efectiva, distinguir formato de política y cerrar la brecha entre invocación parseada y aceptación semántica. Migrar los cuatro roles obligatorios de forma coherente y verificable, con costos estimados trazables y recuperación humana de nuevos fallos de formato.

**Non-Goals:** admitir lotes, agregar filtrado path a list_tree/search_text, ampliar límites o modelos a elección de la HU, habilitar el gestor de contexto, modificar históricos, reejecutar la HU real o desplegar recursos cliente. Tampoco se cambia la recuperación automática de serialización del planner ni el contrato de acciones HTTP.

## Decisions

### 1. Un contrato compartido, una operación por turno

Mantener las tres formas vigentes:

```json
{"context_request":{"op":"list_tree"}}
{"context_request":{"op":"read_file","path":"src/common/schema.py"}}
{"context_request":{"op":"search_text","query":"normalize_table_name"}}
```

Son respuestas distintas. La respuesta final no incluye context_request. Publicar desde `prompt_contracts.py` una descripción compartida que incluya formas, tipos, límites de argumentos y ejemplos; usarla en `repo_context.py` y `context_manager.py` sin perder selección/cache/memoria. Los presupuestos de rondas, lecturas, búsquedas, bytes y tiempo siguen provenientes del perfil. Versionar los prompts afectados y conservar sus hashes en la evidencia que ya existe.

Alternativas: solo reforzar la frase en la ruta deshabilitada dejaría duplicación y divergencias; admitir listas exigiría presupuesto por operación, orden y atomicidad de fallos parciales. Ninguna es necesaria para el caso validado. Los schemas existentes del planner deben seguir permitiendo context_request individual o salida final, sin exigir contenido Markdown durante retrieval.

### 2. Separar validación de formato y ejecución autorizada

En `contextual_answer`, comprobar presencia de la clave, exclusividad del envoltorio y objeto antes de tratar una salida como final; ejecutar validate_request antes del bloque que transforma denegaciones operativas en feedback. Para fallos de formato, actualizar mark_response a invalid_contract y levantar ContextResponseError con esa categoría y un mensaje generado por el harness. Cubrir listas, null, escalares, mezcla, op desconocido, campos extra y tipos/tamaños incorrectos. No interpolar rutas, queries ni nombres arbitrarios de campos del modelo en mensajes públicos.

Las rutas denegadas, enlaces, secretos y presupuesto operativo conservan el feedback de rechazo actual, sin lectura y sin reinterpretación para ampliar permisos. Una solicitud inválida no consume una operación efectiva de filesystem ni se ejecuta parcialmente. No generar llamadas adicionales para corregir el contrato ni convertir listas a objetos.

Alternativa descartada: hacer recuperable cualquier ValueError del runtime mezclaría errores de política/configuración con fallos de salida. Usar la excepción de respuesta ya existente delimita el nuevo comportamiento.

### 3. Reutilizar retry y preservar históricos

ContextResponseError permite al motor persistir retryable=true para nuevos fallos de formato. Verificar el flujo hasta checkpoint y coordinación, la visibilidad en la UI y los controles de API; ajustar integraciones solo si la prueba descubre una brecha. Cada retry humano genera llamadas propias y restaura la etapa, pero no implica aprobación del plan. Conservar aclaraciones y artefactos parciales íntegros.

No modificar el JSON ni el checkpoint del run original para cambiar retryable=false. Después de migrar, una persona puede presentar una HU nueva si necesita repetir aquel caso; el nuevo proceso requiere planificación/aprobación propias. Compatibilidad de procedencia sigue gobernando continuaciones y retries, también cuando cambian hashes de prompts o runtime. El reinicio no invoca modelos para fallos persistidos.

### 4. Selección estricta de Sonnet 5.5 y paquete coherente

Actualizar `models.py` y `config/defaults/models.yaml` para exigir los cuatro roles obligatorios en `databricks-claude-sonnet-5-5`, incluyendo developer. Actualizar pruebas de configuración negativa y routing real. Haiku 4.5 permanece asesor. No mantener fallback automático ni una lista de modelos intercambiables: el usuario pidió migrar a este endpoint específico. El rollback requiere el paquete anterior completo, no cargar YAML de Sonnet 5 en el runtime nuevo.

Actualizar `examples/naturapet/environment.yaml` y verificar que el paquete renderizado referencia Sonnet 5.5 en CAN_QUERY. El despliegue operativo modifica solo la instalación del harness. No implica permisos en tablas o recursos cliente. No se cambia la interfaz pública por mostrar detalles técnicos del modelo.

Mantener límites: planner 64.000, fallback 12.000, presupuesto conservador de entrada existente. No asumir json_schema=true copiándolo del endpoint anterior: realizar smoke breve con el endpoint nuevo usando el límite efectivo 64.000 y el schema real del planner, incluyendo contexto individual y contrato final. Si no hay soporte probado, conservar json_schema=false y las validaciones textuales vigentes; si el endpoint no admite el presupuesto requerido, detener activación y reportarlo sin degradación silenciosa.

### 5. Tarifas y evidencia antes de activar

El loader exige tarifas configuradas. Obtener valores específicos de Sonnet 5.5 del calculador Databricks o evidencia del operador para la región de instalación, registrar fuente/fecha, y declararlos estimaciones, no facturación. No renombrar la entrada de Sonnet 5 manteniendo precios como si estuvieran verificados. Si no hay fuente suficiente, mantener bloqueada la activación; pruebas locales pueden usar tarifas sintéticas explícitas. La verificación remota conserva usage real y evita costo cero cuando falta uso.

Guardar evidencia de metadata, request efectiva sin secretos, terminación, límites, esquema, uso y duración. Distinguir prueba del operador de prueba con identidad de la App y smoke funcional sintético. Conservar costos históricos y registrar cada nueva llamada en el almacén protegido actual, sin snapshots públicos de contexto cliente.

## Risks / Trade-offs

- Un prompt explícito reduce ambigüedad pero no garantiza obediencia del modelo: validación previa, rechazo íntegro y regresión del caso real siguen siendo necesarios.
- Separar formato de feedback modifica la recuperación de solicitudes mal formadas: cubrir positivos/negativos en ambos modos y confirmar que política y presupuestos conservan su tratamiento.
- La migración estricta rompe configuración Sonnet 5 en el runtime nuevo: actualizar paquete, tarifas y permisos juntos; preservar paquete previo para rollback.
- READY y permisos del operador no prueban acceso de la App ni JSON Schema: smoke separado de identidad y capacidades antes de habilitar HUs.
- Nuevos hashes pueden impedir continuar intentos anteriores: drenar trabajo antes de migrar, no sustituir procedencia ni heredar aprobaciones.
- Latencia/costo pueden cambiar con el nuevo modelo: medir uso/duración reales y conservar presupuestos actuales; no prometer mejoras por disponibilidad.

## Migration Plan

1. Implementar y probar en el harness con fixtures sintéticos; conservar cambios locales previos. Completar suite y validación OpenSpec. No publicar código cliente.
2. Obtener y documentar tarifas; comprobar endpoint/límite/esquema con CREA_DEV mediante salida sintética breve y registrar evidencia. Si no puede verificarse un requisito, no marcar la migración como completada.
3. Preparar paquete completo con routing y recurso sonnet_endpoint coherentes. Validar bundle dev renderizado estrictamente; si se cambia databricks.yml/resources, esa comprobación es obligatoria antes de publicar. Conservar paquete/configuración/recursos previos para rollback.
4. Antes de despliegue autorizado, drenar HUs y comprobar identidad de App con CAN_QUERY en Sonnet 5.5. Desplegar solo instalación del harness y ejecutar smoke sintético de explore/planificación, rechazo y retry humano; no usar la HU real como smoke ni crear PR en NaturaPet.
5. Registrar por separado evidencia local, validación, endpoint, permisos y despliegue real. Para rollback, detener admisión, drenar trabajadores y restaurar producto, routing, tarifas y recursos previos completos, sin borrar checkpoints ni alterar registros.

## Open Questions

- Tarifas específicas por región: el valor queda por verificar durante implementación con fuente/fecha; su ausencia bloquea activación, sin cambiar contrato ni alcance.
- Compatibilidad efectiva de JSON Schema: la prueba específica decide el flag de capacidades; las validaciones del contrato son obligatorias en ambos casos.
