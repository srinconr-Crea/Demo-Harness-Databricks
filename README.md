# Databricks Development Harness

Harness de desarrollo separado de los repositorios cliente. Parte del scaffold de
[`agentops-stacks`](https://github.com/databricks-solutions/agentops-stacks)
(commit `9dc9edd`) y añade un flujo controlado para recibir una historia de usuario
(HU) manual, analizarla, editar una rama `feature/*`, validar en un sandbox y
abrir un pull request hacia la rama base del perfil. El merge y el despliegue del código del
cliente requieren revisión humana.

## Flujo de una HU

La App recibe **HU** y **descripción** después de la preparación manual del cliente: una persona ejecuta `openspec init --tools agents --no-animation`, configura contexto y los siete workflows requeridos, crea el PR e integra sus cambios. La App no inicializa ni actualiza OpenSpec ni crea PR de preparación. Cada HU clona el SHA base y consume sus skills versionadas; véase el procedimiento en `docs/operacion.md`.

El explorador aclara la HU y el planner presenta la propuesta, manifiesto y pruebas previstas para aprobación o cambios. Para ejecuciones nuevas, aprobar el plan autoriza aplicar, verificar, sincronizar, archivar y crear el PR automáticamente. Sonnet y las pruebas son obligatorios; Haiku es asesor. El diff real queda consultable y el merge y despliegue siguen siendo humanos. Los históricos conservan su modalidad original de aprobación. Véase [desarrollo general y publicación automática](docs/repository-workflow.md) para permisos, adaptadores y recuperación.

Los flujos OpenSpec usan `databricks-claude-sonnet-5-5`; el desarrollador opera en `apply` y el verificador independiente usa el modelo configurado. Cada instalación activa un perfil externo aprobado con `general_patch` o una estrategia acotada y sus propios límites y validadores. `silver_safe_ratio` sigue disponible para perfiles que lo configuren. El código general se ejecuta en un Job de Databricks dedicado con otra identidad y sin secretos de la App.

El volumen Unity Catalog conserva JSON de ejecuciones, eventos y llamadas por modelo, más checkpoints exactos y diffs de revisión con ACL restringidas. La tabla Delta del harness coordina revisiones y leases. El costo por llamada es estimado cuando el endpoint entrega `usage`.

El Job dedicado ya tiene una identidad separada y pruebas sintéticas positivas y negativas verificadas. El flujo completo de interfaz se comprobó con un cliente local sintético y la CLI real de OpenSpec; véase la [evidencia](docs/evidence/2026-09-30-openspec/verification.md). Cada cliente debe integrar su PR de preparación y configurar sus rutas y pruebas antes de habilitar HUs generales.

## Estructura

Para retomar el desarrollo sin depender del historial del chat, consulta el
[protocolo de contexto del proyecto](docs/contexto-proyecto.md).

| Ruta | Función |
| --- | --- |
| `databricks.yml`, `resources/` | Bundle aislado de App, catálogo, esquema, volumen y experimento. |
| `src/agents/harness/app/` | Formulario y servidor FastAPI. |
| `src/agents/harness/harness/` | Contratos, orquestación, GitHub App, modelos, validación y almacenamiento. |
| `src/agents/harness/config/` | Defaults comunes de roles, routing, precios y límites; el perfil se entrega al despliegue. |
| `examples/` | Perfiles de instalación y [scaffold histórico](examples/legacy-agentops-scaffold/README.md), separados del runtime y del paquete de despliegue. |
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
```

Una App por cliente utiliza el mismo producto y un perfil aprobado entregado en
un paquete local. Sigue la [guía de configuración y despliegue](docs/configuracion-instalacion.md)
para preparar `.deployments/<id>`, validar, desplegar e iniciar la instalación.
El lanzador Windows recibe App y perfil CLI como argumentos.
Consulta [operación](docs/operacion.md) para controles y recuperación y el
[ejemplo piloto](examples/naturapet/README.md) para sus valores específicos.

## Aislamiento

El bundle crea recursos con nombres `demo_harness_*` y no usa catálogos,
esquemas, jobs ni pipelines del cliente. La única escritura prevista en el
repositorio del cliente es una rama `feature/*` seguida de un PR hacia
`develop`. El merge y despliegue del cliente siguen siendo humanos.
