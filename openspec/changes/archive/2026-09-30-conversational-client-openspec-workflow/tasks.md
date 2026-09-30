# Tasks

## 1. Contratos y persistencia de la conversación

- [x] 1.1 Versionar los contratos de HU (`hu`, `description`), intento, etapa, revisión, evento y aprobación en `contracts.py`; verificar validación de entradas y lectura de registros v3 con pruebas de contratos.
- [x] 1.2 Crear un almacén canónico de checkpoints en el volumen UC para manifiesto y bytes exactos del borrador, separado de los JSON redactados; verificar restauración, huellas, archivos eliminados y rechazo de un checkpoint alterado en pruebas de `store.py`.
- [x] 1.3 Añadir en el catálogo aislado del harness la tabla Delta de coordinación de estado, versión, lease e idempotencia, con permisos mínimos en el bundle; verificar transiciones concurrentes y que un lease vencido se recupere una sola vez en pruebas de integración.
- [x] 1.4 Extender el almacenamiento de eventos y llamadas con etapa/revisión/hash aprobado sin romper consultas históricas de costos; verificar la unión por `run_id` y `attempt_id`, el costo ausente sin `usage` y la lectura de JSON previos.
- [x] 1.5 Documentar en `docs/operacion.md` la retención, ACL, recuperación y migración de registros/checkpoints; verificar que los ejemplos coinciden con los contratos versionados.

## 2. Checkout y preparación única del cliente

- [x] 2.1 Añadir al cliente GitHub App un checkout completo del repositorio y SHA base autorizados, con credencial temporal fuera de URL, argumentos, configuración Git y logs; verificar repo/SHA correctos y ausencia del token en trazas mediante pruebas con Git local simulado.
- [x] 2.2 Implementar la operación de incorporación que ejecuta OpenSpec `init` una vez y prepara solo su configuración en una rama `feature/*` y PR de preparación; verificar que no incluye código de HU y que nunca escribe en la rama base.
- [x] 2.3 Reemplazar `prepare_client_workspace` por comprobación de OpenSpec ya versionado en la base; verificar que una HU de cliente preparado no llama a `init` y una HU sin configuración se detiene antes del planner.
- [x] 2.4 Restaurar el checkout desde SHA base y checkpoint con límites de archivos/tamaño y rechazo de enlaces fuera del checkout; verificar recuperación tras reinicio y fallo cerrado con contenido alterado.
- [x] 2.5 Documentar en `README.md` y `docs/operacion.md` el PR de preparación, la espera de merge humano y el ciclo de checkout; verificar los comandos y estados descritos con una prueba de cliente sintético.

## 3. Orquestación OpenSpec y roles

- [x] 3.1 Separar `workflow.run_story` en tramos reanudables para `explore`, `propose`, `update`, `apply`, `verify`, `sync` y `archive`; verificar transiciones, espera sin ocupar trabajador y reanudación con checkpoint en pruebas de flujo.
- [x] 3.2 Implementar preguntas de `explore` y generación/actualización de proposal, specs, design y tasks según instrucciones del esquema, con validación estricta y versiones; verificar aclaraciones, artefactos inválidos y aprobación obsoleta en pruebas OpenSpec.
- [x] 3.3 Enrutar todas las llamadas que ejecutan flujos OpenSpec a `databricks-claude-sonnet-5`, llamar al desarrollador durante `apply` y mantener la revisión independiente configurada; verificar modelo, rol, etapa, errores, tokens y costo de cada llamada JSON.
- [x] 3.4 Contrastar `verify` con los specs, resultados de pruebas y diff; permitir un ciclo `update`/`apply` limitado cuando haya hallazgos; verificar que un resultado inconcluso no permite revisión final.
- [x] 3.5 Actualizar `openspec/config.yaml`, `docs/agents/roles.md` y la guía de operación con el ciclo real, modelos y responsabilidades; verificar que no describen inicialización por HU ni expresión única como contrato general.

## 4. Edición general y pruebas aisladas

