# Design

## Context

Base inspeccionada: Db_Spec_Harness, 47756733afa86ec82980dd8724d0775cb163efc3. Véase proposal.md para motivación. docs/sql contiene solo detalle con read_files inferido y un join dependiente de una vista manual. models.py calcula Decimal desde prompt_tokens/completion_tokens; app/start_server.py persiste estimated_cost_usd y pricing_source mediante AgentCallContract. Hay históricos v2/v3 y registros de ejecución de modalidades distintas. La spec vigente ya impide recalcular históricos y presentar usage ausente como cero.

La exploración de solo lectura en CREA_DEV confirmó fuentes accesibles system.serving.endpoint_usage, system.billing.usage y list_prices. El enriquecimiento con system.serving.served_entities para identidad de modelo requiere comprobar acceso, esquema y vigencia de esa dimensión durante implementación; su ausencia no inventará identidad ni eliminará llamadas. system.ai_gateway.usage tiene un esquema distinto del publicado actualmente y cero coincidencias en la ventana/identidad consultada: no se dependerá de esa tabla ni se habilitará tracking. Una llamada Sonnet 5 tiene tres IDs físicos distintos exitosos; no hay evidencia suficiente para afirmar por qué se repitió la solicitud.

Instalación objetivo: workspace 7405606739630987; warehouse 9e696889dea65361 (demo-harness-sandbox-wh); raíz /Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/artifacts/runs; App demo-dbx-harness-mvp; Job sandbox 611081415041874. Estos valores pertenecen al bloque de instalación entregado, no a una selección diaria del catálogo. No se cambiarán recursos cliente.

## Goals / Non-Goals

**Goals:** ejecución directa de reportes independientes; métricas de llamada y consumo físico con granularidad explícita; cálculo monetario reproducible; facturación neta con precio de lista y cobertura visibles.

**Non-Goals:** obtener factura Azure/importe contractual con descuentos e impuestos, habilitar tracking/ACL, crear dashboards o tablas persistentes, cambiar modelos o política de retry, ni repartir costos compartidos a HUs mediante reglas arbitrarias. No se alteran snapshots históricos para corregir tarifas.

## Decisions

### 1. Cinco SELECT independientes con bloque inicial de filtros

Modificar harness_costs_by_call.sql y harness_endpoint_usage_join.sql; añadir harness_costs_summary.sql, harness_billing_reconciliation.sql y harness_costops_quality.sql. Cada archivo incluye sus CTE de lectura, normalización y filtros; ninguno depende de una vista creada por el usuario. Todas las tablas se califican con tres partes; read_files utiliza rutas absolutas del volumen del harness.

El bloque params inicial contiene fecha_desde y fecha_hasta (por defecto últimos siete días locales, ambos inclusivos), hu_id, run_id, attempt_id, model y call_id con strings vacíos como ausencia. El lector cambia literales del bloque y ejecuta el archivo completo. No se exigen widgets, rutas, USE CATALOG, variables de sesión ni creación previa. La guía muestra ejemplos listos para editor SQL y CLI --file con --profile CREA_DEV --warehouse 9e696889dea65361. Para otra instalación se entrega un bloque de instalación revisado una vez; no se modifica en cada consulta.

Identificadores exactos y AND para filtros simultáneos. HU corresponde a story_id real, que puede incluir un título completo; no se inventa un ID corto. Fechas convertidas explícitamente desde America/Bogota a UTC, rango [inicio, día posterior al final). Rango invertido falla de forma comprensible. Filtrar un run antiguo requiere ampliar las fechas; ningún identificador elimina silenciosamente el filtro temporal. Timestamps UTC y representación local se identifican.

Alternativa descartada: parameter markers para rutas o dependencias compartidas persistentes, porque añaden preparación manual. Duplicación de CTE se controla con pruebas de coherencia y cambios conjuntos de los cinco archivos.

### 2. Normalización explícita de históricos y precisión

read_files utilizará un schema mínimo explícito, tolerante a campos opcionales de ejecución/llamada, suficiente para los cinco reportes; evitar referencias a structs inferidos que desaparecen en ventanas históricas. Incluir claves, modelo/rol/fase, estado de invocación y aceptación, fechas, tokens, costo y snapshot de tarifa. Considerar campos incompatibles/rescatados en el reporte de calidad, sin descartar filas silenciosamente. Leer únicamente *.json de runs y agent_calls, sin introducir checkpoints o evidencia sintética de otras carpetas en el costo por HU.

Importes DECIMAL con precisión suficiente y redondeo solo de presentación; nunca convertir null a cero de consumo. Guardar subtotal conocido, cobertura y faltantes. Prompts/respuestas y texto de la HU no relacionado con identificación quedan fuera de los reportes financieros. El detalle mantiene una fila por (run_id, attempt_id, call_id); conflictos de clave se señalan y evitan sumas arbitrarias.

### 3. Dos granularidades para conciliación

La conciliación primero limita workspace/ventana y agrupa evidencia física por (workspace_id, databricks_request_id). Repeticiones idénticas se consolidan; contradicciones se señalan. Une client_request_id y comprueba usage_context de run/intento/HU cuando exista, y modelo mediante served_entities si está disponible. databricks_request_id registrado por el harness ayuda a identificar la respuesta observada, pero no elimina otras solicitudes físicas de la misma llamada.

