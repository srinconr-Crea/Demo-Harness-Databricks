# Design

## Context

Ver `proposal.md` para la motivación. `run_story` aplica hoy un gate `analyst` seguido de `developer`, editor determinista, sandbox y `verifier`. `models.py` exige exactamente esos tres roles. `GitHubAppClient` comprueba repositorio, rama base y conjunto de archivos; su ruta de reutilización de rama existente está especializada para un solo archivo. La App guarda contratos JSON por ejecución, intento y llamada. Las pruebas remotas actuales cubren una expresión SQL sintética, no el notebook completo.

## Goals / Non-Goals

**Goals:** introducir una fase de planificación revisable sin ceder al modelo autoridad sobre políticas; inicializar OpenSpec en el workspace del repositorio cliente antes de desarrollar; publicar la inicialización y los artefactos con el código; conservar trazabilidad y costos por llamada e intento; mantener la estrategia y sus controles.

**Non-Goals:** ejecución automática de tareas arbitrarias descritas por un modelo; soporte de nuevas estrategias de edición; merge o despliegue de repositorios cliente; migración de registros históricos; almacenamiento global de especificaciones de todos los clientes en este repositorio.

## Decisions

### 1. Adaptador de CLI con versión fijada

Crear `harness/openspec.py` como único punto de acceso a la CLI. Fijar la versión de `@fission-ai/openspec` usada por el runtime y ejecutar el binario sin shell, con argumentos y directorio explícitos, límite de tiempo, salida acotada y error cerrado. El empaquetado de la App debe instalar Node y esa versión durante la preparación del artefacto, nunca descargarla por historia. La comprobación de arranque y las pruebas de despliegue deben confirmar que `openspec --version` e `instructions`, `status` y `validate --strict` funcionan en el runtime real. Se elige la CLI oficial para conservar sus esquemas y validación; reproducir el formato con un parser propio dejaría de ser OpenSpec interoperable.

### 2. Workspace aislado por intento

Crear un directorio temporal por `run_id` y `attempt_id` que represente el repositorio cliente en el commit base fijado. Leer desde GitHub los archivos OpenSpec existentes, si los hay, y ejecutar siempre `openspec init --tools none` en ese workspace antes de llamar al desarrollador. Si el cliente aún no tiene OpenSpec, generar `openspec/config.yaml` con contexto derivado del perfil y del repositorio cliente; nunca copiar el contexto de este harness. El espacio OpenSpec se delimita por un prefijo confiable obligatorio del perfil. El identificador del cambio se deriva del intento y se sanea para evitar colisiones o traversal. Los archivos de inicialización y planificación se consideran cambios pendientes del mismo PR, sin escribir a la rama base ni publicar antes de superar los gates. Cada artefacto se almacena con hash SHA-256 al terminar.

### 3. Planner guiado por OpenSpec, con contrato estructurado

El orquestador llama `openspec instructions proposal/specs/design/tasks --json` en orden de dependencias y pasa instrucciones, historia, fragmento de fuente limitado y restricciones del perfil al modelo `planner` mediante Foundation Model API. Fijar `routing.planner` a `databricks-claude-sonnet-5`, el endpoint anterior del analista; el perfil y la HU no pueden sustituirlo. El resultado incluye el contenido del artefacto y un manifiesto estructurado con estrategia, expresión y lista de archivos de código previstos. El orquestador valida el manifiesto contra `ClientProfile` y contra el resultado de `editor.parse`; no interpreta texto libre como autorización. Ejecuta `openspec validate <change> --strict` al finalizar. Solo después invoca al desarrollador con los artefactos validados; el verificador recibe esos mismos artefactos, el diff y la evidencia de sandbox. Se evita tratar la CLI como modelo o permitir que el planner aplique cambios directamente.

### 4. Persistencia y contratos compatibles

Ampliar `RunAttempt` con identificador, estado, referencias y hashes del cambio; conservar los campos anteriores como opcionales para leer JSON existentes. Registrar **cada** llamada `planner` a Sonnet 5 mediante el `ModelClient` actual y su callback `save_call`, con `run_id`, `attempt_id`, `call_id`, tokens y costo estimado en `runs/agent_calls/*.json`, incluso si la generación falla. La ausencia de `usage` deja el costo sin valor; nunca se inventa cero. Guardar los documentos completos en un subdirectorio por intento del volumen UC y exponer referencias legibles desde la API de estado con las mismas ACL del registro. La configuración de modelos cambia a `planner/developer/verifier`; la lectura de llamadas históricas con rol `analyst` permanece válida. No se modifican registros antiguos.

### 5. Publicación en el cliente

Agregar al perfil un prefijo OpenSpec obligatorio y separado de `allowed_paths` para código. Mantener `feature/*` y la rama base del perfil. Construir la lista exacta de archivos validados (código + inicialización + configuración + artefactos OpenSpec) y validar cada ruta contra su política. Extender `GitHubAppClient` para crear un solo commit Git con el conjunto completo, verificar base y archivos en una rama reutilizada, y registrar cualquier progreso de publicación. Después de implementar y verificar, archivar el cambio OpenSpec en el workspace temporal antes de preparar los archivos del PR; incluir tanto el archivo histórico como las specs resultantes. La PR seguirá requiriendo revisión humana. Este diseño evita que los documentos amplíen la lista de archivos permitidos.

### 6. Pruebas y despliegue gradual

Probar el adaptador con una CLI fijada y workspaces temporales; probar fallos de timeout, validación, rutas, manifiesto, salida del modelo y reutilización de ramas. Ejecutar la suite local y `databricks bundle validate` tras cambiar el empaquetado. Hacer una prueba sintética en un perfil aislado que carezca de OpenSpec para verificar que `init` ocurre antes del desarrollador y que el PR lleva inicialización, artefactos y código. Mantener cerrada la publicación cuando la CLI o el prefijo OpenSpec del perfil no estén disponibles.

## Risks / Trade-offs

- **Dependencia Node en Databricks Apps** → instalarla durante build, verificar en el runtime de desarrollo y fallar al iniciar o antes de ejecutar si falta; no recurrir a descargas dinámicas.
- **Artefactos correctos estructuralmente pero falsos semánticamente** → manifiesto determinista, editor y sandbox independientes, verificador contra specs y revisión humana del PR. La validación CLI solo demuestra formato y consistencia estructural.
- **Costo y latencia de cuatro artefactos** → límites de entrada/salida, tiempos máximos y registro de tokens/costo por llamada; no ampliar modelos desde la historia.
- **Datos sensibles en documentos** → mismas reglas de redacción, ACL y retención que los registros existentes; no incluir secretos en contexto ni artefactos.
- **Publicación de varios archivos** → commit único, comparación exacta contra la base validada y rechazo de ramas divergentes.

## Migration Plan

1. Incorporar el adaptador, almacenamiento y contratos compatibles; añadir el prefijo OpenSpec a los perfiles cliente confiables.
2. Sustituir el rol interno y ejecutar pruebas locales completas; verificar la CLI fijada y el bundle en el entorno de desarrollo.
3. Probar una historia sintética aislada con un repositorio cliente sin OpenSpec y revisar inicialización previa al desarrollo, artefactos, hashes, llamadas Sonnet 5, costos y rechazo de políticas.
4. Comprobar un PR `feature/*` con código y OpenSpec en el repositorio de prueba, sin merge ni cambio de la rama base.
5. Si la fase nueva falla en despliegue, retirar su activación y volver a la revisión manual previa; conservar registros y ramas creadas para diagnóstico, sin presentarlas como aprobadas.
