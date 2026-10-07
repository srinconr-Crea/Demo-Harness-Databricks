# CostOps del harness

Abra cualquiera de los cinco `.sql` en el editor SQL, seleccione **demo-harness-sandbox-wh** y ejecute el archivo completo. No seleccione catálogo, cree vistas ni ejecute otra consulta antes. Las rutas del volumen y tablas `system` están calificadas para workspace `7405606739630987`; otra instalación requiere revisar esos valores una vez.

Cada archivo empieza por `params`. Los valores predeterminados cubren hoy y los seis días anteriores en **America/Bogota**, independientemente de la zona de sesión. Para un rango concreto sustituya solamente las dos expresiones por fechas:

```sql
SELECT DATE '2026-10-01' AS fecha_desde,
       DATE '2026-10-07' AS fecha_hasta,
       '' AS hu_id,
       '4684261fbd554fea87185a765dc754f8' AS run_id,
       '' AS attempt_id, '' AS model, '' AS call_id
```

El día final está incluido. Un rango invertido falla. Los identificadores son coincidencias exactas; un string vacío no restringe. Filtros simultáneos usan **AND**. `hu_id` es el `story_id` guardado, que puede contener el título completo. Un run antiguo necesita también ampliar las fechas. Los timestamps `*_utc` son instantes UTC; `*_bogota` identifica su representación local. No cambie el volumen para cada HU.

| Archivo | Resultado y granularidad |
| --- | --- |
| `harness_costs_by_call.sql` | Una fila por run/intento/llamada, tokens reportados, estimación histórica y reestimación revisada. Una clave contradictoria conserva una fila con estado `conflict` y métricas desconocidas. |
| `harness_endpoint_usage_join.sql` | Misma llamada lógica y costo histórico una sola vez; solicitudes físicas agregadas antes de la unión, IDs/estados, cobertura y coincidencias faltantes/múltiples/conflictivas. |
| `harness_costs_summary.sql` | Totales por HU/run/intento/modelo/rol/fase/estado. Subtotales conocidos y cobertura; incluye llamadas rechazadas y fallidas y distingue consumo físico. |
| `harness_billing_reconciliation.sql` | Consumo neto facturable y costo a precio de lista por componente, endpoint, SKU, unidad y periodo. |
| `harness_costops_quality.sql` | Claves contradictorias, históricos huérfanos, campos rescatados, faltantes, requests sin llamada seleccionada, precios y retraso de facturación. |

## Ejecución desde terminal

La CLI instalada v1.18.0 no expone un comando de ejecución SQL con `--file`. El ejecutor adjunto usa el SDK ya instalado en el proyecto y ofrece ese mismo bloque de argumentos:

```powershell
src/agents/harness/.venv/Scripts/python.exe docs/sql/run_costops.py --file docs/sql/harness_costs_by_call.sql --profile CREA_DEV --warehouse 9e696889dea65361
src/agents/harness/.venv/Scripts/python.exe docs/sql/run_costops.py --file docs/sql/harness_billing_reconciliation.sql --profile CREA_DEV --warehouse 9e696889dea65361
```

Modifique primero `params` en el archivo. El ejecutor devuelve JSON con ID del statement, columnas y filas, y termina con error si Databricks rechaza la consulta. No configura permisos ni crea recursos. También se pueden ejecutar los archivos completos mediante la API SQL Statement Execution.

## Interpretación financiera

`estimated_cost_usd` / `costo_historico_estimado_usd` conserva el valor registrado. `costo_reestimado_tarifa_revisada` usa la relación versionada `harness-costops-2026-10-07` verificada y alineada con configuración; no modifica registros. Sonnet 5.5: USD 0,000002999955/0,000014999985 por token entrada/salida. Haiku 4.5: USD 0,000001500030/0,000007500045. Modelos históricos sin tarifa verificada no heredan otro precio. La evidencia y fuentes de tarifas están en `docs/evidence/2026-10-07-costops/`.

Los tokens de la llamada provienen del endpoint. Los tokens físicos suman solicitudes distintas, incluso si una llamada generó tres IDs exitosos; no prueban por qué ocurrió. Repeticiones idénticas del mismo ID se consolidan, contradicciones permanecen visibles. El modelo se comprueba contra `served_entities` vigente en el instante del request; dimensión ausente permite coincidencia con marca de identidad no comprobada, contradicciones o vigencias ambiguas no se aceptan. Contexto run/intento/HU presente debe coincidir. Ninguna consulta usa prompts o respuestas como columnas financieras.

Los null son desconocidos; las columnas `*_known` son **subtotales**, no totales completos. La cobertura indica cuánto falta. Los campos rescatados requieren revisión: un schema mínimo puede rescatar campos adicionales conocidos del contrato y no implica por sí mismo que todo el registro sea inválido. Los registros sin timestamp no se incluyen en los totales temporales y se cuentan por separado en calidad.

Facturación incluye cantidades **con signo** de ORIGINAL, RETRACTION y RESTATEMENT. El costo de lista requiere un precio único por cuenta/nube/SKU/unidad/USD vigente para el bloque entero. Un precio ausente, ambiguo o una frontera tarifaria deja el importe desconocido. Los productos usan precisiones decimales acotadas para conservar los 12 decimales de tarifa por token y 24 del consumo monetizado. Un bloque facturable que no quepa exactamente en DECIMAL(27,18) para cantidad o DECIMAL(10,6) para precio queda `invalid_decimal_precision`, con importe desconocido, sin redondearlo silenciosamente. Una HU/run deriva endpoints y días relacionados: `endpoint_period_shared` es consumo compartido, **no costo real atribuido a esa HU**. App, warehouse y Job sandbox se identifican con recursos exactos únicamente; filtros de HU/run excluyen infraestructura sin enlace verificable.

Ni precios de lista ni estimaciones equivalen al importe final de factura Azure, con posibles descuentos, créditos e impuestos. Componentes de cache no observados permanecen como incertidumbre. Una consulta sin filas o facturación retrasada no demuestra costo cero. `physical_requests_without_selected_call` corresponde a la selección actual y puede incluir tráfico legítimo de otros usuarios del endpoint. Los diagnósticos de integridad de la fuente física (repeticiones, IDs conflictivos o ausentes) abarcan el workspace y rango temporal, incluso tráfico ajeno a la HU seleccionada; los diagnósticos de llamadas aplican los filtros de identidad. `unknown_time_selected_ids_date_unverifiable` aplica esos identificadores pero no puede comprobar el rango de fecha porque falta el timestamp.

## Permisos y diagnóstico

Se requiere lectura del volumen de runs/agent_calls; los reportes de conciliación/resumen/calidad requieren `system.serving.endpoint_usage` y `system.serving.served_entities`; facturación/calidad también requieren `system.billing.usage` y `system.billing.list_prices`. Consulte al administrador si una fuente falta o está denegada: estos archivos no cambian ACL ni sustituyen una fuente silenciosamente. No dependen de `system.ai_gateway.usage` ni habilitan tracking.