El reporte principal agrega resultados físicos antes de unir a llamadas: request_count, estado missing/single/multiple/conflict, tokens físicos conocidos y cobertura, además del uso/costo histórico una sola vez. IDs/estados físicos quedan auditables sin prompts. Los tres IDs distintos observados son solicitudes adicionales, no duplicados a borrar. No se modifica política del SDK para resolver esta observabilidad.

### 4. Actualizar supuestos sin reescribir costos

Conservar routing y capacidades de models.yaml. Verificar tarifas DBU por millón de entrada/salida de cada modelo y precio DBU aplicable, documentando SKU, fuente primaria, fecha, vigencia, redondeo y limitaciones de cache. El precio observado de PREMIUM_ANTHROPIC_MODEL_SERVING es USD 0,105/DBU desde 2025-03-26; con 28,571/142,857 DBU por millón, Sonnet 5.5 resulta aproximadamente USD 3/15 por millón. Revalidar ambas piezas antes de fijar esos números. Haiku conserva su tarifa hasta verificar una fuente específica; no multiplicar todas las tarifas automáticamente por 1,5.

Añadir metadatos de versión/vigencia y snapshot numérico de las tarifas usadas por nuevas llamadas a AgentCallContract y su construcción en start_server.py; models.py/contracts.py solo se ajustan en la medida necesaria para propagar y validar ese snapshot. Campos opcionales para históricos; incrementar versión de contrato si corresponde según convenciones existentes. Un cambio de tarifa no reconstruye registros previos, recalcula approvals ni modifica el perfil.

Para reestimación de llamadas históricas, cada SQL incorpora una relación pequeña versionada de tarifas verificadas por modelo, consistente con la configuración y su evidencia; pruebas de coherencia impiden divergencia. Se llama costo_reestimado_tarifa_revisada, no costo histórico corregido ni factura. Modelos antiguos sin tarifa verificable conservan solo costo histórico. La App usa configuración local aprobada, no consultas de facturación en cada invocación. Componentes de cache no soportados permanecen como limitación explícita; no se inventan conteos o tarifas.

### 5. Facturación agregada y calidad

Consultar system.billing.usage por workspace, periodo, endpoints pertinentes y recursos exactos del harness para componentes de infraestructura; sumar ORIGINAL/RETRACTION/RESTATEMENT con su signo. Evitar un filtro limitado a SERVERLESS_REAL_TIME_INFERENCE: el consumo principal observado está en PREMIUM_ANTHROPIC_MODEL_SERVING. Unir list_prices por cuenta, nube, SKU, unidad, USD y vigencia [inicio, fin), mostrando ambigüedad y ausencia sin multiplicar cantidades. Si un registro cruza una frontera tarifaria no resoluble con su granularidad, mostrar limitación/importe desconocido en vez de inventar distribución temporal.

Un filtro de HU/run deriva endpoints y días completos pertinentes a las llamadas seleccionadas; la facturación se etiqueta endpoint_period_shared. No se recorta un bloque facturado parcialmente como si su consumo pudiera dividirse por tiempo exacto. El reporte conserva las ventanas consultadas y cobertura, y separa inferencia de App/SQL/sandbox. No compara totales de ventanas o identidades diferentes como una discrepancia concluyente. Precio de lista no es importe final de factura.

Calidad: duplicados lógicos/físicos, conflictos, huérfanos, tokens/costos ausentes, requests sin llamada del harness, precios ausentes/ambiguos, importes incompletos y última fecha de datos. Preflight acotado mediante lectura y diagnóstico; cero filas en gateway no prueba cero inferencias. El operador consulta permisos actuales; este cambio no agrega ACL ni fuentes alternativas silenciosas.

## Risks / Trade-offs

- Duplicación de CTE entre archivos -> pruebas de filtros, normalización y resultados comunes; cada consulta mantiene ejecución independiente.
- Endpoint compartido, retraso y componentes SDK no observados -> conservar ambas granularidades y no prometer atribución real por llamada/HU.
- Esquema histórico incompleto -> schema mínimo explícito y fixtures de contratos previos; campos nuevos null.
- Tarifas revisadas pueden elevar estimaciones/presupuestos -> probar comportamiento de presupuesto sin elevar sus límites ni cambiar modelos.
- Permisos de operador distintos de los de App -> verificar SQL con CREA_DEV; no presentar esa verificación como permiso de facturación de la App.
- Consultas sobre volúmenes y tablas de sistema consumen SQL -> ventanas acotadas y warehouse del harness; ninguna invocación LLM requerida para validar consultas.

## Migration Plan

1. Implementar consultas/guía, snapshots y tarifas verificadas; ejecutar pruebas locales y smoke SQL de solo lectura con instalaciones calificadas.
2. Comparar conteos/totales de los cinco reportes y registros históricos protegidos; registrar resultados y SHA de producto en docs/evidence.
3. Presentar implementación verificada. Publicación y despliegue se realizan cuando se soliciten, preservando los cambios locales ajenos.
4. Rollback de SQL/configuración/código mediante revisión anterior, sin editar datos históricos ni recursos. Restaurar tarifas antiguas afecta nuevas llamadas únicamente y exige documentación de su procedencia.
