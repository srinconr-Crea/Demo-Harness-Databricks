# Design

## Context

Véase `proposal.md` para motivación y alcance. En la revisión `8765443801731830786285878b577896c81a853c`, `conversation.py` envía tanto pruebas fallidas como rechazo Sonnet a updating. La igualdad exacta entre operations y manifest produce scope_changed incluso cuando operations está vacío. `patch.py` rechaza listas vacías y no distingue operaciones sobre el checkout de su efecto respecto de la base. `openspec.py` fija specs al nombre del cambio. El contador actual solo cubre rechazos de verify; no cubre los ciclos por scope_changed. `progress.py` no contempla correcting.

La ejecución f9c8efe4b82449b98e0de1ea749c6a0e contiene un verify, pruebas con 25 passed y cuatro scope_changed tras respuestas vacías. Es evidencia del problema anterior, no verificación del comportamiento propuesto. `tests/test_repository_workflow.py` actualmente espera replanificación ante todo rechazo Sonnet y habrá que sustituir esa expectativa por casos clasificados. El gestor de contexto puede estar habilitado o deshabilitado; ambos recorridos deben cumplir el mismo contrato.

El diseño es necesario por afectar autorización, estados persistidos, contratos LLM, pruebas, artefactos y recuperación.

## Goals / Non-Goals

**Goals:** preservar la aprobación por hash del plan mientras cambia el candidato; impedir que una clasificación LLM amplíe permisos; dar al usuario diagnóstico y evidencia suficientes para entender cada transición; resolver el bloqueo real sin reescrituras artificiales.

**Non-Goals:** cambiar modelos, presupuestos de contexto, identidad sandbox, mecanismos de merge/deploy o arquitectura del almacén. Haiku permanece asesor independiente con sus llamadas, fallos no bloqueantes y costos actuales. No se añade un nuevo agente clasificador ni una investigación de métricas Haiku.

## Decisions

### 1. Clasificar con evidencia y decidir con controles deterministas

Añadir resultados tipados para fallos técnicos y hallazgos Sonnet: identificador, categoría propuesta (`implementation`, `scope_spec`, `infrastructure_evidence`, `harness_defect`), criterio afectado, evidencia/ref, rutas/operaciones necesarias y recomendación. Mantener approved boolean estricto. El modelo propone clasificación semántica; el runtime comprueba compatibilidad con plan, perfil, manifiesto y evidencia vigente antes de autorizar correcting. Fallos técnicos reciben códigos de adaptador que distingan error del candidato de fallo del runner; un passed=false sin evidencia suficiente no habilita corrección automática. Contratos inválidos, política y presupuesto conservan rechazo existente.

Los hallazgos informativos no generan reparación por sí mismos. Rechazos ambiguos se detienen con diagnóstico en vez de elegir una ruta permisiva. Hallazgos mixtos se conservan íntegros y scope_spec impide correcciones dependientes. Infraestructura/evidencia admite lectura o recuperación ya autorizada dentro de límites existentes; sin evidencia suficiente termina failed con categoría comprensible y recuperación humana solo si los controles vigentes la permiten. Un defecto del producto termina failed sin planner ni developer cliente.

Alternativas descartadas: otro LLM clasificador agrega costo sin decidir permisos; todos los tests fallidos como implementation confunde errores de ejecución con defectos de código; todo rechazo como update reproduce el ciclo actual.

### 2. Separar plan_revision y candidate_revision

Conservar revision como revisión de plan para compatibilidad de acciones y hashes; añadir candidate_revision y candidate_hash a contratos de intento nuevo. correcting valida la aprobación vigente y los bytes del plan antes de invocar developer, usando la skill apply como instrucciones mediadas con contrato de corrección de tareas aprobadas. No generar una skill cliente nueva ni cambiar el catálogo de siete workflows. Registrar stage=correcting, fase apply y versión de candidato en cada llamada, con prompts confiables específicos para la corrección.

