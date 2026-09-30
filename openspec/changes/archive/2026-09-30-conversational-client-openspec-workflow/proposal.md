# Proposal

## Why

El flujo actual inicializa OpenSpec por cada HU, trabaja con una copia parcial del repositorio cliente y publica un PR en una ejecución sin pausas de revisión. Esto impide que la persona converse sobre el plan, vea cómo avanzan los specs y el código, y apruebe exactamente el resultado que se publicará; además, el editor actual solo cubre `silver_safe_ratio`.

## What Changes

- **BREAKING**: sustituir la entrada de siete campos por HU y descripción, con aclaraciones posteriores dentro de la conversación de la App.
- Incorporar cada cliente una sola vez: inicializar OpenSpec en su repositorio mediante un PR de preparación y exigir que la rama base ya contenga `openspec/config.yaml` antes de admitir HUs.
- Clonar en la App un commit identificado del repositorio cliente por intento; crear y modificar allí los artefactos OpenSpec y el código, con puntos de control persistentes que permitan reanudar tras aprobaciones o reinicios.
- Orquestar `explore`, `propose`, revisión y `update`, `apply`, `verify`, corrección y `sync`/`archive` como etapas conversacionales. Mostrar mensajes, artefactos, pruebas, diff, modelo y costo conforme se producen.
- Mantener planner, desarrollador y verificador como roles separados. `apply` invoca al desarrollador sobre tareas aprobadas; habilitar una estrategia de parches generales dentro de las rutas y operaciones admitidas por el perfil, con validaciones y pruebas propias.
- Exigir aprobación humana del plan antes de `apply` y del diff final completo en la App antes de crear el PR. La revisión y el merge del PR siguen siendo humanos en GitHub.

## Capabilities

### New Capabilities

- `client-workspace`: checkout cliente fijado a un commit, preparación única de OpenSpec y recuperación de borradores persistentes.
- `conversation-review`: conversación por HU, progreso incremental, revisión de versiones y decisiones humanas antes de implementar y publicar.

### Modified Capabilities

- `story-intake`: entrada de dos campos, aclaraciones y reintentos de una conversación persistente.
- `change-planning`: cambio OpenSpec por intento, sin reinicialización por HU, con revisión y actualización del plan.
- `deterministic-editing`: estrategia registrada de parches generales además de `silver_safe_ratio`, sin ampliar la autoridad del perfil.
- `execution-validation`: verificación contra specs, pruebas por tipo de cambio y ciclos de corrección.
- `client-policy`: autorización del checkout, archivos, operaciones y pruebas para cambios generales.
- `observability-control`: estados pausados, eventos y llamadas de todos los roles por etapa y revisión, con costos.
- `github-publication`: sincronización/archivo y diff exacto aprobados antes de crear una rama `feature/*` y su PR.

## Impact

Afecta la interfaz y API FastAPI, contratos de HU e intento, orquestación, adaptador OpenSpec, cliente GitHub App, estrategias de edición, pruebas, almacenamiento en volumen UC y configuración de perfiles/modelos. Requiere actualizar `openspec/config.yaml`, `README.md`, `docs/operacion.md` y la documentación de roles al implementar. Los JSON históricos permanecen legibles; las HUs nuevas usarán un contrato versionado. No autoriza cambios en recursos o repositorios de NaturaPet fuera del perfil ni merge o despliegue automático.
