# Gestión determinista del contexto por HU

La política confiable vive en `src/agents/harness/config/defaults/context.yaml` y el catálogo en `prompts.yaml`. No los configura la HU ni el repositorio cliente. El producto trae `enabled: false`; una instalación puede habilitarlo después de las pruebas. Cada intento nuevo fija hashes de ambos. Un histórico sin metadatos conserva su flujo original. Un intento gestionado con hashes incompatibles exige retry humano y nueva aprobación; consulta y cancelación siguen disponibles.

## Fuentes y contratos

| Rol | Fuentes mínimas de su llamada | Resultado |
|---|---|---|
| explorer | HU original, aclaraciones, preguntas, skill explore completa, contexto OpenSpec y fuentes recuperadas autorizadas | summary y hasta cinco questions |
| planner | HU, decisiones originales, instrucciones del artefacto, dependencias y skill propose/update completa | content; proposal general incluye summary y manifest |
| developer | plan/manifiesto aprobado, skill apply, archivos actuales completos del manifiesto con SHA | operations o expresión silver_safe_ratio |
| openspec_verifier | instrucciones verify, artefactos y evidencia de pruebas obligatorias | approved booleano y findings; obligatorio |
| verifier | evidencia de pruebas y contexto de revisión; sin herramientas de recuperación | approved y findings; asesor |

El system contiene restricciones comunes, rol/fase y salida esperada. La skill se conserva íntegra en el cuerpo de la solicitud. La HU, documentos y respuestas del modelo son datos y no autorizan operaciones. La política de repositorio y la comparación exacta del manifiesto siguen aplicándose antes de editar.

Las herramientas se solicitan con `context_request` y campos exactos:

| Operación | Argumentos | Respuesta |
|---|---|---|
| list_tree | op | paths, truncated |
| search_text | op, query de 1 a 200 caracteres | matches con path/line/text/sha256, truncated |
| read_file | op, path relativa autorizada de hasta 500 caracteres | path, content, sha256, truncated |

Rigen además rondas, lecturas, búsquedas, bytes y timeout del perfil cliente. Traversal, enlaces, binarios y campos extra se rechazan. Un límite devuelve truncated/reason; un rechazo devuelve error. Ninguna respuesta truncada o fallida entra en cache como evidencia completa. Las referencias no sustituyen una lectura necesaria.

## Vigencia, memoria y selección

El gestor conserva el texto humano original, actor, revisión y hash; no genera resúmenes ni inferencias con otro modelo. La extracción estructurada es conservadora: reconoce explícitamente la regla de cero en compras; para otros contenidos conserva el original completo, sin inferir equivalencias semánticas. “Cero permitido en compras” y “cero rechazado en compras” generan conflicto. “Corrijo: cero ahora rechazado en compras” sustituye la regla anterior y conserva sus orígenes. El reconocimiento no constituye un detector universal de contradicciones en lenguaje natural; las discrepancias no estructuradas siguen bajo exploración y aprobación humana.

Una decisión humana no caduca por antigüedad. Una lectura pierde vigencia si cambian sus bytes o permisos. Una nota reciente no sustituye por fecha una decisión vigente. Interpretaciones propuestas no son decisiones confirmadas. El retry conserva mensajes originales, reconstruye decisiones y exige aprobación nueva; nunca reconstruye aprobaciones desde memoria.

Antes de cada llamada se comprueban fuentes del historial contra candidato e inventario actuales. Se recupera una versión cambiada bajo límites del perfil. Se conserva una copia íntegra de duplicados exactos y se registra cada exclusión. Verificación excluye source_summary cuando su contrato no lo consume. Texto humano y skills no se podan. Fuente ausente, conflicto o presupuesto insuficiente bloquean el paso dependiente.

La cache es descartable y aislada por intento, repo, perfil, base, revisión, checkpoint y contenido/inventario. TTL por defecto: 300 segundos; LRU: 100 entradas y 1 MiB. Revalidar hashes sigue leyendo bytes: un hit evita repetir búsqueda/serialización, no garantiza ahorro de I/O ni tokens. Al reiniciar empieza vacía.

El presupuesto cuenta system y cuerpo completos. Defaults: 524288 bytes de prompt, estimación máxima de 524288 tokens de entrada y reserva de 12000 tokens (o salida solicitada mayor). La estimación conservadora usa un token por byte UTF-8; no representa usage real del endpoint. Si mínimos y reserva exceden límites, se bloquea sin truncar ni aumentar presupuesto. No hay compactor ni rol adicional.

## Evidencia, operación y recuperación

Snapshots completos viven en `context/<run_id>/<attempt_id>/<sha256>.json`, con las ACL del almacén de checkpoints. El checkpoint confirmado enlaza memoria y selección; un snapshot huérfano no se vuelve canónico. Derivaciones corruptas se reconstruyen desde mensajes y fuentes vigentes o bloquean. La API principal expone referencias/métricas y conserva sus ACL; no entrega snapshots completos de prompts/memoria. Eventos y llamadas registran hashes, bytes antes/después, exclusiones y cache. Costo y tokens reales solo existen si el endpoint entrega usage.

| Síntoma | Comprobación humana | Acción |
|---|---|---|
| Repite un dato incorrecto | Revisar origen, hash y decisiones incompatibles | Aclarar o sustituir explícitamente; no borrar registros |
| Olvida una regla | Revisar selección y mensajes originales | Recuperar evidencia o aclarar alcance |
| Usa herramienta incorrecta | Revisar contrato del rol, permisos y solicitud | Corregir contrato/catálogo en una versión revisada |
| Se contradice | Buscar restricciones duplicadas y sustituciones | Resolver conflicto antes de aprobar |
| Excede presupuesto | Revisar bytes, fuentes completas y duplicados | Acotar HU o cambiar política tras revisión y nuevo intento |
| Cambió política/prompt | Comparar hashes fijados por intento | Retry humano; aprobación anterior no se hereda |

No se deduce automáticamente envenenamiento ni necesidad de sesión nueva a partir de un síntoma. La retención/borrado del volumen pertenece a operación humana y debe preservar intentos activos y PR pendientes. TTL de cache no es retención de memoria.

Para rollback conservar el paquete y snapshot de despliegue previos. Deshabilitar afecta a intentos nuevos; los activos gestionados bajo otra política requieren retry explícito. Drenar los intentos activos antes de modificar la instalación. El estrés de 40 turnos es un escenario acotado; aceptación significa preservar decisiones y controles dentro del presupuesto, no duración ilimitada.

## Solicitudes individuales de contexto

El modelo solicita una sola operación por turno, exclusivamente mediante
context_request como objeto. Las formas admitidas son:

```json
{"context_request":{"op":"list_tree"}}
{"context_request":{"op":"read_file","path":"src/common/schema.py"}}
{"context_request":{"op":"search_text","query":"normalize_table_name"}}
```

Cada línea corresponde a una respuesta distinta. list_tree no recibe path;
search_text recibe solo op y query. Después del resultado puede solicitar otra
operación o devolver el contrato final del rol sin context_request. Listas, null,
campos adicionales y solicitudes mezcladas con salida final se rechazan antes
de leer, con acceptance=invalid_contract y diagnóstico seguro.

Los nuevos fallos de formato admiten Reintentar etapa por acción humana con
identidad, failure_id, revisión, perfil, contexto, procedencia y checkpoint
compatibles. Un reinicio no los reintenta automáticamente. Los históricos
con retryable=false conservan su mensaje y estado; para repetir ese caso se
presenta una HU nueva con planificación y aprobación propias. Política,
permisos, presupuestos y tratamiento de denegaciones siguen vigentes.
