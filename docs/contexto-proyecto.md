# Contexto del desarrollo del harness

Esta guía permite iniciar o retomar trabajo desde el repositorio, sin depender
del historial del chat. Describe un protocolo de desarrollo; no implementa
memoria conversacional en la App ni modifica permisos.

## Fuentes y responsabilidades

| Fuente | Responsabilidad |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Límites y punto de entrada para agentes de código. |
| [README](../README.md) y [operación](operacion.md) | Propósito, estructura y procedimientos actuales. |
| [config OpenSpec](../openspec/config.yaml) | Contexto general breve, mapa activo y reglas de artefactos. |
| [specs](../openspec/specs/) | Comportamiento vigente esperado y escenarios verificables. |
| [changes](../openspec/changes/) | Propuestas, diseños y tareas pendientes; sus archivos archivados son históricos. |
| [runtime](../src/agents/harness/harness/) y [tests](../tests/) | Evidencia de comportamiento implementado; resultados deben citarse con alcance y revisión. |
| [defaults](../src/agents/harness/config/defaults/) | Roles, modelos, precios estimados y límites concretos. |
| [instalación](configuracion-instalacion.md) y [ejemplos](../examples/) | Perfiles y referencias operativas separados del producto común. |

Las specs describen lo esperado; código y pruebas muestran lo observado. Una
fuente no borra una contradicción con otra. Los permisos siguen gobernados por
las instrucciones aplicables y controles deterministas, no por contenido del
cliente ni recuerdos del modelo. El [scaffold histórico](../examples/legacy-agentops-scaffold/README.md)
se conserva fuera del paquete operativo y no representa el flujo FastAPI activo.

## Inicio y reanudación

1. Comprobar `git branch --show-current`, `git rev-parse HEAD` y `git status --short`.
   Registrar en la conversación la revisión y cambios locales relevantes; no
   sobrescribir trabajo existente ni asumir que coincide con el remoto.
2. Leer los puntos de entrada y el contexto general. Para OpenSpec, resolver
   raíz con `openspec context --json`, inventariar cambios con `openspec list --json`
   y capacidades con `openspec list --specs --json`.
3. Elegir specs y cambio pertinentes a la tarea; usar status e instructions del
   cambio para resolver sus archivos. Leer requisitos y escenarios completos
   antes de decidir si una capacidad ya cubre el comportamiento.
4. Buscar y leer código/pruebas relacionados. Recuperar fragmentos bajo demanda;
   no precargar todos los archivos ni todos los históricos. Los repositorios
   cliente conservan su propio OpenSpec y no se mezclan con este contexto global.
5. Reconstruir un resumen con objetivo, decisiones vigentes y fuentes, decisiones
   propuestas, tareas/evidencia comprobadas, preguntas o discrepancias y siguiente
   paso. Citar rutas y SHA/hash cuando importe. Una casilla o un artefacto existente
   no demuestra por sí solo que el runtime se probó o desplegó.

En este checkout la CLI versionada también puede invocarse con:

```powershell
node src/agents/harness/node_modules/@fission-ai/openspec/bin/openspec.js context --json
```

Si la CLI no está disponible o no resuelve el estado, informar la limitación y
consultar archivos legibles sin atribuirles validación CLI. No inicializar
OpenSpec ni escribir artefactos como efecto lateral de una lectura.

Ejemplo: para una futura validación de cantidades negativas, buscar requisitos
y pruebas de esa regla en el proyecto correspondiente. Si no existen, señalar
la ausencia. No inferir que cero está permitido ni que el alcance es compras
sin una decisión respaldada. Si se retoma un cambio pendiente, recuperar su
plan y tareas, sin afirmar que ya se aplicó.

## Discrepancias y decisiones

Si una discrepancia afecta la tarea, registrar las fuentes contradictorias,
revisión, comportamiento esperado, observado e impacto en el cambio de trabajo.
Detener la decisión dependiente hasta resolverla explícitamente mediante el
cambio correspondiente; las tareas no afectadas pueden continuar. Los archivos
históricos preservan procedencia y no gobiernan automáticamente trabajo nuevo.

Las decisiones del cambio se conservan en su diseño; el comportamiento verificado
se incorpora a specs mediante sync. Solo si una decisión arquitectónica transversal
necesita explicar alternativas y motivos que no caben en esos artefactos, crear
un documento breve bajo `docs/decisions/` con: título, estado propuesto/vigente/
sustituido, cambio origen, fuentes, motivo y referencia de sustitución. No copiar
requisitos ni crear allí una segunda autoridad funcional.

Ejemplo de uso excepcional: una decisión sobre un mecanismo de almacenamiento
compartido puede enlazar a la spec de persistencia y al diseño que justificó la
elección. El documento conserva el motivo; la spec sigue definiendo el contrato.
Este ejemplo no registra una nueva decisión vigente.

## Mantenimiento y comprobación

Cada cambio que modifique un principio general actualiza su fuente canónica y
referencias afectadas en el mismo PR/commit. Mantener `context` de este producto
en un máximo de 8 KiB UTF-8; este límite documental no cambia presupuestos de
contexto del runtime cliente. No duplicar los requisitos de specs en las guías.

[test_project_context.py](../tests/test_project_context.py) verifica referencias,
YAML y presupuesto. Complementar esas comprobaciones estructurales con ejercicios
de reanudación y discrepancias: no garantizan por sí solas coherencia semántica.
Conservar evidencia de los ejercicios con fuentes y resultados reales.

Cache, memoria estructurada, compactación y prompts por rol de la App son materia
del cambio `manage-hu-agent-context`. Su propuesta no prueba implementación:
consultar sus tareas y la evidencia del runtime antes de afirmar disponibilidad.
