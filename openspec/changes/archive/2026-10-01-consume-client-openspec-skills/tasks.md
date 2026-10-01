# Tasks

## 1. Preparación manual y catálogo de skills

- [x] 1.1 Añadir configuración confiable de catálogo, compatibilidad y presupuestos junto con `harness/skills.py`; verificar carga de las siete skills del checkout, name/generatedBy y hashes sin fallback.
- [x] 1.2 Añadir pruebas del lector para faltantes, UTF-8 inválido, traversal, enlaces/reparse points, límites y versiones incompatibles; verificar rechazo antes de llamada al modelo y ausencia de lectura externa.
- [x] 1.3 Retirar `app/onboard_client.py` y helpers de onboarding automático de la ruta soportada, adaptar fixtures que los usan y documentar en README/operación el init manual con agents, selección custom incluyendo verify, PR y merge; verificar el procedimiento con CLI fijado en un cliente sintético y que procesar HU no ejecuta init/update ni crea PR de preparación.

## 2. Instrucciones CLI y composición

- [x] 2.1 Ampliar el adaptador con consultas y validadores de status/instrucciones de artefactos/apply/archive, rutas y dependencias; verificar con CLI real y pruebas negativas de raíz externa, esquema no soportado y apply bloqueado.
- [x] 2.2 Crear composición de skill íntegra, contrato del Harness, instrucciones, dependencias y contexto autorizado dentro de los módulos existentes; verificar presupuesto sin truncamiento y contratos JSON/context_request con modelos simulados.
- [x] 2.3 Documentar el mapa fase/skill y las capacidades mediadas en la guía del workflow; verificar que no se presentan workflows de agente como subcomandos CLI ni se interpretan allowed-tools o referencias como permisos.

## 3. Procedencia y recuperación

- [x] 3.1 Extender contratos, ModelClient y store con procedencia opcional y snapshots protegidos de instrucciones; propagarla a cada ronda/fallo sin alterar usage_context del endpoint y verificar identificadores, tokens/costos y lectura de JSON históricos.
- [x] 3.2 Normalizar rutas temporales autorizadas para hashes, incluir catálogo/runtime en plan_metadata y comprobarlos tras restaurar checkpoints; verificar recuperación en otra carpeta y rechazo de instrucciones/runtime alterados antes de aplicar/publicar.
- [x] 3.3 Definir bloqueo y reintento explícito de procesos activos anteriores sin procedencia, conservando consulta/cancelación y publication_mode; verificar históricos sin datos inventados y documentar recuperación/mantenimiento en operación.

## 4. Integración de fases y conversación

- [x] 4.1 Integrar explore/propose/update con skills del cliente y dependencias CLI en conversation.py/openspec.py; verificar HU clara, aclaraciones acumuladas, propuesta con manifiesto y cambios que invalidan aprobación.
- [x] 4.2 Integrar instructions apply y skill del desarrollador en general_patch y silver_safe_ratio conservando editor/manifiesto/sandbox; verificar operaciones fuera de alcance, hashes obsoletos y peticiones importadas de shell/modelos/rutas adicionales.
- [x] 4.3 Incorporar skill verify al verificador obligatorio y guías sync/archive al preflight determinista sin llamadas LLM adicionales; verificar pruebas/Sonnet obligatorios, Haiku asesor, sincronización única, archivo real y eventos con evidencia.
- [x] 4.4 Añadir regresión de API e interfaz para mismos estados/acciones, errores naturales de preparación, borradores persistentes y ausencia de aprobaciones adicionales; verificar publicación automática por plan y modalidad histórica de diff con tests/test_conversation.py y tests/test_conversation_webapp.py.
- [x] 4.5 Actualizar docs/repository-workflow.md y contratos de roles con la arquitectura final y límites de ejecución; verificar concordancia con los payloads y transiciones cubiertos por las pruebas de esta sección.

## 5. Verificación integrada del cambio

- [x] 5.1 Ejecutar recorrido sintético con CLI real, skills preparadas manualmente, modelos y GitHub simulados hasta PR, incluyendo reinicio y base avanzada; verificar que el candidato contiene solo código/OpenSpec autorizados y no modifica skills ni crea recursos externos.
- [x] 5.2 Ejecutar `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider`, validación estricta del cambio OpenSpec y revisión del diff; registrar resultados y confirmar que no se ejecutaron merge, despliegue ni cambios en clientes reales. Validar bundle solo si durante implementación cambia infraestructura o empaquetado Databricks.
