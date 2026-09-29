# Proposal

## Why

El control `analyst` actual devuelve una decisión breve y efímera. Para que la intención de cada historia sea revisable y utilizable por desarrollo y verificación, el harness necesita producir y validar artefactos OpenSpec antes de editar código cliente.

## What Changes

- Sustituir el control `analyst` por una fase `planner` que genera `proposal`, especificaciones delta, diseño y tareas con la CLI de OpenSpec y un modelo de Databricks.
- Validar la estructura OpenSpec y contrastar el contenido con la política determinista del perfil antes de habilitar al desarrollador.
- Entregar los artefactos aprobados al desarrollador y al verificador; registrar sus referencias y hashes por intento.
- Preparar la publicación conjunta de código y artefactos OpenSpec en repositorios cliente habilitados explícitamente por perfil, con el mismo control de archivos y revisión humana del Pull Request.
- Mantener el tipo de edición `silver_safe_ratio` y los controles de sandbox existentes hasta que otras estrategias tengan sus propios validadores.
- **BREAKING**: cambiar los contratos internos de rol y routing de `analyst` a `planner`; los contratos de ejecución versionados deberán conservar lectura de registros históricos.

## Capabilities

### New Capabilities

- `change-planning`: generación, validación y persistencia de un cambio OpenSpec por intento de historia.

### Modified Capabilities

- `client-policy`: autorización explícita de rutas de artefactos OpenSpec en perfiles cliente, sin derivarla de texto de la historia.
- `execution-validation`: sustitución de la aprobación del analista por una planificación validada y consumida por desarrollo y verificación.
- `github-publication`: inclusión opcional y controlada de artefactos OpenSpec entre los archivos validados del Pull Request.
- `observability-control`: trazabilidad de cambios, artefactos, validación y llamadas del planner por intento.

## Impact

`harness/workflow.py`, `contracts.py`, `models.py`, `github.py`, `store.py`, `app/start_server.py`, configuración de agentes y modelos, perfil de cliente, bundle de la App, documentación y pruebas. La integración requiere disponer de la CLI de OpenSpec en el runtime y definir almacenamiento temporal aislado por intento. No cambia recursos ni datos de proyectos cliente durante esta fase de planificación.
