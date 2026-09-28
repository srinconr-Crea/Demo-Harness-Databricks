# Roles dentro de la App

Los tres roles son llamadas a Foundation Model API desde la misma App FastAPI, no Apps ni identidades independientes. Sus instrucciones y límites de texto están en `config/defaults/agents.yaml`; el enrutamiento de modelos está en `config/defaults/models.yaml`.

| Rol | Entrada | Salida validada | Autoridad |
| --- | --- | --- | --- |
| Analista | HU, ruta permitida y fragmento del notebook | `valid`, `notes`, `evidence` | Puede rechazar el alcance; no edita |
| Desarrollador | HU, expresión calculada por reglas y código fuente | `expression`, `notes` | Propone; el editor determinista escribe |
| Verificador | HU, diff y resultado de sandbox | `approved`, `notes`, `findings` | Puede rechazar la publicación |

El orquestador valida JSON con Pydantic y comprueba por código la estrategia, la expresión, el archivo y la prueba de sandbox. Cualquier salida inválida falla antes de publicar. El cliente GitHub App crea la rama y el PR solamente después de los gates. La identidad de servicio de la App opera recursos configurados; la acción opcional de detenerla usa el token del usuario con permiso `CAN MANAGE`.

Las llamadas guardan `run_id`, `attempt_id`, `call_id`, entrada, salida, tiempos, tokens y costo estimado en el volumen UC. La salida estructurada se guarda cuando cumple el esquema. El rol no tiene herramientas para ampliar políticas a partir de texto de la HU o del repositorio.
