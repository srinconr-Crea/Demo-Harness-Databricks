# Scaffold histórico AgentOps

Referencia conservada de `agentops-stacks` (origen `9dc9edd` en
`.agentops-stacks/manifest.yml`). Traslado desde la revisión del harness
`0ad1b387d7d0b2ff2a1904c6dfc259c4cd574f9f`, después de aplicar
`manage-hu-agent-context`. Los diez archivos trasladados conservan sus bytes.

Este ejemplo no es una entrada soportada ni se distribuye con la App FastAPI.
La operación vigente está en [operacion.md](../../docs/operacion.md) y el
runtime en [harness/](../../src/agents/harness/harness/). La evaluación real del
producto permanece en [evaluation.py](../../src/agents/harness/harness/evaluation.py).

| Ruta anterior | Ruta en este ejemplo |
| --- | --- |
| `src/agents/harness/agent.py` | [agent/agent.py](agent/agent.py) |
| `src/agents/harness/graph.py` | [agent/graph.py](agent/graph.py) |
| `src/agents/harness/tools.py` | [agent/tools.py](agent/tools.py) |
| `src/agents/harness/app/utils.py` | [agent/app/utils.py](agent/app/utils.py) |
| `src/agents/harness/eval/create_dataset.py` | [agent/eval/create_dataset.py](agent/eval/create_dataset.py) |
| `src/agents/harness/eval/evaluate_agent.py` | [agent/eval/evaluate_agent.py](agent/eval/evaluate_agent.py) |
| `src/agents/harness/eval/gates.yml` | [agent/eval/gates.yml](agent/eval/gates.yml) |
| `src/agents/harness/eval/utils.py` | [agent/eval/utils.py](agent/eval/utils.py) |
| `src/components/eval/scorers.py` | [components/eval/scorers.py](components/eval/scorers.py) |
| `resources/uc_function_registration.yml` | [resources/uc_function_registration.yml](resources/uc_function_registration.yml) |
| `src/agents/harness/.env.example` | [agent/.env.example](agent/.env.example) (copia histórica) |

Las dependencias antiguas viven en [pyproject.toml](pyproject.toml), separado
del producto. Los imports `graph`, `tools` y `app.utils` requieren la raíz
`agent/` en el path; el notebook eval conserva su resolución relativa. La
referencia `components/eval/scorers.py` en sus utilidades apunta al árbol de
este ejemplo. Los gates no validan el código generado por el harness actual.

Los notebooks requieren Spark, MLflow, un experimento, Foundation Model API,
dataset y permisos apropiados; pueden registrar objetos y llamar servicios.
No se ejecutaron como verificación del traslado ni se garantiza su ejecución.
El YAML UC es un stub: `../src/components/tools/registry.py` no existe, falta
cluster/principal y su ruta antigua se conserva como procedencia. No está
incluido en el bundle; no ejecutarlo ni incorporarlo como recurso operativo.
`resources/experiment.yml` del producto sí permanece incluido y conserva sus
bindings. No se eliminaron recursos, checkpoints ni paquetes anteriores.
