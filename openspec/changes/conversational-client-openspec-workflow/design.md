# Design

## Context

Véase [proposal.md](proposal.md). Hoy `workflow.run_story` carga solo un notebook y el árbol `openspec/` desde GitHub, ejecuta `openspec init` en un directorio temporal, llama al planner cuatro veces, aplica `silver_safe_ratio`, verifica y crea el PR en una única función. `webapp.py` mantiene una cola de un trabajador y estados finales o activos; `store.py` guarda JSON de intentos, llamadas y vistas redactadas de artefactos en un volumen UC. `index.html` muestra un formulario de siete campos y un resumen por sondeo. `models.yaml` fija Sonnet 5 para planner/desarrollador y Haiku 4.5 para verificador. El volumen actual es un almacén de evidencia; su contenido redactado no puede reconstruir el borrador exacto.

## Goals / Non-Goals

**Goals:**

- Mantener un checkout real del cliente durante cada etapa activa y una versión canónica durable para continuar tras esperas y reinicios.
- Separar etapas, roles, validaciones y dos decisiones humanas con identidad y hashes verificables.
- Aceptar HUs generales bajo un perfil explícito y pruebas adecuadas, conservando `silver_safe_ratio` como estrategia específica.
- Mostrar el progreso por conversación y conservar costos por llamada sin convertir estimaciones en facturación.

**Non-Goals:**

- Ejecutar código cliente arbitrario con las credenciales de la App o aceptar rutas y modelos pedidos por la HU.
- Hacer merge, desplegar el cliente o sustituir la revisión del PR en GitHub.
- Trasladar las specs del cliente al OpenSpec de este repositorio.

## Decisions

### 1. Incorporación del cliente separada de las HUs

Una operación de preparación clona la rama base permitida, ejecuta `openspec init` una vez, completa `openspec/config.yaml` con contexto del cliente y crea un PR `feature/*` solo con la configuración y los archivos iniciales. Una persona integra ese PR. Al admitir cada HU, el harness verifica que el commit base ya incluya una raíz OpenSpec válida y nunca llama de nuevo a `init`. Así se puede distinguir la configuración aprobada de los cambios de una HU. Alternativa descartada: inicializar en cada intento y mezclar esos archivos en el PR de código; contradice la revisión única de configuración solicitada.

### 2. Checkout temporal con puntos de control canónicos

`GitHubAppClient` obtiene el SHA de la base y crea un checkout completo en el disco local de la App, acotado al repositorio del perfil. La credencial de instalación se entrega al transporte Git sin ponerla en URL, argumentos, `.git/config`, prompts o logs. El checkout existe mientras una etapa ejecuta; antes de esperar a una persona o terminar una etapa se guarda en el volumen UC un manifiesto de versión con SHA base, cambio OpenSpec, archivos añadidos/modificados/eliminados, bytes exactos permitidos, permisos relevantes y hashes. El manifiesto se publica al final de cada punto de control; para reanudar se clona el mismo SHA, se restauran los archivos y se verifican las huellas. Los JSON redactados existentes siguen siendo vistas y registros, no fuente canónica. Una falla de restauración impide continuar. Se fijan límites de tamaño, cantidad de archivos y duración del checkout. Alternativa descartada: conservar un `TemporaryDirectory` a través de aprobaciones; el disco de la App no es durable.

### 3. Máquina de estados por intento y ejecución en tramos

El intento guarda `stage`, `revision`, `base_sha`, `checkpoint_id`, secuencia de eventos y `approval` con sujeto, fecha y hash. Etapas propuestas: `exploring`, `awaiting_clarification`, `proposing`, `awaiting_plan_review`, `updating`, `applying`, `verifying`, `preparing_final_diff`, `awaiting_diff_review`, `publishing` y estados finales. El trabajador termina su tramo al llegar a una espera; una respuesta o aprobación autorizada inicia otro tramo. No se mantiene un hilo ocupado mientras la persona revisa. Las acciones usan versión esperada e idempotency key; una decisión atrasada o duplicada no avanza el intento. El registro de publicación conserva rama, commit y PR para reconciliar reinicios sin duplicarlos. Para evitar ejecución simultánea de un mismo intento entre instancias, la implementación debe añadir coordinación duradera con comparación de versión y lease; se usará una tabla Delta aislada del harness para estado de control, manteniendo los JSON actuales como historial y costos. Las transiciones publican primero el checkpoint completo y luego avanzan el estado transaccional. Alternativa descartada: usar solo el mutex de proceso de `webapp.py`, que no protege varios procesos ni reinicios.

### 4. OpenSpec como artefactos y flujos del agente

La App no tratará `explore`, `propose`, `update`, `apply` y `verify` como si todos fueran subcomandos de la CLI. El orquestador obtiene instrucciones del esquema OpenSpec y ejecuta los flujos de agente sobre los archivos del checkout; usa la CLI fijada para crear el cambio, obtener estado/instrucciones, validar, sincronizar y archivar donde corresponda. `explore` produce preguntas o un resumen y puede pausar. `propose` y `update` escriben proposal/specs/design/tasks por versión, pasan `openspec validate --strict` y esperan la aprobación del plan. `apply` entrega las tareas aprobadas al desarrollador, que propone/aplica parches en el checkout por pasos. `verify` comprueba los specs y pruebas; un hallazgo retorna a `update`/`apply`. Se ejecutan `sync` y `archive` en el candidato local antes de generar el diff para aprobación final, de modo que la persona vea exactamente lo que llegará al PR. Se conserva un checkpoint previo para corregir y regenerar el candidato.

