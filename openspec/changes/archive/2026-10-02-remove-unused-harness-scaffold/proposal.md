# Proposal

## Why

El producto FastAPI conserva módulos LangGraph/AgentServer, evaluación genérica y un recurso UC sin entrada válida que no participan en el flujo operativo observado. Limpiar su superficie activa reduce confusión y dependencias, conservando ejemplos, documentación, procedencia y contratos actuales del harness.

## What Changes

- Retirar del árbol operativo agent.py, graph.py, tools.py, app/utils.py y eval/ del scaffold; conservar sus referencias reutilizables en examples/legacy-agentops-scaffold, claramente separadas del producto.
- Trasladar el scorer genérico src/components/eval/scorers.py y el YAML UC no incluido al área de ejemplos históricos, declarando prerrequisitos ausentes y carácter no operativo.
- Retirar del paquete del producto el grupo de dependencias eval exclusivo del scaffold, regenerar lock y conservar las dependencias de ejemplos fuera del runtime; mantener dev y spark-validation.
- Alinear referencias actuales, configuración ejemplificada y documentación conservada con la estructura limpia; preservar históricos y evidencia sin convertirlos en procedimientos vigentes.
- Verificar arranque FastAPI, preparación de instalaciones, API/HU, recuperación, costos, validadores y sandbox mediante suite completa y flujo sintético; no eliminar recursos desplegados.

## Capabilities

### New Capabilities

Ninguna. Refactor de organización, dependencias y documentación sin capacidad funcional nueva.

### Modified Capabilities

Ninguna. Los contratos actuales de operación, aislamiento, observabilidad y despliegue se mantienen. Se declara skip_specs: true; no se inventan requisitos funcionales para una limpieza interna.

## Impact

Scaffold bajo src/agents/harness, src/components/eval/scorers.py, resources/uc_function_registration.yml, pyproject.toml/uv.lock, examples/legacy-agentops-scaffold, referencias documentales y pruebas de empaquetado pertinentes. El runtime harness/, entradas app/start_server.py/provision_run_state.py/sandbox_job_runner.py, index.html, scripts operativos, defaults, OpenSpec/skills, pruebas reales y recursos activos se conservan.

resources/experiment.yml está incluido en databricks.yml: se conserva junto con sus bindings, aunque el runtime inspeccionado no importe MLflow. Su retiro implica ciclo de recursos y requiere otro cambio con evidencia del entorno. También se conserva .agentops-stacks/manifest.yml como procedencia. No se borran documentación, ejemplos existentes, checkpoints, perfiles locales, entornos, caches de operadores ni recursos Databricks/GitHub. Sin cambio de API, modelos, aprobaciones o despliegue previsto.

Cambio independiente de manage-hu-agent-context; ambos revalidan SHA y referencias si el otro se aplicó primero. Este artefacto es una propuesta, no evidencia de limpieza realizada.