- [x] 4.1 Añadir `general_patch` al perfil y al registro de estrategias con allowlist de rutas, extensiones, operaciones, límites y validadores; verificar rechazo de configuraciones ausentes o ampliadas desde la HU.
- [x] 4.2 Implementar el aplicador de operaciones de archivo tipadas y comparación final contra la base, conservando el editor `silver_safe_ratio`; verificar creación, modificación, borrado admitido y rechazo de traversal, `.github/`, enlaces y binarios no admitidos.
- [x] 4.3 Configurar adaptadores de pruebas confiables por perfil y ejecutarlos en un sandbox sin secretos de la App, con tiempo y recursos limitados; verificar rechazo de comandos pedidos por el repo y ausencia de credenciales en el entorno de pruebas.
- [x] 4.4 Integrar validación de sintaxis/estructura y evidencia de pruebas en `verify`; verificar que un tipo de HU sin comprobación obligatoria queda como no verificado y no puede publicarse.
- [x] 4.5 Documentar en los perfiles de ejemplo y `docs/operacion.md` cómo habilitar un tipo de cambio general y sus pruebas; verificar que el ejemplo sintético pasa y que `silver_safe_ratio` conserva sus pruebas existentes.

## 5. API y experiencia conversacional

- [x] 5.1 Cambiar `/run` a HU y descripción, generar identidad interna y añadir endpoints de mensajes, eventos paginados y acciones por estado con revisión esperada; verificar entradas, autorización, idempotencia y decisiones atrasadas con pruebas FastAPI.
- [x] 5.2 Implementar estados `awaiting_clarification`, `awaiting_plan_review` y `awaiting_diff_review` persistentes; verificar que el reinicio conserva la espera, los artefactos y la identidad de quien responde.
- [x] 5.3 Reemplazar el formulario de siete campos por dos campos y una vista de conversación con progreso incremental, artefactos, pruebas, modelo/costo y diff; verificar el flujo completo de aclaración y revisión en prueba de interfaz.
- [x] 5.4 Añadir controles de aprobar, pedir cambios y cancelar válidos para cada etapa; verificar que la UI invalida aprobaciones anteriores, muestra errores y no interpreta HTML de la HU o del modelo.
- [x] 5.5 Actualizar `README.md` y `docs/operacion.md` con estados, acciones y recuperación de la App; verificar las respuestas JSON y capturas del flujo en un entorno de prueba.

## 6. Candidato final y publicación

- [x] 6.1 Ejecutar `sync` y `archive` en el checkout candidato antes de mostrar el diff final, conservando un checkpoint previo a correcciones; verificar que el diff incluye código, specs e historial del cambio.
- [x] 6.2 Calcular un hash del SHA base y del conjunto ordenado de archivos exactos, vincularlo a la aprobación humana y comprobarlo otra vez al publicar; verificar rechazo de archivos cambiados o aprobación de otra revisión.
- [x] 6.3 Comprobar la cabeza remota de la base antes de crear rama y PR; verificar que una base avanzada invalida el candidato y exige nueva validación y aprobación.
- [x] 6.4 Hacer idempotente la creación/reutilización de `feature/*` y PR tras reinicios, sin merge ni despliegue; verificar coincidencia del diff remoto completo y preservación de rama/commit/URL si falla una etapa posterior.
- [x] 6.5 Documentar la revisión del PR y el estado real de checks en `docs/operacion.md`; verificar con pruebas que `pending` o `unavailable` no se muestran como aprobados.

## 7. Verificación integrada

- [x] 7.1 Ejecutar la suite completa y un flujo sintético de cliente preparado con aclaración, revisión de plan, `apply`, corrección, verificación, revisión de diff y PR; verificar la secuencia de eventos, archivos y costos del mismo intento.
- [x] 7.2 Validar el bundle de desarrollo con `databricks bundle validate --strict -t dev --profile CREA_DEV` tras añadir la tabla y permisos; verificar que solo refiere recursos `demo_harness_*` y el warehouse de sandbox autorizado.
- [x] 7.3 Ejecutar `openspec validate conversational-client-openspec-workflow --strict` y revisar el diff de este cambio antes de solicitar implementación; verificar que los artefactos permanecen coherentes con el comportamiento probado.

