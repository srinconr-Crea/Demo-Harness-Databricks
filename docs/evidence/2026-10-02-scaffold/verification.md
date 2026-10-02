# Limpieza del scaffold — 2026-10-02

Cambio: `remove-unused-harness-scaffold`. Base de apply:
`0ad1b387d7d0b2ff2a1904c6dfc259c4cd574f9f`, rama `Db_Spec_Harness`.
El usuario autorizó aplicar/sincronizar/archivar, publicar en esa rama existente
y actualizar la App con perfil CLI `CREA_DEV`, elegido explícitamente. También
autorizó corregir los 35 errores de lint presentes en la base. Estas decisiones
de entrega están registradas en el diseño; no son permisos de una HU cliente.

## Inventario y conservación

[moves.json](moves.json) contiene los diez pares origen/destino y SHA-256 de
bytes comprobados antes y después. El [README del ejemplo](../../../examples/legacy-agentops-scaffold/README.md)
documenta motivos, dependencias, procedencia y límites. Imports de AgentServer,
LangGraph y utilidades genéricas se consumían solo dentro del scaffold; la
entrada activa es `app/start_server.py` → `harness/`. CI prueba el producto y
el PySpark sintético, sin ejecutar eval/scorers del ejemplo.

La copia histórica de `.env.example` conserva sus variables. El ejemplo tiene
su propio `pyproject.toml`; el producto pierde únicamente el grupo eval.
El lock se regeneró con uv: 185 a 51 paquetes, sin versiones nuevas entre los
paquetes restantes. Runtime, dev y spark-validation se instalaron congelados
en entornos locales. OpenSpec CLI 1.13.2 y sus package manifests permanecen.

Se conservaron configuración del bundle/App, todos los recursos incluidos,
scripts operativos, defaults, evaluación real y su prueba, manifest de
agentops-stacks, ejemplos anteriores, documentación y evidencia histórica.
El único YAML trasladado no estaba incluido y apunta a un registry ausente.
No se ejecutó ni se fabricó ese registry. Las guías setup/supervisor quedan
identificadas como históricas. Los enlaces afectados resuelven y el contexto
OpenSpec conserva el presupuesto de 8 KiB. `manage-hu-agent-context` ya estaba
aplicado en la base; se revalidaron referencias y defaults contra esa revisión.

[package-comparison.json](package-comparison.json) conserva los manifiestos
sintéticos antes/después: 58 a 49 archivos, nueve exclusiones previstas (el
scorer de components ya no pertenecía al paquete). Solo cambian pyproject/lock
y los seis módulos con ajustes de lint; no cambia configuración operativa.
La regresión nueva comprueba hashes, perfil, App/runner/defaults/CLI y exclusión
del scaffold. Arranca el entrypoint FastAPI empaquetado con WorkspaceClient
stub y perfil sintético; `/` y `/configuration` devuelven HTTP 200. No usa
credenciales ni invoca GitHub, modelos o Databricks.

## Verificación local

- Baseline: 224 passed, 1 skipped (PySpark ausente), 1076,32 s.
- Regresiones nuevas de paquete y arranque: 2 passed.
- Ratio positivo/negativo, fallo seguro y recuperación hasta PR simulado:
  2 passed, 95,75 s.
- PySpark sintético con filas positiva, cero y NULL: 1 passed, 12,97 s.
- Lint activo de CI: correcto después de los ajustes autorizados.
- OpenSpec change: validate --strict correcto, skip_specs explícito.
- Specs principales: 15 passed, 0 failed; no deltas que sincronizar.
- Paquete de instalación: bundle validate --strict -t dev con CREA_DEV correcto.

Suite final: **227 passed, 0 failed, 0 skipped**, 941,76 s, incluido PySpark.
El caso ratio se amplió a positivo/negativo después de la colección de esta
suite; ambos pasaron aislados (2 passed). En conjunto quedan comprobados los
228 casos actuales, sin atribuir 228 a la ejecución agrupada.
Las dos variantes del flujo con CLI real, modelos/costos, skills, sandbox/job,
publicación/recovery y contratos existentes pasan. No hay llamadas reales a
modelos en las fixtures ni se inventan costos: las pruebas de usage/ausencia
de usage y registro de costos conservan sus aserciones. Los fallos sintéticos
impiden publicación y requieren nueva aprobación; los reinicios conservan
revisión, perfil y checkpoints.

