# Tasks

## 1. Baseline y alcance concreto

- [x] 1.1 Revalidar inventario de design contra SHA de apply con referencias/imports/comandos CI y empaquetado; entregar manifiesto conservar/trasladar/editar con motivos y detener eliminación dependiente ante consumidor activo inesperado.
- [x] 1.2 Ejecutar baseline de suite y preparación de instalación sintética en temporales autorizados; registrar resultados reales, archivos/hash del paquete y bloqueos de entorno sin presentarlos como éxito.

## 2. Aislar scaffold como ejemplo histórico

- [x] 2.1 Trasladar agent.py/graph.py/tools.py/app/utils.py a examples/legacy-agentops-scaffold/agent manteniendo estructura relativa; verificar diff de traslados, referencias internas y ausencia de imports del servidor activo hacia origen/destino.
- [x] 2.2 Trasladar los cuatro archivos eval y components/eval/scorers.py; verificar conservación de contenido/ejemplos, dependencias relativas y permanencia de harness/evaluation.py y su prueba funcional.
- [x] 2.3 Trasladar resources/uc_function_registration.yml como stub histórico; documentar registry ausente y comprobar que includes actuales/bindings no se modifican ni ejecutan registro UC.
- [x] 2.4 Crear README del ejemplo con origen/SHA, mapa antes/después, dependencias y límites de uso; verificar enlaces locales y que ninguna guía lo presenta como entrada operativa soportada.

## 3. Dependencias y distribución

- [x] 3.1 Retirar grupo eval exclusivo del producto y regenerar uv.lock; conservar dependencias del ejemplo por separado y verificar instalación congelada runtime/dev/spark-validation, diff del lock y CLI OpenSpec presente.
- [x] 3.2 Actualizar .env.example vigente conservando variables antiguas en ejemplo histórico; documentar configuración real de arranque y verificar que no se añadieron secretos ni cambios de routing desde HU.
- [x] 3.3 Preparar paquete sintético y ampliar regresión de instalación para excluir scaffold trasladado y conservar App/runner/perfil/hash/defaults/CLI; comprobar arranque FastAPI con perfil sintético y conectores stub, sin credenciales reales.
- [x] 3.4 Verificar app.yaml/databricks.yml/includes/sync y scripts operativos contra baseline; documentar resultado y ejecutar bundle validate estricto si se modificó bundle o recurso incluido, sin deploy ni eliminación remota.

## 4. Documentación y contexto

- [x] 4.1 Actualizar referencias vigentes en README/AGENTS/docs/contexto-proyecto/openspec config y guías afectadas; verificar enlaces y tests/test_project_context.py con presupuesto <=8 KiB, sin borrar docs, ejemplos existentes o evidencia.
- [x] 4.2 Mantener setup/supervisor como documentos históricos con referencias al ejemplo y operación vigente; comprobar clasificación/origen y que archives/evidencia antigua y manifest de procedencia no se reescriben para simular estado actual.

## 5. Verificación integrada y entrega

- [x] 5.1 Ejecutar suite completa y lint activo de CI, incluidas evaluación real, cliente/instalación, sandbox/job, skills/CLI, conversación/webapp, repository workflow y PySpark sintético; registrar éxitos/fallos reales sin confundir estructura válida con runtime verificado.
- [x] 5.2 Repetir fixture HU positiva/negativa y recuperación en espera hasta PR simulado con general_patch y silver_safe_ratio; comparar estados/aprobaciones/contratos/costos con baseline y verificar aislamiento y ausencia de llamadas auxiliares del scaffold.
- [x] 5.3 Validar OpenSpec estricto, inspeccionar diff final y manifiesto antes/después; comprobar solo traslados/ediciones previstas, conservación de documentación/ejemplos/procedencia y recursos incluidos, y cero borrado local/remoto fuera del candidato versionado.
- [x] 5.4 Preparar el cierre y entrega del refactor sin deltas funcionales: evidencia/rollback, destino Db_Spec_Harness y paquete para actualizar solo código de la App existente con CREA_DEV según autorización explícita registrada en design; comprobar conservación de bindings/checkpoints y referencias de manage-hu-agent-context ya aplicado. El archivo, despliegue y push solicitados se ejecutan después de verificar estas tareas.
