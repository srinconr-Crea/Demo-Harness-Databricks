# Verificación CostOps — 2026-10-07

Cambio `reconcile-harness-costops`, rama `Db_Spec_Harness`, base `47756733afa86ec82980dd8724d0775cb163efc3`. Los hashes SHA-256 del producto verificado están en `verification.json`; identifican los archivos locales antes del commit de entrega.

## Pruebas y revisión

La suite del producto terminó con **474 passed**, distribuida sin duplicar casos en seis grupos de 79, en 1256,18 segundos. Incluye diez pruebas nuevas de tarifas/snapshot. `python-suite.json` conserva resultados y colas de los logs; la advertencia de Starlette/httpx es previa. Los 21 casos de `tests/test_costops_sql.py` terminaron con **21 passed** en 339,67 segundos: seis controles locales, cinco reportes reales y diez pruebas conductuales. En conjunto se verificaron **495 casos distintos**.

Los fixtures ejecutan los cálculos SQL entregados con fuentes sintéticas SELECT, sin crear objetos. Comprueban una llamada/tres requests, duplicados idénticos, conflictos lógicos/físicos, propietarios ambiguos, contexto/modelo incompatible, dimensión ausente, claves/tiempos ausentes, huérfanos y campos rescatados, filtros exactos y medianoches Bogotá, cobertura parcial, negativos, ajustes de facturación y precios ausentes/ambiguos/cruzados. Sonnet conserva exactamente `0.005999952 USD` para 1000/200 tokens; `0.123456789012345678 DBU × 0.105` conserva `0.01296296284629629619 USD`. Los rangos invertidos fallan también con fuentes vacías. `sql-fixtures.json` registra 11 statements correctos y dos errores esperados.

La revisión independiente del runtime no encontró bloqueadores. La revisión SQL encontró dependencia de zona de sesión, filtros incompletos y posibles propietarios múltiples; se corrigieron y verificaron con fixtures. Estos también detectaron y comprobaron las correcciones de precisión decimal, negativos físicos y evaluación del rango inválido. Se ejecutó `git diff --check` sin errores y la validación OpenSpec strict del cambio fue correcta. Las cinco incorporaciones se sincronizaron en `observability-control`; la validación strict de las 15 specs pasó sin fallos. Con las diez tareas completas, el cambio quedó archivado en `openspec/changes/archive/2026-10-07-reconcile-harness-costops/`.

## Consultas reales de solo lectura

Perfil `CREA_DEV`, workspace `7405606739630987`, warehouse `demo-harness-sandbox-wh` (`9e696889dea65361`). Los cinco archivos finales se ejecutaron sin selección de catálogo, vistas, ACL nuevas o llamadas LLM, con defaults y con fecha/run y fecha/HU/run. Los IDs y salidas financieras están en `sql-defaults-final.json`, `sql-filtered.json` y `sql-hu-run-final.json`. `sql-smoke.json` está marcado como evidencia intermedia, anterior a las correcciones finales.

| Reporte | Filas defaults | Filas del run exitoso |
| --- | ---: | ---: |
| Detalle | 128 | 15 |
| Conciliación física | 128 | 15 |
| Resumen | 29 | 5 |
| Facturación | 9 | 4 |
| Calidad | 25 | 25 |

El run `339bbcda32a848b18743cdc4c1cc06e9` conserva **USD 1,0437625 históricos** y muestra por separado **USD 1,556796736740 reestimados**. Detalle y resumen coinciden con aritmética Decimal. La llamada `367079dd8d7248da80bfc1c5fdc937f1` conserva una fila, tres requests y 86469/16963 tokens físicos; su costo histórico aparece una sola vez.

Con defaults, 127 de 128 llamadas tienen costo histórico: subtotal conocido **USD 10,1262445**. Solo 114 tienen datos/modelo con tarifa revisada configurada: subtotal conocido **USD 13,223280066885**. Son sumas parciales; históricos de otros modelos no reciben tarifas por semejanza. Los 128 enlaces físicos incluyen 127 simples y uno múltiple. Los campos rescatados pueden ser campos adicionales conocidos fuera del schema mínimo, no prueban corrupción por sí solos. El diagnóstico de timestamps ausentes conserva los filtros de identidad, pero no puede verificar fecha.

Facturación permanece agregada por endpoint/periodo y componente, con alcance compartido explícito al filtrar una HU. El costo de lista no equivale a factura ni a costo real exclusivo de una HU; cache y procesamiento regional siguen como limitaciones de la estimación. Los errores de acceso no se convierten en consumo cero.

## Estado protegido y publicación

`protected-state.json` confirma hashes intactos de **141 JSON históricos**, sin nuevos archivos, bindings sin cambios y App en estado `STOPPED`. No se modificaron registros ni recursos de clientes, modelos, routing, capacidades o límites. Se conservan fuera del commit los cambios locales previos de preparación NaturaPet.

Esta entrega autoriza push al repositorio y **no despliega la App**. El snapshot v4 y las tarifas nuevas del runtime requieren una publicación futura para afectar nuevas llamadas; los SQL sí pueden ejecutarse directamente desde los archivos entregados. La evidencia de tarifas y sus límites se encuentra en `pricing.md` y la guía diaria en `../../sql/README.md`.
