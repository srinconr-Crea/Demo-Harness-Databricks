# Databricks Development Harness

Harness de desarrollo separado del repositorio NaturaPet. Parte del scaffold de
[`agentops-stacks`](https://github.com/databricks-solutions/agentops-stacks)
(commit `9dc9edd`) y añade un flujo controlado para recibir una historia de usuario
(HU) manual, analizarla, editar una rama `feature/*`, validar en un sandbox y
abrir un pull request hacia `develop`. El merge y el despliegue del código del
cliente requieren revisión humana.

## Estado del MVP

- Una Databricks App con un formulario para ID, título y cinco bloques: arquitectura, origen/destino, reglas de negocio, requisitos no funcionales y reglas de validación. La interfaz permite solicitar cancelación mientras la HU está activa y solicitar la parada de la App tras un estado final.
- Orquestador determinista con roles analista y desarrollador en `databricks-claude-sonnet-5`, y verificador en `databricks-claude-haiku-4-5`. Usa Foundation Model API con pago por token.
- Integración GitHub App limitada a `srinconr-Crea/Naturapet_DLH`, base `develop`, cambios en rutas permitidas y PR sin merge.
- Perfil NaturaPet en YAML. La estrategia validada añade una razón `columna = numerador / denominador` con `safe_divide` en el notebook Silver comercial autorizado; la medida concreta viene de cada HU.
- Prueba remota con datos sintéticos en un SQL warehouse nuevo y aislado. Comprueba el cálculo para costo positivo, cero y NULL; **no ejecuta el notebook PySpark completo**.
- Contratos versionados de HU, intento y llamada por agente en el volumen Unity Catalog del harness. `run_id`, `attempt_id` y `call_id` vinculan entradas, salidas, eventos, archivos, tiempos, tokens y costos estimados. Sin tope monetario inicial.

La lógica de esta estrategia ya no depende de la medida `NP-001`, pero sigue acotada a razones seguras en un notebook con la estructura configurada. Otros tipos de cambio necesitan editor, validadores y pruebas propias antes de permitir push/PR.

El piloto `NP-001` produjo [NaturaPet PR #6](https://github.com/srinconr-Crea/Naturapet_DLH/pull/6). La segunda prueba `NP-002` produjo [NaturaPet PR #7](https://github.com/srinconr-Crea/Naturapet_DLH/pull/7) y tres registros de llamadas a modelos, consultables por HU y agente. La [evidencia del primer piloto](docs/pilot/validacion.md) y la [guía de operación](docs/operacion.md) explican costos estimados y límites de validación. El [plan de implementación](docs/superpowers/plans/2026-09-28-productizacion-harness.md) registra el diseño y las comprobaciones pendientes de despliegue. Los cambios de esta iteración están en el repositorio del harness; la App desplegada no se actualiza hasta ejecutar el bundle.

## Estructura

| Ruta | Función |
| --- | --- |
| `databricks.yml`, `resources/` | Bundle aislado de App, catálogo, esquema, volumen y experimento. |
| `src/agents/harness/app/` | Formulario y servidor FastAPI. |
| `src/agents/harness/harness/` | Contratos, orquestación, GitHub App, modelos, validación y almacenamiento. |
| `src/agents/harness/config/` | Perfil del cliente, tareas de roles, routing, precios y límites configurables. |
| `docs/agents/` | Especificación de la App y contratos de los roles. |
| `docs/sql/` | Consultas por llamada y conciliación opcional con `endpoint_usage`. |
| `.agentops-stacks/` | Metadatos de origen del scaffold. |
| `tests/` | Pruebas locales del flujo y de los controles. |
| `docs/` | Plan, diseño, piloto y guía de operación. |

## Probar y desplegar

```powershell
cd src/agents/harness
uv sync
cd ../../..
uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider
databricks bundle validate --strict -t dev --profile CREA_DEV
databricks bundle deploy -t dev --profile CREA_DEV
databricks bundle run harness -t dev --profile CREA_DEV
```

La App se llama `demo-dbx-harness-mvp`. Para encenderla y abrirla desde Windows,
ejecuta [`iniciar-harness.bat`](iniciar-harness.bat). Después de las pruebas del
MVP se deja detenida. Consulta [`docs/operacion.md`](docs/operacion.md) para
credenciales, incorporación de clientes, costos y límites conocidos.

## Aislamiento

El bundle crea recursos con nombres `demo_harness_*` y no usa catálogos,
esquemas, jobs ni pipelines de NaturaPet. La única escritura prevista en el
repositorio del cliente es una rama `feature/*` seguida de un PR hacia
`develop`. No hay workflow que haga merge o despliegue de NaturaPet.
