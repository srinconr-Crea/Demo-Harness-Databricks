# Databricks Development Harness

Harness de desarrollo separado de los repositorios cliente. Parte del scaffold de
[`agentops-stacks`](https://github.com/databricks-solutions/agentops-stacks)
(commit `9dc9edd`) y añade un flujo controlado para recibir una historia de usuario
(HU) manual, analizarla, editar una rama `feature/*`, validar en un sandbox y
abrir un pull request hacia la rama base del perfil. El merge y el despliegue del código del
cliente requieren revisión humana.

## Flujo de una HU

La App recibe **HU** y **descripción**. Una operación de incorporación separada clona el repositorio cliente, inicializa OpenSpec una sola vez y abre un PR de preparación. Una persona debe integrar ese PR antes de enviar HUs. Cada HU posterior clona el SHA base completo en un workspace local temporal y verifica que OpenSpec ya esté versionado.

El explorador puede pedir aclaraciones. El planner genera proposal, specs, design y tasks; la App los muestra para aprobación o cambios. Tras aprobar el plan, el desarrollador aplica código dentro de la política del perfil. Las pruebas configuradas y dos verificadores revisan el resultado. OpenSpec se sincroniza y archiva antes de mostrar el diff final; una aprobación humana en la App permite abrir el PR. El merge y despliegue del cliente siguen siendo manuales.

Los flujos OpenSpec usan `databricks-claude-sonnet-5`; el desarrollador opera en `apply` y el verificador independiente usa el modelo configurado. `silver_safe_ratio` conserva su editor y prueba SQL sintética. Un perfil puede habilitar `general_patch` con rutas, extensiones, operaciones y validadores acotados. El código general se ejecuta en un Job de Databricks dedicado con otra identidad y sin secretos de la App.

El volumen Unity Catalog conserva JSON de ejecuciones, eventos y llamadas por modelo, más checkpoints exactos y diffs de revisión con ACL restringidas. La tabla Delta del harness coordina revisiones y leases. El costo por llamada es estimado cuando el endpoint entrega `usage`.

El Job dedicado ya tiene una identidad separada y pruebas sintéticas positivas y negativas verificadas. El flujo completo de interfaz se comprobó con un cliente local sintético y la CLI real de OpenSpec; véase la [evidencia](docs/evidence/2026-09-30-openspec/verification.md). Cada cliente debe integrar su PR de preparación y configurar sus rutas y pruebas antes de habilitar HUs generales.

## Estructura

| Ruta | Función |
| --- | --- |
| `databricks.yml`, `resources/` | Bundle aislado de App, catálogo, esquema, volumen y experimento. |
| `src/agents/harness/app/` | Formulario y servidor FastAPI. |
| `src/agents/harness/harness/` | Contratos, orquestación, GitHub App, modelos, validación y almacenamiento. |
| `src/agents/harness/config/` | Perfil del cliente, tareas de roles, routing, precios y límites configurables. |
| `openspec/` | Especificaciones del harness y cambios planificados. Cada cliente conserva su propio árbol OpenSpec en su repositorio. |
| `docs/agents/` | Especificación de la App y contratos de los roles. |
| `docs/sql/` | Consultas por llamada y conciliación opcional con `endpoint_usage`. |
| `.agentops-stacks/` | Metadatos de origen del scaffold. |
| `tests/` | Pruebas locales del flujo y de los controles. |
| `docs/` | Plan, diseño, piloto y guía de operación. |

## Probar y desplegar

```powershell
cd src/agents/harness
uv sync
npm ci
cd ../../..
uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider
databricks bundle validate --strict -t dev --profile CREA_DEV
databricks bundle deploy -t dev --profile CREA_DEV
databricks bundle run harness -t dev --profile CREA_DEV
```

La App desplegada actualmente se llama `demo-dbx-harness-mvp`. Para encenderla y abrirla desde Windows,
ejecuta [`iniciar-harness.bat`](iniciar-harness.bat). Después de las pruebas del
piloto se deja detenida. Consulta [`docs/operacion.md`](docs/operacion.md) para
credenciales, incorporación de clientes, costos y límites conocidos.

## Aislamiento

El bundle crea recursos con nombres `demo_harness_*` y no usa catálogos,
esquemas, jobs ni pipelines de NaturaPet. La única escritura prevista en el
repositorio del cliente es una rama `feature/*` seguida de un PR hacia
`develop`. No hay workflow que haga merge o despliegue de NaturaPet.
