# Roles de la conversación OpenSpec

Las skills se generan manualmente en el repositorio cliente con `init --tools agents`, se revisan por PR y se integran antes de usar la App. Cada rol recibe su skill versionada y un contrato JSON mediado por el Harness; los workflows e instrucciones CLI se combinan según [el mapa de fases](../repository-workflow.md). allowed-tools no habilita herramientas y las skills no seleccionan modelos ni aprobaciones. Se registra procedencia por llamada, incluida cada ronda contextual y fallos; sync/archive conservan ejecución determinista y eventos sin costos ficticios.

La App FastAPI coordina las llamadas mediante Databricks Foundation Model API. Los roles comparten la identidad de la App; el Job de pruebas usa una identidad de servicio separada. El enrutamiento está en `src/agents/harness/config/defaults/models.yaml` y los límites de texto en `src/agents/harness/config/defaults/agents.yaml`.

| Rol | Momento | Responsabilidad |
| --- | --- | --- |
| Explorador | `explore` | Resume la HU y pide aclaraciones cuando faltan datos. Usa Sonnet 5. |
| Planner | `propose` / `update` | Escribe proposal, specs, design y tasks siguiendo las instrucciones del esquema OpenSpec del cliente. Usa Sonnet 5. |
| Desarrollador | `apply` / etapa `correcting` | Propone operaciones de archivo tipadas y cobertura por entrada del manifiesto, o confirma la expresión de `silver_safe_ratio`. Solo el aplicador de la App escribe dentro de la política del perfil. Una corrección conserva el plan aprobado. |
| Verificador OpenSpec | `verify` | Confronta specs, tareas, diff acumulado y evidencia vigente de pruebas; propone hallazgos clasificados con criterio, evidencia y operaciones necesarias. Usa Sonnet 5. |
| Verificador independiente | `verify` | Haiku 4.5 revisa como asesor. Sus recomendaciones, rechazo o fallo se registran sin bloquear ni consumir correcciones. |

OpenSpec se prepara una sola vez por cliente en un PR separado. Cada HU nueva clona el repositorio preparado y espera aprobación del plan, manifiesto y pruebas previstas; después aplica, verifica con Sonnet/pruebas obligatorios, sincroniza, archiva y crea automáticamente el PR. El diff queda consultable; el PR y su merge se revisan en GitHub por una persona. Los históricos conservan su aprobación original. La HU y las salidas de modelos no amplían permisos. Véase [contratos y presupuestos](../repository-workflow.md) para las solicitudes tipadas de contexto y operaciones por estrategia.

Developer y Sonnet reciben el contrato aprobado completo, notas y bloqueos,
lecturas pertinentes con ruta/hash/origen y pruebas vinculadas al candidato. El
verificador puede pedir lecturas autorizadas bajo los mismos presupuestos; no
recibe shell ni escrituras. Las notas se conservan como afirmaciones, sin
convertirse en pruebas ni decisiones humanas. Cobertura `already_conformant`
requiere el hash actual comprobado; una lista vacía de operaciones sin cobertura
completa no demuestra que el trabajo esté terminado.

Un hallazgo `implementation` solo permite `correcting` tras la comprobación
determinista de plan, perfil, manifiesto y evidencia. Después se repiten pruebas
y Sonnet sobre el candidato actual. `scope_spec` exige `update` y aprobación
nueva; hallazgos mixtos que cambian el contrato bloquean reparaciones dependientes.
`infrastructure_evidence` permite recuperación acotada o diagnóstico bloqueante;
`harness_defect` detiene el intento sin llamadas de reparación al cliente.
Clasificaciones ambiguas y contratos inválidos no habilitan corrección permisiva.
Hay como máximo dos correcciones automáticas de implementación por intento,
compartidas entre pruebas y Sonnet, sin reinicio del contador por update o
reinicio del proceso. Repetir un bloqueo sin progreso pertinente detiene otra
llamada equivalente. Haiku mantiene su invocación asesora y no consume este
presupuesto. Véase [operación](../operacion.md) para recuperación y compatibilidad.

Cada invocación guarda `run_id`, `attempt_id`, `call_id`, rol, etapa, revisión, modelo, tiempos, tokens, estado y costo estimado si hubo `usage`. Las llamadas de corrección conservan la fase `apply`, etapa `correcting` y procedencia del candidato. Un fallo o una respuesta sin `usage` conserva el costo ausente. Los JSON históricos siguen legibles.
