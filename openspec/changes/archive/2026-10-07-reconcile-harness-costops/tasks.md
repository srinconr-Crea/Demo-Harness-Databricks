# Tasks

## 1. Tarifas verificadas y cálculo reproducible

- [x] 1.1 Verificar fuentes primarias y vigencias de tarifas entrada/salida por modelo y precio USD/DBU por SKU; registrar comparación con configuración previa en docs/evidence y actualizar models.yaml con tarifas, versión, vigencia y fuente verificadas. Verificación: cálculos Decimal reproducibles, evidencia de Sonnet/Haiku específica y tests que conservan routing, capacidades y límites; no aplicar multiplicadores globales ni cambiar modelos históricos sin evidencia.
- [x] 1.2 Propagar snapshot opcional de tarifa por llamada en carga de configuración, AgentCallContract y start_server.py, manteniendo costo null sin usage y compatibilidad de registros previos. Verificación: pruebas de cálculo con snapshot, tarifas inválidas, contratos v2/v3, presupuesto sin aumento de límites y no modificación de costos históricos; documentar nueva procedencia y limitaciones de cache en docs/operacion.md.

## 2. Detalle autónomo y filtros comunes

- [x] 2.1 Añadir fixtures/pruebas de schema mínimo de runs/agent_calls, claves ausentes, importes DECIMAL, histórico sin tarifa, conflictos y filtros; implementar harness_costs_by_call.sql independiente con bloque params y fuentes calificadas. Verificación: ejecución directa sin vista/catalog selection, una fila por clave lógica, rangos Bogotá incluyendo medianoche/final inclusive, defaults siete días y error de rango invertido, strings vacíos y filtros AND exactos; prompts/respuestas ausentes del resultado financiero.
- [x] 2.2 Crear docs/sql/README.md con mapa de las cinco consultas y ejemplos de editar únicamente fecha/HU/run/intento/modelo/llamada y ejecutar por editor/CLI en CREA_DEV y warehouse aprobado. Verificación: ejecutar ejemplos tal como están escritos sin rellenar rutas, crear vistas o usar USE CATALOG; documentar identificadores HU completos, intersección y búsqueda de runs antiguos con rango ampliado.

## 3. Solicitudes físicas y resumen por HU

- [x] 3.1 Modificar harness_endpoint_usage_join.sql para agregar solicitudes físicas antes de unir llamadas y comprobar workspace/contexto; comprobar esquema/acceso y unicidad temporal de served_entities para enriquecimiento cuando disponible. Verificación: fixtures una llamada/tres IDs exitosos, ID físico repetido idéntico, conflicto, missing, otro workspace/intento/modelo y dimensión ausente; una estimación histórica por llamada y tokens físicos separados, con estado y evidencia explícitos. Documentar diferencia entre consumo adicional y duplicación de filas.
- [x] 3.2 Crear harness_costs_summary.sql autónomo con agregaciones por HU/run/intento/modelo/rol/fase, tarifas revisadas coherentes con configuración y cobertura de usage/costo. Verificación: detalle y resumen suman el mismo subtotal Decimal por filtros, incluyen fallos/reintentos, separan histórico de reestimación, no imputan tarifas desconocidas ni convierten null a cero; documentación de granularidad y sumas parciales.

## 4. Facturación y calidad

- [x] 4.1 Crear harness_billing_reconciliation.sql autónomo con consumo neto por SKU/endpoint/periodo, precio vigente único por cuenta/nube/unidad/moneda y componentes separados de inferencia/App/warehouse/sandbox. Verificación: fixtures ORIGINAL/RETRACTION/RESTATEMENT, precio ausente/ambiguo, cambio de vigencia y bloque temporal no atribuible; incorporar SKU Anthropic sin depender solo de REAL_TIME_INFERENCE, mostrar fecha de cobertura y costo de lista separado de factura. Documentar alcance compartido de filtros HU/run y no atribución íntegra por llamada.
- [x] 4.2 Crear harness_costops_quality.sql independiente con diagnósticos de duplicados/conflictos, huérfanos, uso/costo ausente, requests sin llamada, esquema incompatible y cobertura/facturación retrasada. Verificación: fixtures esperados de cada categoría, ausencia de permisos no tratada como consumo cero, y coherencia de filtros/configuración de los cinco archivos; documentar interpretación y límites de los diagnósticos.

## 5. Verificación integrada y entrega revisable

- [x] 5.1 Ejecutar los cinco SQL en modo solo lectura con defaults y filtros por fecha/HU/run sobre demo-harness-sandbox-wh mediante CREA_DEV, sin depender del catálogo/esquema de sesión ni crear objetos persistentes. Verificación: guardar IDs de statements, conteos, totales/cobertura y resultados mínimos redactados en docs/evidence; contrastar la llamada con tres solicitudes, HU 339bbcda32a848b18743cdc4c1cc06e9 e históricos, sin exigir conteos antiguos si llegaron registros nuevos y sin invocaciones LLM ni cambios cliente.
- [x] 5.2 Ejecutar pruebas enfocadas y suite tests completa, validar OpenSpec strict y git diff --check, y revisar implementación contra delta/guía. Verificación: evidencia por SHA de producto, resultados y limitaciones; snapshot de registros históricos sin modificaciones, defaults/modelos/infra/perfil conservados salvo tarifas y procedencia previstas, cambios locales anteriores excluidos. Presentar resultado listo para apply/sync/archive/publicación según instrucciones posteriores; no acreditar despliegue por validar SQL.