### 5. Roles, contratos y enrutamiento de modelos

Los roles siguen siendo llamadas a Foundation Model API desde la misma App, no servicios o identidades independientes. El rol de exploración y el planner que generan, revisan o verifican artefactos OpenSpec usan `databricks-claude-sonnet-5`, según la política del proyecto. `apply` llama al desarrollador, también Sonnet 5, con tareas y versión de plan aprobadas; el verificador independiente conserva Haiku 4.5 para revisar diff y evidencia, sin sustituir pruebas deterministas ni la verificación OpenSpec con Sonnet. `models.py` enruta por rol/etapa desde configuración confiable y registra cada llamada, incluidos errores, tokens y costo estimado cuando hay `usage`. Los contratos de salida pasan de `expression` a mensajes, operaciones de archivo/parches y hallazgos tipados, con límites. El agente no ejecuta shell libre ni elige modelo o ruta autorizada. Alternativa descartada: un único agente que planifica, edita y aprueba su propio resultado; pierde separación de responsabilidades.

### 6. Estrategia de edición general con controles concretos

Se registra `general_patch` como estrategia adicional. El perfil define prefijos editables, extensiones admitidas, operaciones (crear/modificar/eliminar), tamaños, rutas protegidas y adaptadores de validación. Un aplicador de parches comprueba cada operación antes de escribir y después compara el árbol completo con la base; rechaza enlaces que salgan del checkout, rutas ocultas protegidas, archivos binarios no admitidos y cambios no previstos. El conjunto de pruebas se elige desde una lista confiable, no desde instrucciones del repositorio. Las pruebas que ejecutan código del cliente corren en un sandbox aislado sin la clave de GitHub App ni tokens de la App; si el perfil no ofrece comprobaciones suficientes para el tipo de HU, el flujo lo informa como no verificable y no habilita publicación. `silver_safe_ratio` mantiene sus validadores y prueba SQL sintética. La revisión humana del diff añade control, pero no reemplaza estas comprobaciones.

### 7. Contratos y experiencia de la App

El contrato nuevo de HU tiene `hu` y `description`; el ID interno de ejecución se genera aparte para no exigir un tercer campo. Se versiona el registro de ejecución, conservando lectura de v3 y de llamadas históricas. La API expone mensajes y eventos paginados por secuencia, vistas redactadas de artefactos y diff, decisiones con revisión/hash esperado y estados de espera. La interfaz sondea eventos incrementales (aprovechando el sondeo actual) y representa un hilo con etapas, preguntas, archivos, pruebas y costos. Solo permite las acciones válidas para el estado actual. El contenido sin redactar se guarda como borrador privado del intento; las respuestas visibles aplican redacción y controles de acceso. La UI no renderiza HTML ejecutable proveniente de HU, repositorio o modelos.

### 8. Publicación ligada al candidato aprobado

El hash de aprobación final cubre SHA base, lista ordenada de archivos y contenido exacto, incluidos specs sincronizados e historial archivado. Antes de publicar, el harness consulta otra vez la cabeza de la base; si avanzó, invalida la aprobación y regresa a preparación/verificación/revisión. La publicación usa exclusivamente el candidato aprobado, crea una rama `feature/*`, compara el diff remoto completo y crea o reutiliza el PR de manera idempotente. Las comprobaciones de PR se informan con su estado real. La persona aún revisa y hace merge en GitHub.

## Risks / Trade-offs

- [Clonado o pruebas de repositorio no confiable] → limitar tamaño y contenido del checkout; aislar ejecución de pruebas, sin credenciales y con comandos permitidos por perfil.
- [Pausa larga o reinicio] → checkpoint canónico en volumen UC, manifiesto final con hashes, lease y reconciliación antes de reanudar.
- [Aprobación de una revisión obsoleta] → exigir revisión/hash y volver a comprobar base y candidato antes de publicar.
- [Costo y latencia de más llamadas] → registro por etapa y límites configurables de iteraciones, tokens, archivos y tiempo; costo desconocido permanece ausente si falta `usage`.
- [Migración de JSON y UI] → lector compatible para registros v3; nuevas ejecuciones usan esquema nuevo y la App distingue historiales sin aprobaciones.

## Migration Plan

1. Añadir contratos versionados, almacenamiento de checkpoints y coordinación durable sin borrar registros previos.
2. Incorporar checkout, preparación única y validación de OpenSpec en perfiles de prueba; mantener la publicación actual bloqueada para clientes aún no preparados.
3. Introducir estados conversacionales y revisiones, luego `general_patch` con sandbox y pruebas, conservando `silver_safe_ratio` como estrategia registrada.
4. Actualizar `openspec/config.yaml`, perfiles, modelos, App, documentación y pruebas. Validar la suite y el bundle; desplegar en desarrollo y comprobar un cliente sintético preparado antes de habilitar otros perfiles.
5. Ante un fallo de despliegue, volver a la versión previa de la App. Los nuevos borradores quedan conservados para diagnóstico, sin publicarse automáticamente con el ejecutable anterior.
