# Plan de trabajo: harness de desarrollo para Databricks

**Fecha de revisión:** 2026-09-25
**Estado:** scaffold y MVP publicados en `MVP-Databricks-Harness`. La HU piloto creó [NaturaPet PR #6](https://github.com/srinconr-Crea/Naturapet_DLH/pull/6) hacia `develop`, abierto y sin merge. La App y el warehouse aislado están detenidos. La revisión humana y los checks de CI del cliente quedan pendientes.

Este documento registra el plan original. La implementación y sus límites actuales se describen en [`operacion.md`](operacion.md). Las secciones siguientes que usan el futuro expresan la arquitectura objetivo y no implican que cada capacidad ya esté implementada.

## 1. Objetivo y alcance

Construir un producto reutilizable que, a partir de una historia de usuario (HU) y cinco bloques preparados por una persona —arquitectura, origen y destino, reglas de negocio, requisitos no funcionales y reglas de validación—, analice un repositorio Databricks, proponga y ejecute un cambio en una rama nacida de `develop`, verifique el resultado y abra un pull request (PR) con evidencias. El primer caso será NaturaPet; la lógica general quedará en un repositorio independiente y el contexto propio de cada cliente en configuración versionada.

**Criterio de éxito del piloto:** una HU pequeña y representativa de NaturaPet termina en un PR hacia `develop` con código, pruebas, evidencia de validación, trazabilidad de decisiones y costo registrado; no hay push directo a `develop`, ejecución de jobs ni despliegue automático causado por el harness.

**Límites del primer incremento:** GitHub como proveedor Git; repositorios Databricks con Python, notebooks y DAB; un cliente (NaturaPet); entrada manual de HU. Azure Boards/Azure Functions, Power BI, CRM, extracción documental y otros proveedores Git quedan como adaptadores posteriores. Genie se usaría solo cuando aporte contexto verificable; no es requisito para abrir el primer PR.

## 2. Recursos verificados y consecuencias

| Recurso | Evidencia verificada | Consecuencia para el plan |
| --- | --- | --- |
| `agentops-stacks` | Se revisó `main` en `9dc9edd` (2026-09-18). El template genera DAB, App por agente con LangGraph/MLflow AgentServer, componentes opcionales, evaluación por agente y CI/CD. Entradas: cloud, plataforma CI/CD, Vector Search, Lakebase, UC Functions y origen del dataset de evaluación. | Usarlo como base del **servicio del harness**, no asumir que ya implementa un agente que edita repositorios, calcula costos, hace routing o crea PR. [Repositorio](https://github.com/databricks-solutions/agentops-stacks), [schema de entrada](https://github.com/databricks-solutions/agentops-stacks/blob/main/databricks_template_schema.json). |
| NaturaPet `develop` | Se revisó `9c48831` (2026-05-13). Tiene DAB, jobs de Bronze/Silver/Gold, `src/common`, notebooks por dominio y tests. Usa catálogos `naturapet_dev`, `naturapet_qa`, `naturapet_prod`, con esquemas por dominio/capa. | Construir un adaptador de contexto y validación para este layout; no sustituir su bundle ni sus jobs. [Rama develop](https://github.com/srinconr-Crea/Naturapet_DLH/tree/develop). |
| CI/CD de NaturaPet | Push a `develop` despliega `dev`; push a `qa` despliega `qa`; push a `main` despliega `prod`. Actualmente los PR disparan validación solo si apuntan a `main`. | Trabajar en `feature/*` y solicitar revisión humana del PR. La extensión de la CI hacia `develop` queda pendiente; el MVP valida localmente y con SQL sintético remoto. No hacer merge automático. [Workflow](https://github.com/srinconr-Crea/Naturapet_DLH/blob/develop/.github/workflows/databricks-cicd.yml). |
| Compatibilidad de ambientes | El scaffold propone `dev/staging/prod`, un esquema UC por proyecto y promoción desde `main`/tags. NaturaPet usa `dev/qa/prod`, esquemas por dominio y `develop/qa/main`. | Mantener **dos bundles y ciclos CI/CD independientes**; mapear explícitamente ambientes. Evitar copiar la CI/CD del scaffold dentro de NaturaPet. |
| Entorno local | Databricks CLI `v1.18.0`, Python `3.13.14`. El schema actual del scaffold declara CLI mínima `v1.1.0` y Python `>=3.11`. | El requisito de CLI ya se cumple. Verificar compatibilidad real de dependencias y runtime de la App con Python 3.13 antes del despliegue. |
| Workspace | `CREA_DEV` permitió crear y ejecutar la App, catálogo, esquema, volumen, secreto y warehouse propios; ambos endpoints de Foundation Model respondieron a una invocación mínima. | La viabilidad de recursos quedó comprobada en paralelo a NaturaPet. Los costos reales de ejecución se evaluarán tras el piloto. |
| Directorio de trabajo actual | La rama local `MVP-Databricks-Harness` nació de `main` en el remoto `Demo-Harness-Databricks`. | Publicar esta rama una vez cerradas las verificaciones; mantener el harness independiente del código de NaturaPet. |

La referencia anterior a AI Dev Kit como fuente de skills debe actualizarse: las skills se distribuyen hoy desde [Databricks AI Tools](https://github.com/databricks/databricks-agent-skills); AI Dev Kit conserva otros componentes, incluido un servidor MCP. Su adopción será selectiva y versionada, después de validar licencias, compatibilidad y valor en el piloto. [Estado actual del AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit).

## 3. Arquitectura propuesta

```text
HU + cinco bloques + criterios de aceptación
                  │
                  ▼
          API/CLI del harness
                  │
          motor de flujo en Python
       ┌──────────┼──────────┐
       ▼          ▼          ▼
 políticas    agentes     validadores
 y costos     especializados  y evidencias
       └──────────┼──────────┘
                  ▼
       adaptadores Git / Databricks / Genie
                  │
       feature/* en repo NaturaPet
                  │
         PR hacia develop
```

**Tres límites de propiedad:**

1. **Repositorio del harness:** scaffold de `agentops-stacks` fijado a un commit o release, motor Python, agentes, conectores, políticas, pruebas, DAB/App y CI propia.
2. **Perfil de cliente NaturaPet:** YAML y documentos que describen repositorio, ramas, ambientes, estructura Bronze/Silver/Gold, dominios, catálogos, rutas permitidas, comandos de validación y vocabulario de negocio. Sin credenciales ni datos sensibles en Git.
3. **Repositorio del cliente:** notebooks, código común, jobs y DAB que el harness modifica únicamente en ramas de feature. Una pequeña integración de CI para validar PR hacia `develop` será el primer cambio propuesto allí.

El scaffold proporciona una App por agente, pero para el primer incremento conviene **una App de entrada y un flujo determinista**, con especialistas invocados como componentes. Se decidirá si vale la pena separar agentes en Apps cuando haya mediciones de carga, permisos o aislamiento que lo justifiquen. Tampoco se activa Vector Search, Lakebase ni UC Functions por defecto: cada componente opcional debe responder a un caso y tener costo/permiso conocido.

### Organización prevista

```text
harness-repo/
  databricks.yml / resources/ / src/agents/...  # base generada y adaptada
  src/harness/
    intake/          # contrato de HU y validación de entradas
    workflow/        # estados, reintentos, checkpoints e idempotencia
    context/         # extracción de contexto del repo/cliente
    planning/        # plan de cambio y alcance
    execution/       # edición controlada y herramientas
    verification/    # validadores y reporte de evidencias
    integrations/    # git, github, databricks; Genie opcional
    governance/      # políticas, permisos, costos, auditoría
  config/
    defaults/        # agentes, modelos, routing, workflows, límites
    clients/naturapet/  # perfil y reglas del cliente
  prompts/ / tests/ / docs/
```

`databricks.yml` y `app.yaml` pertenecen al despliegue Databricks. Los YAML de `config/` son configuración propia del harness, se validan con un esquema versionado y se interpretan desde Python. Las referencias a secretos serán nombres de recursos del gestor de secretos, nunca valores.

## 4. Contrato mínimo de entrada y salida

**Entrada obligatoria:** ID y título de HU; los cinco bloques; criterios de aceptación; repositorio y rama base; dominio y capa afectados; artefactos esperados; fuentes/tabla de origen y destino; ejemplos o datos de prueba accesibles; clasificación de datos; restricciones de acceso; límites de tiempo/costo. Si falta un dato necesario para cambiar código con seguridad, el flujo se detiene con una lista concreta de ausencias.

**Salida por ejecución:** ID correlativo, commit base exacto, versión del harness/perfil, plan y supuestos, diff, pruebas y resultados, costo estimado/real disponible, recursos consultados, decisión de cada gate y URL del PR. El PR describirá qué cambió, cómo se verificó y qué sigue pendiente de validación humana.

**Estados del flujo:** `recibida → validada → contexto → plan → implementación → pruebas → revisión → PR`, con salidas explícitas `necesita_información`, `bloqueada_por_política`, `presupuesto_agotado` y `fallo_técnico`. Cada paso debe poder reintentarse sin crear otra rama, otro commit o un PR duplicado.

## 5. Agentes y responsabilidades

| Rol | Tipo inicial | Responsabilidad | Salida verificable |
| --- | --- | --- | --- |
| Orquestador | Código determinista | Estados, llamadas, reintentos, límites y gates; nunca decide permisos mediante texto libre del modelo. | Registro de ejecución y decisiones. |
| Analista/planificador | Agente LLM | Contrastar HU con contexto de repo, fuentes y arquitectura; proponer archivos y pruebas. | Plan trazable a criterios de aceptación. |
| Ingeniero Databricks | Agente LLM con herramientas acotadas | Modificar Python, notebooks, YAML DAB y tests en rama de feature. | Diff limitado a rutas permitidas. |
| Revisor independiente | Agente LLM con acceso de lectura | Buscar errores, efectos colaterales, incumplimientos de HU y vacíos de pruebas. | Hallazgos y decisión argumentada. |
| Verificador | Código determinista; LLM solo para explicar fallos | Ejecutar validadores y resumir resultados. | Evidencia reproducible y gate final. |

No crear de inicio un supervisor LLM ni agentes separados para Bronze, Silver, Gold, seguridad y costos. Su especialización se expresará primero mediante contexto, reglas y herramientas por tarea; se divide un rol solo si las pruebas del piloto muestran necesidad.

## 6. Políticas, herramientas y costos

**Routing de modelos.** `models.yaml` contendrá alias lógicos, proveedor/endpoint, capacidad, región, clasificación de datos admitida, límite de contexto y referencia a precios vigentes. `routing.yaml` asignará roles y tareas a alias por reglas deterministas; el fallback necesitará cumplir capacidad, residencia y presupuesto. El modelo nunca puede ampliar por sí mismo la lista de herramientas o permisos.

**Ejecución de herramientas.** Registro con esquemas de entrada/salida, timeout, permisos y auditoría. Primera lista: lectura del repo, edición en rama de trabajo, `git diff/status`, GitHub PR, DAB `validate/plan`, tests Python, lectura de metadatos UC y lectura de documentación local. Las llamadas de SQL/Genie serán de lectura y con límites. Push, PR, escritura en Databricks y ejecución de jobs son capacidades distintas; la política permitirá push/PR al completar gates, mientras despliegue o ejecución de jobs requerirán autorización explícita según las reglas actuales de NaturaPet.

**Costos.** Registrar tokens de entrada/salida, costo estimado por llamada, HU y mes, usando precios versionados y configurables. El MVP no impone tope monetario, por decisión del usuario; se mantienen topes técnicos de duración, iteraciones y tamaño de entrada para evitar ejecuciones accidentales sin fin. Registrar también tiempo/consumo de compute Databricks cuando exista telemetría; tratar ese dato como estimación o reporte diferido si no está disponible en tiempo real.

**Seguridad y aislamiento.** Identidad de servicio de mínimo privilegio; credenciales en secretos del workspace/CI; perfiles separados por cliente; rutas Git, catálogos y schemas permitidos; lectura de datos de muestra con minimización; redactar secretos/PII de prompts, logs y PR. El contenido de HU, repositorio y Genie se trata como datos, no como instrucciones que puedan alterar políticas. Hooks `pre_plan`, `pre_edit`, `pre_tool`, `post_test` y `pre_pr` deben ser deterministas, observables y con fallo cerrado para controles obligatorios.

## 7. Validación y criterios de aceptación

1. **Entrada:** esquema de HU, coherencia origen/destino, criterios comprobables y permisos para consultar muestras.
2. **Cambio local:** formato, lint, importación/sintaxis, tests unitarios y pruebas de contratos; inspección de secretos y rutas prohibidas.
3. **Databricks:** `bundle validate` y `bundle plan` sobre el target de desarrollo, sin `deploy`; validación de referencias a notebooks/jobs y compatibilidad con los contratos de NaturaPet.
4. **Datos:** fixtures sintéticos o anonimizados para Bronze/Silver/Gold, comparaciones de conteos, esquema, nulos, unicidad, reglas de negocio y resultados esperados. Pruebas remotas solo en recursos de desarrollo aislados y con permiso para ejecutar.
5. **Revisión:** revisor independiente comprueba cobertura de la HU, impacto en dominios vecinos, idempotencia, costos y evidencia. Un fallo obligatorio bloquea el PR; advertencias documentadas pueden dejar el PR en borrador, según política.
6. **CI del PR:** agregar validación para PR hacia `develop` en NaturaPet y exigirla como check de rama antes de usar el piloto. El PR debe poder abrirse sin activar el despliegue de `dev`.

Los gates de evaluación de `agentops-stacks` miden calidad del **agente**. Se conservarán y ampliarán con un conjunto de HUs de prueba y trazas MLflow; no reemplazan los tests de calidad del **código y datos** que genere el harness.

## 8. Fases de trabajo y entregables

| Fase | Trabajo concreto | Entregable / puerta de salida |
| --- | --- | --- |
| 0. Contrato y viabilidad | Elegir HU piloto, perfil de permisos, entorno de pruebas, presupuesto, proveedor Git; verificar CLI compatible y autorización para Apps/UC/serving. | Ficha de HU, inventario de recursos y decisiones cerradas. |
| 1. Base aislada | Fijar versión de `agentops-stacks`; generar scaffold **en repositorio del harness** con Azure + GitHub Actions; desactivar recursos opcionales; ajustar hosts/targets propios. | Proyecto generado que instala, pasa tests y valida su bundle sin tocar NaturaPet. |
| 2. Contexto de cliente | Esquema YAML, loader, perfil NaturaPet, inventario de ramas/rutas, convenciones de dominio, catálogos y comandos. | Validación del perfil y reporte de contexto reproducible desde `develop`. |
| 3. Núcleo de ejecución | Contrato HU, estado persistente, orquestador, agentes iniciales, registro de herramientas, aislamiento Git y hooks. | Ensayo local con repo de prueba: rama, edición, pruebas y diff; sin acceso a producción. |
| 4. Gobierno | Modelos permitidos, routing, presupuestos, auditoría, permisos y manejo de secretos. | Pruebas de límites, fallos de política, reintentos e idempotencia. |
| 5. Integración Databricks/NaturaPet | Adaptadores de metadatos, DAB, pruebas del caso piloto; PR de CI hacia `develop` para habilitar checks sin deploy. | Validación en rama de feature y CI aprobada para PR a `develop`. |
| 6. Piloto de punta a punta | Ejecutar HU pequeña, medir precisión/costo/tiempo, revisar diff y abrir PR hacia `develop`. | PR revisable, sin merge ni despliegue; informe de fallos y mejoras. |
| 7. Producto reutilizable | Extraer supuestos NaturaPet, documentar onboarding, versionar paquete/config, probar un segundo perfil sintético o cliente. | Onboarding desde YAML sin modificar núcleo Python; guía de actualización del scaffold. |

Cada fase termina con evidencia antes de avanzar. Los PR de NaturaPet y los cambios de despliegue se preparan para revisión; la aprobación humana decide el merge y cualquier ejecución/despliegue que afecte el workspace.

## 9. Decisiones que faltan para convertir este plan en tareas de implementación

Las cinco decisiones están cerradas por el usuario: HU propuesta; Sonnet 5 para análisis y desarrollo, Haiku 4.5 para verificación, a través de Foundation Model API por token; GitHub App; registro de costos sin tope monetario inicial; pruebas remotas en sandbox aislado. El harness podrá hacer push a `feature/*` y abrir PR, sin merge ni despliegue de NaturaPet.

## 10. Enfoques considerados

- **Recomendado: harness separado desde el inicio, piloto con NaturaPet en rama de feature.** Protege el bundle y la CI existentes, permite versionar la parte genérica y deja un límite claro entre producto y cliente. Requiere diseñar un adaptador de contexto antes del primer PR.
- **Scaffold dentro de NaturaPet y extracción posterior.** Acelera un prototipo local, pero mezcla targets, CI/CD y convenciones UC incompatibles; el push a `develop` despliega. A la luz del código actual, agrega trabajo de separación y riesgo operacional.
- **Harness desde cero sin scaffold.** Da máximo control, pero duplica infraestructura de App, DAB, evaluación y observabilidad ya disponible. Se reserva para componentes que el scaffold no cubre.

La implementación detallada se dividirá, tras revisar este plan, en contratos/configuración, núcleo de flujo, conectores/gobierno y piloto NaturaPet. Cada bloque tendrá archivos exactos, pruebas y criterios de aceptación propios.

## 11. Decisiones confirmadas el 2026-09-25

- Una única Databricks App, con una única interfaz para ingresar manualmente la HU y sus cinco bloques. La misma interfaz mostrará estado, evidencias y URL del PR.
- Harness y perfil NaturaPet en `Demo-Harness-Databricks`, separados del código y bundle del cliente. Rama de trabajo remota: `MVP-Databricks-Harness`, nacida de `main`.
- Nueva App y recursos del harness en paralelo; no modificar recursos actuales de NaturaPet.
- Modelos efectivos confirmados en el workspace: `databricks-claude-sonnet-5` (analista y desarrollo) y `databricks-claude-haiku-4-5` (verificador), mediante Foundation Model API de pago por token. No se usará la API de OpenAI ni endpoint dedicado.
- La captura del calculador de Databricks muestra un escenario artificial de 43.200 llamadas mensuales con 1 token de entrada y 1 de salida por llamada: Sonnet 5 = 7,406 DBU y USD 0,78/mes; Haiku 4.5 = 3,703 DBU y USD 0,39/mes. No es una estimación de una HU real. La telemetría del MVP registrará tokens reales por rol y proyectará costo mensual con una tarifa configurable.
- GitHub App dedicada con `Contents: read/write`, `Pull requests: read/write` y acceso solo al repositorio NaturaPet. La clave privada se guardará fuera de Git, en secretos de Databricks.
- El usuario autorizó pruebas remotas en un sandbox separado y pidió no aplicar límite monetario inicial.
- Flujo automático hasta push de rama de feature y creación de PR. La aprobación, el merge y el despliegue del código de NaturaPet quedan a cargo de una persona.
- Tras desplegar y verificar la App del harness, dejarla en estado `STOPPED`. Incluir un `.bat` de Windows que ejecute `databricks apps start <nombre> --profile CREA_DEV` y abra la URL real obtenida de la App. El CLI `v1.18.0` soporta `apps start` y `apps stop`.