La CLI OpenSpec del paquete sintético también se instaló desde package-lock con
npm ci: versión 1.13.2. [test-results.json](test-results.json) registra los casos
y duraciones de la suite, sin logs o credenciales. git diff --check es correcto
y Git reconoce los diez traslados con similitud 100%.

Los primeros intentos locales encontraron permisos de temporales y caché del
sandbox. Se repitieron con aprobación automática de herramientas y rutas del
workspace. La construcción de PySpark encontró MAX_PATH: una unidad temporal H:
apunta únicamente a `.runs/`. Java encontró un fallo loopback con temporales
largos; se resolvió fijándolos en esa misma raíz corta. Se utilizó un
[JDK 17 portátil oficial de Microsoft](https://learn.microsoft.com/en-us/java/openjdk/download-major-urls),
sin instalación global ni cambios persistentes de PATH. Los intentos fallidos
son limitaciones ambientales registradas, no evidencia de pruebas aprobadas.

## Entrega y rollback

Cierre OpenSpec: 16/16 tareas, artefactos done/skipped; sin deltas según status.
Sync no requirió escrituras en specs principales. Archivo realizado en
`openspec/changes/archive/2026-10-02-remove-unused-harness-scaffold/`, conservando
el hash de `.openspec.yaml`. Se separó la preparación de cierre (tarea 5.4) de
las operaciones de archivo/despliegue/push para registrar cada resultado real.

Paquete local: `.deployments/naturapet-dev-clean-20261002`. Conserva perfil con
hash `27ac71c9b2c0c3bdea588ee77d06df20eedb228fbf47002121404f6f7f0df01f`,
App config y política `context.enabled=true` de la instalación previa,
comparados con los archivos remotos de la fuente anterior. El default versionado
del producto permanece false. Los hashes de overrides quedan en installation.json.

Despliegue `01f1bea1fae712918b5087ac138dce29`: **SUCCEEDED**, fuente nueva
`/Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-clean-20261002`,
modo SNAPSHOT. Inicio completado el 2026-10-02 a las 20:44:11 UTC (15:44:11
America/Bogota). App RUNNING y compute ACTIVE; `/` y `/configuration` autenticados
devuelven HTTP 200. [remote-package.json](remote-package.json) confirma los
39 archivos del snapshot con hashes idénticos al paquete, ausencia de scaffold,
11 bindings conservados y los mismos IDs de Job y warehouse. Perfil y política
de contexto coinciden con la instalación previa. [remote-smoke.json](remote-smoke.json)
conserva el resultado HTTP sin credenciales.

La App estaba detenida: el primer deploy fue rechazado mientras arrancaba el
cómputo; start reactivó automáticamente la fuente anterior y fue necesario
esperar a su término antes de crear el snapshot nuevo. Los logs muestran los
dos avisos ValueError de recuperación histórica ya documentados en la entrega
anterior; el servidor completó el arranque. No se ejecutaron HUs ni modelos
remotos, ni se actualizaron Job, permisos, recursos cliente o checkpoints.

La publicación Git utiliza `Db_Spec_Harness`, solicitada por el usuario. El
commit de entrega conserva código, archivo OpenSpec y esta evidencia; no se
hace merge. La App queda encendida.

Rollback remoto: deployment anterior `01f1be9bb4d719a7b01994e5ce6c1e3c`, snapshot
`/Workspace/Users/8910cd3e-32f6-4c75-b16f-b5ff3ea258d2/src/01f1be9bb4d719a7b01994e5ce6c1e3c`.
Rollback del refactor: revert del commit versionado. Los paquetes anteriores y
checkpoints se conservan. No se hace merge ni se cambian recursos de NaturaPet.
