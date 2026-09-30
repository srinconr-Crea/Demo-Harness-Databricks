# Design

## Context

Ver proposal.md para motivación. `ClientProfile` y `GeneralPatchPolicy` duplican prefijos; `patch.py`, `sandbox.py`, snapshots y publicación consumen esas restricciones. `_source_summary()` selecciona extractos por orden de archivos hasta 16.000 caracteres. El prompt developer aún corresponde al piloto. El runner del Job ejecuta pytest con objetivos confiables; SQL, TOML y TXT no tienen validación general actual. Notebooks se compilan como Python sin distinguir lenguaje o magias. Haiku y Sonnet comparten el gate de corrección. La interfaz muestra eventos y artefactos y espera `awaiting_diff_review`.

El cambio es transversal y afecta autorización, contratos durables y ejecución de código cliente. Las specs actuales y AGENTS.md exigen aprobación final del diff: el usuario decidió explícitamente sustituirla por publicación automática autorizada al aprobar la propuesta; actualizar esa documentación durante apply, no interpretar su texto anterior como el comportamiento nuevo.

## Goals / Non-Goals

**Goals:** centralizar permisos, vincular cada candidato al manifiesto aprobado y conservar recuperación e idempotencia al eliminar la espera final. Habilitar pruebas adecuadas antes de activar edición amplia.

**Non-Goals:** ejecución de comandos elegidos por el modelo, despliegue cliente, merge, parada automática, pruebas contra NaturaPet, nueva base analítica o reescritura del scaffold.

## Decisions

### 1. Política compartida de lectura y escritura

Agregar política con `scope: prefixes|repository`, `read_only_paths` y `denied_paths`; mantener prefijos heredados cuando no haya política nueva. GeneralPatchPolicy conserva extensiones, operaciones, límites y pruebas. Una única resolución normaliza rutas relativas por segmentos y aplica precedencia: prohibido > solo lectura > editable. Bloquear nombres protegidos exactos y descendientes, enlaces, traversal, rutas de unidad y escapes; no usar coincidencias textuales que confundan `src` con `src-other`. Soportar archivos raíz. `.github/`, OpenSpec y archivos de instrucciones son solo lectura del developer; `.git/` y rutas de secretos quedan fuera del contexto. El workflow tiene autoridad separada para escribir el prefijo OpenSpec.

Usar esa resolución en contexto, parche, validación, snapshots, restauración y publicación. El ZIP del sandbox necesita archivos de dependencias y pruebas incluso si son solo lectura; filtrar rutas prohibidas y validar integridad, sin convertir lectura en permiso de edición. Alternativa descartada: cambiar solo allowed_paths, porque deja controles contradictorios.

### 2. Contexto mediante solicitudes tipadas

Crear RepoContext con list_tree, search_text y read_file. Ofrecer solicitudes JSON acotadas a explorer, planner y developer; sin shell ni ejecución. Cada respuesta incluye rutas, hashes, contenido limitado y señal de truncamiento. Presupuestos configurables iniciales propuestos: 10 búsquedas, 20 lecturas, 200 KB de contenido total y 20 rondas por etapa; el perfil puede fijar menos. Registrar rondas, tokens y costos por llamada. No enviar archivos secretos ni contenido sin presupuesto. Preferir lectura dirigida a aumentar indiscriminadamente el extracto global. `find_symbol` no es necesario en esta entrega.

Separar developer general (operaciones tipadas y notas) de ratio (expresión exacta). Entregar todos los specs delta de la revisión, no solo Markdown raíz; incluir contexto relevante y manifiesto aprobado.

### 3. Plan estructurado como autorización

Además de artefactos, guardar resumen, archivos/operaciones previstos y matriz de pruebas seleccionada por política. La huella del plan incluye manifiesto y artefactos junto al SHA base; invalidar aprobación ante modificación. Mostrar ejemplos de código como previstos, sin prometer un diff antes de apply. Verificar operaciones contra el manifiesto y contra perfil antes de editar.

Explore vuelve a evaluar aclaraciones acumuladas: la implementación actual salta directamente de una respuesta a propose y debe dejar de hacerlo. Correcciones que revisan plan o alcance vuelven a aprobación; no aceptar automáticamente un plan distinto. Mantener límites de corrección existentes para gates obligatorios.

### 4. Adaptadores por extensión e impacto

