# Roles de la conversación OpenSpec

La App FastAPI coordina las llamadas mediante Databricks Foundation Model API. Los roles comparten la identidad de la App; el Job de pruebas usa una identidad de servicio separada. El enrutamiento está en `src/agents/harness/config/defaults/models.yaml` y los límites de texto en `src/agents/harness/config/defaults/agents.yaml`.

| Rol | Momento | Responsabilidad |
| --- | --- | --- |
| Explorador | `explore` | Resume la HU y pide aclaraciones cuando faltan datos. Usa Sonnet 5. |
| Planner | `propose` / `update` | Escribe proposal, specs, design y tasks siguiendo las instrucciones del esquema OpenSpec del cliente. Usa Sonnet 5. |
| Desarrollador | `apply` | Propone operaciones de archivo tipadas o confirma la expresión de `silver_safe_ratio`. Solo el aplicador de la App escribe dentro de la política del perfil. |
| Verificador OpenSpec | `verify` | Confronta specs, tareas, diff y evidencia de pruebas. Usa Sonnet 5. |
| Verificador independiente | `verify` | Revisa el resultado con el modelo de revisión configurado, actualmente Haiku 4.5. |

OpenSpec se prepara una sola vez por cliente en un PR separado. Cada HU clona el repositorio preparado, espera aprobación del plan, aplica código, ejecuta las pruebas configuradas y solicita aprobación del diff final antes de crear un PR. El PR y su merge se revisan en GitHub por una persona. La HU y la salida de modelos son datos no confiables y no amplían rutas, modelos, permisos ni validadores.

Cada invocación guarda `run_id`, `attempt_id`, `call_id`, rol, etapa, revisión, modelo, tiempos, tokens, estado y costo estimado si hubo `usage`. Un fallo o una respuesta sin `usage` conserva el costo ausente. Los JSON históricos siguen legibles.
