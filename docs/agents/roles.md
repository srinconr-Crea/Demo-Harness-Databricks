# Roles dentro de la App

Los tres roles son llamadas a Foundation Model API desde la misma App FastAPI, no Apps ni identidades independientes. Sus instrucciones y límites de texto están en `config/defaults/agents.yaml`; el enrutamiento de modelos está en `config/defaults/models.yaml`.

| Rol | Entrada | Salida validada | Autoridad |
| --- | --- | --- | --- |
| Planner OpenSpec | HU, contexto del cliente, estrategia, expresión y fuente | `content`, `strategy`, `code_path`, `expression` por artefacto | Usa Sonnet 5 para propuesta, spec, diseño y tareas; no edita código |
| Desarrollador | HU, plan OpenSpec validado, expresión calculada por reglas y código fuente | `expression`, `notes` | Propone; el editor determinista escribe |
| Verificador | HU, plan OpenSpec, diff y resultado de sandbox | `approved`, `notes`, `findings` | Puede rechazar la publicación |

El orquestador inicializa OpenSpec en un workspace temporal del repositorio cliente antes de llamar al desarrollador. Valida JSON con Pydantic, ejecuta `openspec validate --strict` y comprueba por código la estrategia, la expresión, el archivo y la prueba de sandbox. Tras la aprobación del verificador, archiva el cambio y publica notebook y archivos OpenSpec en un mismo commit de la rama `feature/*`. La identidad de servicio de la App opera recursos configurados; la acción opcional de detenerla usa el token del usuario con permiso `CAN MANAGE`.

Las cuatro llamadas del planner a `databricks-claude-sonnet-5` guardan `run_id`, `attempt_id`, `call_id`, entrada, salida, tiempos, tokens y costo estimado en los mismos JSON del volumen UC que los demás roles. Los registros históricos con rol `analyst` siguen legibles. Los artefactos redactados se guardan por intento bajo `runs/openspec/`. Ningún rol puede ampliar políticas a partir de texto de la HU o del repositorio.
