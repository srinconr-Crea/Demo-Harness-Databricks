# Proposal

## Why

Las consultas actuales no concilian correctamente llamadas y solicitudes físicas ni consultan consumo facturable: una validación en CREA_DEV encontró 131 llamadas y 133 filas tras el join, con estimación inflada de USD 10,1747875 a 10,3766155. El operador necesita ejecutar reportes cambiando únicamente fechas o identificadores, y tarifas documentadas que distingan estimación, consumo facturable y factura.

## What Changes

- Entregar cinco consultas de solo lectura, independientes y listas para ejecutar en el warehouse del harness: detalle por llamada, conciliación de solicitudes, resumen por HU/modelo, consumo facturable y calidad de CostOps.
- Usar nombres completos de tablas y rutas de la instalación actual; eliminar la selección manual de catálogo, parámetros obligatorios de rutas y dependencia de una vista creada previamente.
- Unificar filtros en un bloque inicial con fechas en America/Bogota e identificadores opcionales de HU, run e intento; incluir modelo y llamada donde corresponda. Ejecutar con valores predeterminados sin preparación adicional.
- Separar llamada lógica de solicitudes físicas, conservar consumos adicionales y reportar coincidencias ausentes/ambiguas sin duplicar costo histórico.
- Mostrar tokens reportados, faltantes y cobertura, importes DECIMAL, costo histórico y estimación con tarifa revisada en columnas distintas.
- Actualizar tarifas configuradas de modelos con evidencia y vigencia. La inspección de list_prices encontró USD 0,105/DBU para PREMIUM_ANTHROPIC_MODEL_SERVING frente al supuesto USD 0,07/DBU usado por Sonnet; verificar también la tarifa Haiku antes de fijarla.
- Consultar consumo facturable neto y precio de lista vigente, con retraso de datos visible; conservarlo agregado por endpoint/SKU/periodo y separado de infraestructura y factura final.
- Documentar y probar ejecución directa, granularidades y límites de atribución; preservar JSON históricos y modelos actuales.

## Capabilities

### New Capabilities

Ninguna; el cambio amplía la observabilidad existente.

### Modified Capabilities

- `observability-control`: reportes CostOps autónomos y parametrizables, conciliación de solicitudes físicas, calidad/cobertura, tarifas reproducibles y consumo facturable distinguido de estimaciones e importe final.

## Impact

Modificar docs/sql/harness_costs_by_call.sql y harness_endpoint_usage_join.sql; añadir harness_costs_summary.sql, harness_billing_reconciliation.sql y harness_costops_quality.sql, más guía de ejecución. Afecta models.yaml, carga/cálculo de tarifas y registro por llamada cuando sea necesario para guardar su snapshot; contratos nuevos deben admitir históricos sin esos campos. Añadir pruebas de consultas, granularidad y cálculo, y evidencia de solo lectura en el warehouse demo-harness-sandbox-wh con CREA_DEV.

No se cambian modelos, permisos, endpoints, recursos de NaturaPet ni infraestructura. No se crean vistas/tablas persistentes ni se habilita AI Gateway. Implementación, push y despliegue no se acreditan con esta propuesta.
