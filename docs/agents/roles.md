# Roles de la conversación OpenSpec

La App FastAPI coordina las llamadas mediante Databricks Foundation Model API. Los roles comparten la identidad de la App; el Job de pruebas usa una identidad de servicio separada. El enrutamiento está en `src/agents/harness/config/defaults/models.yaml` y los límites de texto en `src/agents/harness/config/defaults/agents.yaml`.

| Rol | Momento | Responsabilidad |
| --- | --- | --- |
| Explorador | `explore` | Resume la HU y pide aclaraciones cuando faltan datos. Usa Sonnet 5. |
| Planner | `propose` / `update` | Escribe proposal, specs, design y tasks siguiendo las instrucciones del esquema OpenSpec del cliente. Usa Sonnet 5. |
| Desarrollador | `apply` | Propone operaciones de archivo tipadas o confirma la expresión de `silver_safe_ratio`. Solo el aplicador de la App escribe dentro de la política del perfil. |
| Verificador OpenSpec | `verify` | Confronta specs, tareas, diff y evidencia de pruebas. Usa Sonnet 5. |
| Verificador independiente | `verify` | Haiku 4.5 revisa como asesor. Sus recomendaciones, rechazo o fallo se registran sin bloquear ni consumir correcciones. |

OpenSpec se prepara una sola vez por cliente en un PR separado. Cada HU nueva clona el repositorio preparado y espera aprobación del plan, manifiesto y pruebas previstas; después aplica, verifica con Sonnet/pruebas obligatorios, sincroniza, archiva y crea automáticamente el PR. El diff queda consultable; el PR y su merge se revisan en GitHub por una persona. Los históricos conservan su aprobación original. La HU y las salidas de modelos no amplían permisos. Véase [contratos y presupuestos](../repository-workflow.md) para las solicitudes tipadas de contexto y operaciones por estrategia.

Cada invocación guarda `run_id`, `attempt_id`, `call_id`, rol, etapa, revisión, modelo, tiempos, tokens, estado y costo estimado si hubo `usage`. Un fallo o una respuesta sin `usage` conserva el costo ausente. Los JSON históricos siguen legibles.