Cada aplicación material incrementa la versión del candidato y elimina elegibilidad de pruebas/aprobación Sonnet anteriores. verifying vuelve a ejecutar adaptadores pertinentes y Sonnet sobre el diff acumulado. Notas y solicitudes de alcance se guardan antes de decidir la transición. La verificación asesora mantiene su posición actual tras Sonnet.

No editar tasks.md aprobado durante correcting: almacenar estados de tareas en evidencia separada vinculada a plan/candidato. Entregar ese estado a Sonnet para distinguir tareas de implementación/pruebas y tareas posteriores de sync/archive/PR. Conservar la finalización determinista existente, comprobando sus precondiciones, sin invalidar artificialmente el plan durante una reparación.

Alternativa descartada: incrementar revision del plan por cada cambio de código invalida la autorización que precisamente permite corregirlo.

### 3. Cobertura explícita y diff acumulado

Extender respuesta developer con cobertura por entrada de manifiesto: operación propuesta, `already_conformant` con hash actual, o `blocked` con motivo/evidencia. No equiparar operations=[] a éxito. El runtime exige cobertura completa y comprueba hashes, política, tipo y estado antes de escribir; las operaciones reales pueden ser un subconjunto. Las rutas omitidas quedan sin conformidad y se diagnostican como cobertura incompleta, no ampliación de alcance.

El manifiesto expresa efecto permitido respecto del SHA base. Un create aprobado permite modificar durante correcting el archivo creado en el intento con hash actual, siempre que siga siendo create en el diff base/candidato; delete de un archivo ya ausente exige evidencia del estado base y candidato. Un archivo de base con modify no puede convertirse en delete, y ninguna cobertura habilita otra ruta. Conservar límites de bytes/archivos sobre candidato acumulado y operaciones de cada lote, validación atómica, rutas seguras y denegaciones existentes. La lista vacía se maneja en orquestación como validación de cobertura; no se pasa al editor esperando escrituras.

Siempre reconstruir changed_code_paths desde el diff acumulado respecto de la base, incluidos archivos creados/eliminados y componentes afectados. Una corrección parcial no elimina del conjunto de pruebas los cambios anteriores.

Alternativa descartada: reemplazar igualdad por inclusión sin cobertura permite omitir trabajo obligatorio; reescribir todos los archivos introduce operaciones ficticias y falla con create ya existente.

### 4. Resolver capacidades antes de escribir delta

Extender la salida tipada de proposal con capacidades nuevas/modificadas y rutas relativas exactas, validadas contra el inventario OpenSpec autorizado. Generar specs por cada capacidad declarada, con su requisito base completo disponible, y comprobar que la narrativa y los destinos coinciden. Mantener el artefacto CLI specs como glob, eligiendo destinos solo bajo el cambio vigente; no autorizar rutas OpenSpec a developer.

Comprobar requisitos MODIFIED contra capacidad y requisitos de base, además de validate --strict. Cubrir varias capacidades, nuevas declaradas y nombres anidados ya existentes sin reinterpretarlos. Si el runtime contradice el destino declarado, reportar harness_defect. En un update, retirar del candidato destinos delta obsoletos de la revisión anterior mediante el gestor de artefactos y conservar su evidencia histórica; no dejar una spec espuria que se sincronice después.

Alternativa descartada: leer rutas desde prosa o usar change_id como capacidad pierde el contrato verificable y permite inconsistencias aunque validate acepte la estructura.

### 5. Contexto compartido con procedencia

Construir un paquete común para apply/correcting/verify/update: contrato aprobado (propuesta, diseño, specs, tareas, manifiesto), notas y bloqueos, lecturas pertinentes con hash y evidencias de pruebas con candidato/plan de validación/identidad runner. Referenciar datos completos protegidos cuando no caben; recuperar por herramientas acotadas, nunca truncar silenciosamente mínimos obligatorios. Verificador obtiene RepoContext con los límites existentes; no obtiene shell ni escrituras. Resolver cobertura de decisiones también sin ContextManager.

Revalidar hashes antes de reutilizar lecturas; separar fuentes actuales, observaciones históricas y afirmaciones del modelo. Las pruebas viejas siguen visibles pero no acreditan bytes nuevos. Un update recibe archivos/operaciones solicitados y motivo real, sin convertir notas vacías en la afirmación genérica de alcance adicional.

