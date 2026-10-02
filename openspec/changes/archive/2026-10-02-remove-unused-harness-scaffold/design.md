# Design

## Context

Ver proposal.md para objetivo. Inspección en SHA 487eff3626b08296aff72016763cc37cae75337a: app.yaml y databricks.yml arrancan app/start_server.py, que importa harness/ y no agent.py/graph.py/tools.py/app/utils.py. CI ejecuta tests del producto y PySpark sintético, sin eval genérico. pyproject.toml separa grupo eval de dependencias runtime/dev/spark-validation. harness/evaluation.py y tests/test_evaluation.py calculan métricas reales y deben conservarse.

resources/uc_function_registration.yml no está incluido y referencia src/components/tools/registry.py ausente. src/components/eval/scorers.py y eval/ contienen registro/evaluación genéricos. resources/experiment.yml sí está incluido y puede tener bindings desplegados: no es seguro equiparar falta de imports con recurso eliminable. prepare_installation.py empaqueta src/agents, resources y scripts desde Git; trasladar ejemplos fuera de esas raíces permite excluirlos sin editar el runtime.

## Goals / Non-Goals

**Goals:** superficie operativa con componentes usados, ejemplos legibles fuera de distribución, dependencias coherentes y pruebas de equivalencia funcional.

**Non-Goals:** eliminar ejemplos/documentación/procedencia, borrar estado local o remoto, cambiar endpoints/modelos/seguridad, retirar recursos desplegados o implementar gestor de contexto. No reemplazar pruebas reales por gates genéricos.

## Decisions

### 1. Inventario acotado y conservación

| Origen | Acción propuesta | Evidencia/motivo |
| --- | --- | --- |
| src/agents/harness/agent.py, graph.py, tools.py | Trasladar a examples/legacy-agentops-scaffold/agent/ | Cadena AgentServer/LangGraph aislada del arranque FastAPI |
| src/agents/harness/app/utils.py | Trasladar a examples/legacy-agentops-scaffold/agent/app/utils.py | Consumidor observado: agent.py, no servidor vigente |
| src/agents/harness/eval/create_dataset.py, evaluate_agent.py, gates.yml, utils.py | Trasladar a examples/legacy-agentops-scaffold/agent/eval/ | Evaluación genérica y dataset placeholder, fuera de CI real |
| src/components/eval/scorers.py | Trasladar a examples/legacy-agentops-scaffold/components/eval/scorers.py | Scorers del scaffold sin consumo en flujo activo |
| resources/uc_function_registration.yml | Trasladar a examples/legacy-agentops-scaffold/resources/ | Stub no incluido, registry ausente, nunca ejecutarlo como operación |
| pyproject.toml grupo eval y uv.lock | Retirar grupo del producto y regenerar lock | Consumidores preservados exclusivamente como ejemplos |
| src/agents/harness/.env.example | Actualizar ejemplo vigente; conservar variables del scaffold en ejemplo histórico | No borrar ejemplos ni sugerir selección de modelos por LLM_ENDPOINT del scaffold |
| .agentops-stacks/manifest.yml | Conservar bytes | Procedencia de generación, no configuración viva |
| resources/experiment.yml y restantes includes/bindings | Conservar | Recursos actuales incluidos, retiro requiere cambio separado |
| harness/, app vigente, scripts, tests, defaults, OpenSpec/skills | Conservar | Superficie operativa, controles y herramientas necesarias |
| docs/, examples/ existentes e históricos OpenSpec | Conservar | Documentación, evidencia y ejemplos solicitados |

Este inventario es el alcance de traslados, no una lista de borrado recursivo. Revalidar referencias concretas en el SHA de apply, incluidas imports dinámicas, comandos CI y paquetes. Si aparece consumidor activo de un candidato, conservarlo y registrar discrepancia antes de la eliminación dependiente. No ampliar eliminaciones a módulos de harness/ por una búsqueda sin resultados: API, pruebas o procedimientos pueden ser consumidores.

Alternativa descartada: borrar todo lo nombrado agentops/eval. Perdería ejemplos/procedencia y eliminaría harness/evaluation.py funcional por semejanza de nombre.

### 2. Ejemplos históricos aislados

Trasladar referencias reutilizables conservando estructura relativa de agent/app/eval; agregar README que declare origen, SHA, carácter histórico, prerrequisitos y que no son entradas soportadas del producto. Mantener dependencias opcionales documentadas o en configuración propia del ejemplo, nunca en el pyproject del producto. El YAML UC referencia código ausente: indicarlo explícitamente, no fabricar registry ni presentarlo como ejecutable validado.

Conservar todo ejemplo existente. No duplicar scaffold dentro del árbol operativo ni empaquetarlo mediante prepare_installation o sync. No ejecutar notebooks heredados para verificar traslados: sus comandos registran objetos y usan modelos/servicios; validar estructura/referencias locales solamente. El ejemplo histórico no tiene garantía de ejecución ni habilita permisos.

### 3. Dependencias y empaquetado

