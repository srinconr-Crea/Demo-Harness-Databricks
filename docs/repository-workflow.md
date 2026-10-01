# Desarrollo general y publicación automática

La App muestra preguntas cuando la HU sea ambigua, acumula respuestas y vuelve a explorar hasta concretarla. Sonnet genera y valida los artefactos OpenSpec y presenta una propuesta en español con archivos/operaciones previstos y pruebas requeridas. La persona puede comentar, pedir update o aprobar. El código mostrado en esta fase es previsto: el diff real aparece después de aplicar.

Para ejecuciones nuevas, aprobar el hash del plan autoriza apply, verify, sync, archive y crear el PR automáticamente, sin aprobación humana adicional del diff. El manifiesto, el SHA base y la matriz de pruebas forman parte del hash. Un cambio del plan invalida la aprobación; archivos u operaciones adicionales vuelven a revisión. La publicación compara bytes exactos y la rama remota completa. Si la base avanza, vuelve a planificar y aprobar. Merge y despliegue siguen siendo humanos.

Los intentos históricos conservan modalidad diff_review y awaiting_diff_review. El contrato v5 incluye publication_mode; un registro sin ese campo conserva la modalidad histórica. No se fabrican aprobaciones del diff ni se reanudan registros nuevos con una versión antigua incompatible. La reversión operativa debe impedir nuevas ejecuciones y conservar checkpoints y PR existentes.

## Política de repositorio

El ejemplo `tests/fixtures/clients/repository.yaml` declara repository_policy.scope: repository. Los perfiles existentes usan scope: prefixes y conservan allowed_paths y el piloto silver_safe_ratio. No se activa implícitamente NaturaPet ni se prueba código contra sus recursos.

La política central distingue lectura y escritura. read_only_paths permite consultar archivos sin editarlos; denied_paths excluye contexto y paquete de pruebas. `.github/`, `openspec/` y `AGENTS.md` son solo lectura para developer; `.git/`, `.env*`, credenciales y claves privadas quedan sin acceso. Las prohibiciones prevalecen sobre cualquier permiso de extensión. Solo el workflow OpenSpec puede escribir su prefijo. Rutas absolutas, traversal, unidades Windows, enlaces y escapes se rechazan.

general_patch conserva create/modify/delete y extensiones explícitas `.py`, `.sql`, `.ipynb`, `.yml`, `.yaml`, `.json`, `.toml`, `.md`, `.txt`, junto a archivos/bytes máximos. El tipo autorizado debe tener validación pertinente. Las modificaciones y eliminaciones requieren hash previo y los parches inválidos no se aplican parcialmente. Snapshots, restauración y publicación verifican la misma política.

## Contexto y contratos

`conversation.py` conserva fases, modelos y permisos. `skills.py` lee las skills del SHA base cliente, completas y solo lectura; no mantiene una copia en la App. `openspec.py` consulta instrucciones CLI y valida raíces, archivos y dependencias. Cada prompt combina skill, contrato JSON, HU y contexto autorizado. Las llamadas conservan ruta/hash de la skill, versión CLI y hash/snapshot de instrucciones; la aprobación del plan incluye catálogo y runtime.

| Fase | Skill consumida | Resultado/control |
| --- | --- | --- |
| explore | openspec-explore | summary y questions; inventario de specs |
| propose/update | openspec-propose / openspec-update-change | cuatro artefactos y dependencias CLI; revisión del manifiesto |
| apply | openspec-apply-change | instructions apply; operations o expression |
| verify | openspec-verify-change | Sonnet obligatorio y evidencia de pruebas |
| sync/archive | openspec-sync-specs / openspec-archive-change | preflight y archive deterministas, una sola sincronización |

Los workflows no son subcomandos CLI homónimos. allowed-tools, referencias y texto de una skill no conceden shell, edición directa, modelos ni aprobaciones adicionales. El procedimiento manual para seleccionar los siete workflows e integrar el PR está en operación. Una skill faltante/incompatible bloquea antes de llamadas; las actualizaciones ocurren fuera de las HUs. Los snapshots protegidos conservan instrucciones completas aunque los logs estén truncados.

RepoContext ofrece list_tree, search_text y read_file mediante solicitudes JSON tipadas; no ofrece shell ni ejecución. Las lecturas incluyen SHA-256 y truncamiento explícito. Presupuestos iniciales configurables: 10 búsquedas, 20 lecturas, 200 KB totales, 50 KB por archivo, 20 rondas y 30 segundos para consultas de cada etapa. Cada ronda del modelo se registra con tokens y costo si el endpoint informa usage. Nunca se presume contenido leído cuando se agota el presupuesto.

developer recibe todos los specs delta, tareas y manifiesto de la revisión aprobada. Para general_patch devuelve operations con op/path/content/expected_sha256 y notes; para ratio conserva expression exacta. El contenido de los archivos y de la HU no amplía permisos, modelos ni pruebas.

## Validadores y pruebas funcionales

| Adaptador | Cobertura |
| --- | --- |
| python_compile | Sintaxis Python |
| pytest_sandbox | Suites funcionales configuradas, en Job dedicado |
| sql_lint | Parser Databricks, rechazo de construcciones sin cobertura |
| notebook_validate | nbformat, Python/SQL y magias admitidas; rechaza otros lenguajes |
| yaml_validate, json_validate, toml_validate | Parseo y esquemas configurados por el operador |
| markdown_structure | Título principal Markdown |
| text_validate | Texto UTF-8 sin contenido binario |
| databricks_bundle_validate | bundle validate --strict del target confiable, sin deploy |

impact_rules enlaza rutas/componentes con suites adicionales. Cambiar configuración o eliminar archivos puede activar pruebas del consumidor. El parser y la compilación no demuestran resultados funcionales: código y datos requieren suites configuradas. test_paths, esquemas, bundle_target y bundle_paths son del operador; la HU no define comandos. Los esquemas no admiten referencias externas.

El Job usa identidad dedicada y un entorno sin secretos de la App, verifica hash del ZIP y límites y conserva resultados vinculados al candidato/revisión. El paquete conserva dependencias/pruebas de lectura autorizada y excluye secretos. El runtime fija pytest; validadores del harness tienen versiones en pyproject.toml y uv.lock. Para habilitar bundle_validate el operador debe provisionar una CLI Databricks moderna y confiable en el runtime del Job: CLI ausente, autenticación aislada ausente o comprobación obligatoria fallida bloquean publicación. No se usan credenciales de la App para validar bundles cliente. Cualquier prueba remota continúa restringida a demo_harness_* y al warehouse sintético autorizado.

## Haiku y presentación

Sonnet 5 y las pruebas obligatorias son gates. Haiku 4.5 es asesor: conserva recomendaciones, respuesta inválida, timeout o indisponibilidad sin bloquear ni consumir correcciones. Su transporte tiene timeout HTTP de 20 segundos y presupuesto de reintento de 1 segundo; una llamada sin usage conserva costo ausente. Fallos de persistencia, autorización e integridad siguen propagándose.

El hilo principal muestra preguntas, propuesta y decisiones. Eventos técnicos, artefactos, diff y costos están bajo detalle desplegable. Los comentarios se conservan por ejecución/revisión y durante polling/update. El checklist se deriva de evidencia persistida por fase y presenta tiempos en America/Bogota. Pendiente, en curso, fallido y no aplicable nunca se convierten artificialmente en OK. PR creado y checks passed/pending/failed/unavailable se muestran por separado. La App no se detiene al crear el PR; el operador decide la parada autorizada cuando no hay otras historias activas.