El tiempo de retrieval se contabiliza acumulando las operaciones de contexto, incluidas las fallidas y las servidas por caché. La espera de pruebas o del modelo no consume ni renueva ese presupuesto; los valores configurados de tiempo, lecturas, rondas y bytes se conservan. Las observaciones transferidas se representan por ruta/hash vigente y origen recuperable para evitar duplicar contenido dentro del prompt.

### 6. Presupuesto y falta de progreso durables

Mantener implementation_correction_count por intento, máximo dos correcciones lógicas. Reservar una corrección con identidad persistente y checkpoint/CAS antes de su invocación, evitando doble consumo de una misma continuación. Reinicio y nueva revisión de plan conservan el contador. Las llamadas técnicas de recuperación de formato ya existentes conservan su contrato propio y no se confunden con corrección de implementación.

Persistir huella de bloqueo construida con códigos de fallo, criterio afectado y rutas/operaciones normalizadas; para repetición semántica usar contrato tipado y comparación conservadora, nunca solo el texto generado. Comparar candidato pertinente, contrato autorizado y evidencia relevante antes/después. Si reaparece el bloqueo sin cambio pertinente, detener antes de otra llamada equivalente de planner/developer. Cambios solo de prosa/hash total del documento, timestamps o IDs no prueban progreso. Los presupuestos de retrieval limitan recuperación de evidencia aun si no hay escritura. La primera ruta sin progreso puede verificar el estado para comprobar la resolución; la recurrencia bloquea otro ciclo.

### 7. Recuperación, interfaz y compatibilidad

Versionar el contrato de workflow por intento, incluidos esquema de clasificaciones y respuestas developer. Extender checkpoints/registro y coordinación existente, sin crear otro almacén. Recuperar correcting solo con plan, perfil, catálogo, candidato y evidencia compatibles; retry humano existente verifica failure_id, autorización, revisión y lease. No habilitar retry automáticamente para todos los nuevos fallos.

Históricos mantienen lectura y modalidad original. Para intentos activos anteriores sin contrato nuevo, conservar el recorrido antiguo compatible o detener con diagnóstico que indique nuevo intento explícito; no migrar aprobaciones silenciosamente. La UI añade correcting, intento de corrección y causa, mostrando verificación pendiente para candidato nuevo sin borrar evidencia anterior. Guardar costos por llamada bajo ACL vigentes y redacción pública actual.

## Risks / Trade-offs

- Clasificación errónea del modelo -> runtime valida alcance y evidencia; ambiguos no publican ni disparan corrección permisiva.
- Detección de progreso demasiado amplia -> comparar cambios pertinentes y agregar pruebas con prosa distinta sin resolución, y reparaciones parciales reales.
- Cobertura ya conforme usada para omitir trabajo -> hashes actuales, diff acumulado, pruebas y Sonnet siguen obligatorios.
- Estados de tareas invalidan plan -> evidencia separada durante corrección y finalización determinista después de verify.
- Prompts más grandes -> referencias protegidas, retrieval acotado y mismo presupuesto; no aumentar modelos/tokens por este cambio.
- Contratos nuevos afectan histórico -> marcador por intento y pruebas de consulta/reanudación compatibles; no reinterpretar el caso observado.

## Migration Plan

Implementar y probar localmente las nuevas rutas y contratos; actualizar documentación, interfaz y specs mediante sync al completar el cambio. Antes de actualizar una instalación, drenar intentos activos o identificar explícitamente cuáles conservan workflow antiguo. La publicación y despliegue del producto se harán por solicitud posterior, conservando paquete previo para rollback. No ejecutar de nuevo la HU real ni tocar recursos cliente para validar este cambio: usar fixtures locales y, si se solicita smoke remoto, recursos demo_harness_* y el Job/warehouse autorizados. Rollback no debe reanudar automáticamente intentos nuevos cuyo estado correcting el runtime anterior no entiende; conservar evidencia y exigir runtime compatible o nuevo intento.