Introducir registro confiable y reglas de impacto del perfil: rutas/componentes determinan suites, esquemas y targets de bundle; la HU no aporta comandos. Emitir plan de validación con adaptador, motivo, objetivos y resultado. Python exige sintaxis y pytest; SQL exige parser/lint Databricks y pruebas funcionales sintéticas configuradas cuando transforma datos; notebook valida esquema, lenguaje y magias y pruebas pertinentes; YAML/JSON/TOML parsean y aplican esquemas configurados. MD conserva estructura y TXT valida texto. Cambios de configuración y eliminaciones activan suites de consumidores configuradas.

Bundle validate se activa por databricks.yml y sus includes/recursos, con target confiable y sin deploy. Ejecutar herramientas que cargan configuración ejecutable del cliente en el Job dedicado. Mantener identidad mínima, entorno sin secretos de la App, límites de proceso, salida y paquete. Si validate necesita consultar workspace, usar únicamente la identidad y recursos demo_harness autorizados; nunca credenciales de la App o recursos cliente. Fijar versiones de herramientas y dependencias del runner. Parser/lint no sustituye prueba funcional; tipos sin cobertura requerida bloquean activación/publicación.

### 5. Haiku separado de gates

Persistir advisory con estado, findings, error redactado y referencia de llamada. Limitar tiempo e intentos; capturar únicamente fallos propios de la llamada y su contrato, no errores de almacenamiento, autorización o integridad. Sus hallazgos no alimentan correction_count ni feedback bloqueante. Sonnet y pruebas continúan independientes y obligatorios. Una llamada sin usage conserva costo ausente.

### 6. Publicación automática con candidato exacto

Después de verify, completar tareas, sync y archive; guardar checkpoint y diff finales, hash del candidato y evidencia ligada al plan vigente. Reemplazar la transición a awaiting_diff_review por publishing para ejecuciones nuevas. Registrar autorización de publicación derivada del plan, nunca una aprobación humana del diff. Antes de publicar comprobar plan, política, evidencia, base y bytes. Mantener comprobación del diff remoto completo e idempotencia de rama/PR. Si la base avanza, restaurar checkout nuevo y volver a explorar, proponer y aprobar.

Conservar diff consultable tras preparación y al completar, actualizando los filtros actuales de API. Eventos sync/archive deben corresponder a resultados comprobados, no solo emitirse consecutivamente al retornar archive. Guardar historial y revisión para no atribuir evidencia obsoleta al candidato vigente.

### 7. Interfaz de decisiones y checklist

Hilo principal: preguntas, propuesta comprensible, comentarios y resultado. Detalle expandible: artefactos, diff, eventos técnicos y costos. Preservar borrador por run/revisión y durante polling/update. Checklist derivado de eventos durables, con tiempos UTC convertidos a America/Bogota, estado por revisión y link al PR. Mostrar advisory y checks GitHub por separado; no llamar OK a unavailable, pending ni fases omitidas. Después del PR el usuario decide revisar y detener la App mediante la operación autorizada existente.

## Risks / Trade-offs

- Mayor alcance y costo de contexto → presupuestos configurables, trazabilidad y manifiesto por HU.
- Pruebas pueden pasar sin detectar regresiones → reglas de impacto y suites funcionales mantenidas por operador; mostrar cobertura efectivamente ejecutada.
- Validar notebooks y bundles exige más runtime → dependencias fijadas y fixtures positivas/negativas antes de activar perfiles.
- PR automático elimina revisión previa de bytes → controles deterministas, manifiesto, candidato íntegro y revisión humana en GitHub; no merge.
- Reinicio puede duplicar publicación → reutilizar leases, checkpoints y comparación remota existentes.

## Migration Plan

1. Añadir contratos versionados y lectores históricos. Conservar el comportamiento de perfiles por prefijos y del piloto, sin convertir silenciosamente NaturaPet a general_patch.
2. Conservar intentos existentes con su modalidad de aprobación original, incluidos awaiting_diff_review. Ejecuciones nuevas usan autorización del plan; un registro histórico nunca recibe autorizaciones inventadas.
3. Incorporar adaptadores, dependencias del Job, fixtures generales y validación sintética completa. Habilitar alcance repository únicamente en perfiles explícitos con suites y sandbox operativos.
4. Actualizar documentación, contexto y AGENTS.md con el requisito acordado; validar bundle del harness si cambia el runtime o infraestructura. No desplegar como parte de la planificación.
5. Rollback: impedir nuevos intentos de modalidad nueva y restaurar versión compatible que lea sus registros; preservar checkpoints y PR existentes, sin borrado ni merge. No reanudar intentos nuevos con un binario antiguo que no entienda su autorización.
