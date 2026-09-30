# Evidencia de implementación

Validación realizada el 30 de septiembre de 2026. La implementación queda en `feature/repository-wide-automatic-hu-workflow`.

## Comprobaciones

- Suite final: `python -m pytest tests -q -p no:cacheprovider`: **143 passed, 1 skipped**, 359,16 segundos. Aviso de deprecación del TestClient de Starlette.
- `openspec validate repository-wide-automatic-hu-workflow --strict`: válido.
- Sincronización semántica de ocho capacidades, conservando requisitos y escenarios ajenos al delta; `openspec validate --specs --strict`: **10 passed, 0 failed**.
- `databricks bundle validate --strict -t dev --profile CREA_DEV`: **Validation OK**, sin despliegue.
- `uv sync --locked --project src/agents/harness --dry-run`: resolución válida, sin cambios necesarios.
- Compilación de módulos activos y revisión de whitespace: correctas. Ruff de módulos nuevos y nuevas pruebas: correcto.

## Recorrido sintético

El navegador local recorrió HU ambigua, aclaración, propuesta, petición de ajustes, aprobación y continuación automática. El comentario se conservó durante polling y cambio de revisión. Preguntas y propuesta estuvieron visibles; artefactos, eventos y costos permanecieron bajo detalle desplegable.

Ejecución `b9d8c52b3204406a8768bb3207de757b`: ocho archivos previstos (Python, YAML, JSON, TOML, SQL, notebook, Markdown y texto), validadores reales y pytest aislado. Se comprobó recuperación tras reinicio y fallo local de escritura del diff. El checklist final mostró todas las fases correctas con fechas en America/Bogota y checks del PR pendientes por separado. El fixture usa lecturas tipadas para obtener hashes exactos, incluyendo saltos de línea de Windows; su almacenamiento local usa rutas extendidas para esta prueba.

Ejecución sintética adicional `ac87ce4132194c29b997bcea00fb13ac`: checkout y OpenSpec reales, ocho validadores y dos pruebas funcionales que comprueban salida Python, JSON, TOML y SQL. Una aprobación del plan produjo un único PR simulado. Finalizó el 30/09/2026 a las 16:42:59 America/Bogota. Update quedó no aplicable, sin OK ficticio.

## Controles negativos

Las pruebas cubren rutas prohibidas/solo lectura, enlaces, prefijos vecinos, traversal y unidades Windows, integridad del parche y candidato, límites de contexto, formatos inválidos, referencias externas de esquemas y magias sin cobertura. Haiku rechazado, no disponible o inválido permite continuar; errores de persistencia se propagan. Pruebas y Sonnet fallidos, manifiesto ampliado y base avanzada bloquean publicación o requieren nueva propuesta. La suite conserva pruebas históricas de aprobación del diff, recuperación de publicación y rechazo de divergencias/archivos remotos adicionales. El adaptador de bundle prueba resultado correcto, fallido, timeout, CLI ausente y objetivo ausente.

## Alcance operativo

Modelos y GitHub se simularon en las pruebas sintéticas; no se creó un PR remoto de este harness, no se hizo merge y no se desplegaron recursos. El perfil NaturaPet conserva su alcance original. La ejecución remota del Job no forma parte de esta validación local. Para habilitar validación de bundles cliente, el operador debe provisionar la CLI confiable y la autenticación de la identidad sandbox en su runtime; su ausencia bloquea la comprobación obligatoria. Véase `docs/repository-workflow.md`.
