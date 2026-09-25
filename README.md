# Databricks Development Harness — MVP

Harness de desarrollo separado del repositorio NaturaPet. Parte del scaffold de
[`agentops-stacks`](https://github.com/databricks-solutions/agentops-stacks)
(commit `9dc9edd`) y añade un flujo controlado para recibir una historia de usuario
(HU) manual, analizarla, editar una rama `feature/*`, validar en un sandbox y
abrir un pull request hacia `develop`. El merge y el despliegue del código del
cliente requieren revisión humana.

## Estado del MVP

- Una Databricks App con un formulario para ID, título y cinco bloques: arquitectura, origen/destino, reglas de negocio, requisitos no funcionales y reglas de validación.
- Orquestador determinista con roles analista y desarrollador en `databricks-claude-sonnet-5`, y verificador en `databricks-claude-haiku-4-5`. Usa Foundation Model API con pago por token.
- Integración GitHub App limitada a `srinconr-Crea/Naturapet_DLH`, base `develop`, cambios en rutas permitidas y PR sin merge.
- Perfil NaturaPet en YAML. El primer cambio implementado es la medida `margen_sobre_costo_pct` en Silver comercial.
- Prueba remota con datos sintéticos en un SQL warehouse nuevo y aislado. Comprueba el cálculo para costo positivo, cero y NULL; **no ejecuta el notebook PySpark completo**.
- Registro de ejecuciones en un volumen Unity Catalog nuevo, usando Files API. Costos de modelos estimados a partir de tokens reportados y tarifas configurables. Sin tope monetario inicial.

La estructura y el perfil permiten incorporar otros clientes, pero el ejecutor de cambios de este MVP está acotado a la HU piloto de NaturaPet. Para otro caso se debe implementar y probar una estrategia de edición y sus validadores antes de permitir push/PR.

El piloto `NP-001` produjo [NaturaPet PR #6](https://github.com/srinconr-Crea/Naturapet_DLH/pull/6), abierto y pendiente de revisión humana. La [evidencia de validación](docs/pilot/validacion.md) incluye el diff, costo estimado y límites de pruebas. La App y el warehouse quedaron detenidos.

## Estructura

| Ruta | Función |
| --- | --- |
| `databricks.yml`, `resources/` | Bundle aislado de App, catálogo, esquema, volumen y experimento. |
| `src/agents/harness/app/` | Formulario y servidor FastAPI. |
| `src/agents/harness/harness/` | Contratos, orquestación, GitHub App, modelos, validación y almacenamiento. |
| `src/agents/harness/config/` | Perfil NaturaPet, routing y precios configurables. |
| `.agentops-stacks/` | Metadatos de origen del scaffold. |
| `tests/` | Pruebas locales del flujo y de los controles. |
| `docs/` | Plan, diseño, piloto y guía de operación. |

## Probar y desplegar

```powershell
cd src/agents/harness
uv sync
cd ../../..
uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider
databricks bundle validate -t dev --profile CREA_DEV
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