Quitar únicamente el grupo eval exclusivo del scaffold y regenerar uv.lock con herramientas declaradas. Mantener dev, spark-validation y dependencias transitivas requeridas por runtime; no editar lock a mano ni retirar un paquete solo por ausencia de import directo. package.json/package-lock mantienen CLI OpenSpec. No borrar .venv/node_modules/.deployments/.runs ni caches locales.

Preparar instalación sintética con scripts/prepare_installation.py y comprobar entrypoints/config/perfil/hash, incluidos runner sandbox y CLI. Verificar que ningún archivo trasladado entra al paquete y que no se crean referencias rotas. databricks.yml no requiere edición prevista: mantener includes, identidad sandbox, permisos y bindings. Si una edición de bundle resulta necesaria, revisar alcance y ejecutar bundle validate estricto, sin deploy.

### 4. Documentación y procedencia

Actualizar referencias actuales en README, AGENTS.md, docs/contexto-proyecto.md, openspec/config.yaml y guías afectadas para localizar runtime y ejemplo histórico. Mantener context <=8 KiB. Conservar docs/setup.md y docs/supervisor-patterns.md, identificados como históricos, con enlaces a ejemplo/operación vigente donde corresponda. No reescribir evidencia antigua ni archives para simular que tenían la estructura nueva; documentar el mapa de rutas anteriores a nuevas y el SHA de origen en el README del ejemplo.

Las specs principales conservan comportamiento: skip_specs es deliberado. La documentación de operación referencia capacidades vigentes sin afirmar que manage-hu-agent-context ya está implementado.

### 5. Verificación de equivalencia

Pruebas existentes relevantes: instalación/cliente, conversación/webapp, publicación/recovery, repository workflow, skills/CLI real, sandbox/job, PySpark y evaluation. Ejecutar suite completa; añadir solo comprobaciones de empaquetado/imports necesarias para la regresión del traslado y validar enlaces afectados. Verificar arranque FastAPI con perfil sintético y conectores stub, evitando autenticación real en pruebas locales.

Registrar baseline y resultado posterior en el mismo entorno, con fixture idéntico de HU hasta PR simulado y recuperación en espera; comparar estados, autorizaciones, contratos/costos, archivos del paquete y configuración. Preservar las dos estrategias: general_patch y silver_safe_ratio. Un problema de permisos de temporales no demuestra fallo funcional ni aprobación de pruebas: resolver en ruta temporal autorizada o registrar verificación pendiente.

No desplegar para una limpieza. Antes de publicar exigir suite y lint pertinentes; validación bundle solo si se modifica configuración de bundle. No crear recursos ni ejecutar eval/scorers genéricos. El smoke remoto eventual necesita alcance explícito demo_harness, sin tocar NaturaPet.

## Risks / Trade-offs

- [Import dinámico o consumidor operacional oculto] -> revalidación de referencias/entrypoints, paquete y arranque stub; conservar ante consumidor activo.
- [Eliminar experimento rompe binding o destruye evidencia] -> recurso incluido permanece, retiro fuera de alcance.
- [Ejemplo heredado parece procedimiento vigente] -> README explícito, ubicación separada y guías con enlaces vigentes.
- [Regenerar lock cambia dependencias innecesariamente] -> revisar diff/instalación congelada y conservar grupos/runtime requeridos.
- [Cambio de contexto concurrente] -> revalidar SHA antes de apply sin asumir orden de implementación.
- [Traslado rompe enlaces históricos] -> mapa de rutas/origen y actualización de referencias actuales, sin borrar evidencia.

## Migration Plan

### Autorización de entrega de esta sesión (2026-10-02)

El usuario pidió aplicar, sincronizar, archivar, actualizar la App existente y
publicar directamente en `Db_Spec_Harness`, con perfil CLI `CREA_DEV` elegido
explícitamente. Esta instrucción sustituye para esta entrega del producto la
recomendación de PR feature y la exclusión de despliegue de la planificación
original. Se actualizará únicamente el código de la App del harness, conservando
perfil, política de contexto habilitada de la instalación y bindings. Merge,
destrucción y modificaciones de recursos cliente permanecen fuera de alcance.

El baseline de lint detectó 35 errores previos; el usuario autorizó corregirlos
y verificar regresiones. Los ajustes conservan contratos de excepción externos,
ordenan imports y simplifican condiciones equivalentes; las pruebas eliminan
variables sin uso, hacen explícito check=False y fijan variables de closures.
No se amplía la limpieza a módulos funcionales ni se inventan deltas de specs.

1. Baseline de suite/paquete y revisión concreta de candidatos.
2. Traslados acotados a ejemplos, dependencias y referencias coherentes en un mismo candidato Git.
3. Suite completa, lint, empaquetado/arranque y flujo sintético positivo/negativo con evidencia real.
4. PR feature con manifiesto antes/después; merge y despliegue humanos. Esta planificación no crea PR ni despliega.
5. Rollback mediante revert del cambio versionado: restaurar rutas/dependencias/referencias, sin borrar estado ni recrear recursos. Paquetes previos conservan su revisión independiente.
