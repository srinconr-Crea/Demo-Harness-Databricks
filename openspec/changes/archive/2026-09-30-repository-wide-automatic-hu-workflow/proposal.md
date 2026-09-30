# Proposal

## Why

El piloto restringe el desarrollo a un notebook y el contexto general a extractos pequeños; ampliar únicamente las rutas dejaría pruebas y conocimiento insuficientes para trabajar sobre el repositorio. La conversación expone detalles intermedios y exige otra aprobación antes del PR, mientras Haiku puede bloquear por recomendaciones que deben ser asesoras.

## What Changes

- Habilitar alcance de repositorio en `general_patch`, con políticas independientes de lectura y escritura, rutas solo lectura, rutas sin acceso y límites configurados por cliente. Conservar compatibilidad del piloto `silver_safe_ratio`.
- Mantener operaciones `create`, `modify`, `delete` y lista explícita de extensiones `.py`, `.sql`, `.ipynb`, `.yml`, `.yaml`, `.json`, `.toml`, `.md`, `.txt`.
- Añadir contexto controlado mediante árbol, búsqueda y lectura de archivos; separar contratos y prompts del desarrollador por estrategia.
- Seleccionar validaciones por tipo e impacto: `python_compile`, `pytest_sandbox`, `sql_lint`, `yaml_validate`, `json_validate`, `notebook_validate`, `databricks_bundle_validate`, `toml_validate`, `markdown_structure` y comprobaciones de texto. Las pruebas funcionales siguen siendo obligatorias cuando corresponden.
- Convertir Haiku 4.5 en asesor: conservar hallazgos, fallos y costos sin bloquear ni consumir correcciones. Sonnet y controles obligatorios siguen bloqueando.
- Mostrar preguntas solo cuando exista ambigüedad y propuesta en lenguaje natural con archivos, cambios previstos y pruebas; conservar comentarios y revisiones antes de aprobar.
- **BREAKING**: sustituir la aprobación humana del diff final por autorización de publicación otorgada con la propuesta. Tras aprobación vigente, ejecutar apply, verify, sync, archive y creación del PR automáticamente. No registrar una aprobación humana del diff inexistente.
- Mostrar checklist persistido por fase, revisión y fechas de Colombia, recomendaciones y enlace al PR; separar creación del PR de sus checks y ofrecer detalle técnico bajo demanda.

## Capabilities

### New Capabilities

- `repository-context`: lectura, búsqueda e inventario controlados del checkout para exploración, planificación y desarrollo.

### Modified Capabilities

- `client-policy`: alcance de repositorio, permisos diferenciados y extensiones explícitas.
- `deterministic-editing`: operaciones generales sujetas a la política y al manifiesto del plan aprobado.
- `execution-validation`: adaptadores por tipo e impacto, verificación obligatoria y Haiku asesor.
- `conversation-review`: conversación resumida, revisión de propuesta y continuación automática sin aprobación final del diff.
- `change-planning`: propuesta comprensible y manifiesto verificable de cambios y pruebas previstas.
- `github-publication`: publicación automática vinculada al plan aprobado y candidato verificado después del archivo.
- `observability-control`: checklist con evidencia por fase y separación de recomendaciones, fallos y checks.

## Impact

Contratos, `conversation.py`, `patch.py`, `checkout.py`, `openspec.py`, prompts, perfiles, interfaz y API conversacional; validadores, empaquetado y runner del Job sandbox; pruebas locales y sintéticas. Añadir dependencias de validación fijadas y configurar adaptadores y objetivos confiables por cliente. Actualizar README, operación, AGENTS.md y contexto OpenSpec para reflejar el requisito de aprobación sustituido explícitamente por el usuario.

El desarrollo ocurre en este harness. No cambiar recursos ni datos de NaturaPet, ejecutar pruebas contra ellos, desplegar bundles cliente ni hacer merge. La activación de un perfil general exige sus suites y sandbox operativos; esta propuesta no acredita que NaturaPet ya los tenga. Conservar preparación única OpenSpec, ramas feature/* y revisión humana del PR. No implementar persistencia analítica nueva ni una refactorización general fuera de lo necesario.
