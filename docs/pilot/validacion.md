# Evidencia del piloto NP-001

**Resultado:** el harness abrió [NaturaPet PR #6](https://github.com/srinconr-Crea/Naturapet_DLH/pull/6) hacia `develop`, con origen `feature/np-001-margen-sobre-costo-en-silver-comercial`. El PR permanece abierto y sin merge. La App y el warehouse aislado quedaron detenidos tras la prueba.

## Cambio y controles

- El commit base fue `9c48831022a329902f765058de37e6d0a1528eb7`; el commit de la rama feature es `9626fa0e932e9bc389e2c78973b01f834873d3db`.
- GitHub confirma un solo archivo modificado: `notebooks/comercial/silver/04_business_derivations.ipynb`, con **1 adición y 0 eliminaciones**. La nueva columna es `margen_sobre_costo_pct = safe_divide(margen_bruto, costo_total)` junto a `margen_pct` en `fact_ventas_cabecera`.
- Antes de publicar, el editor validó sintaxis Python, unicidad de la medida y la expresión exacta. Sobre una copia temporal de `develop` el diff unificado tuvo 10 líneas y solo una línea nueva de código.
- El registro persistente de la ejecución `NP-001` indica `remote_check: passed`: tres filas sintéticas en `demo-harness-sandbox-wh` produjeron 2 para margen 20/costo 10, NULL para costo cero y NULL para costo NULL. El SQL no usó tablas ni DDL de NaturaPet.
- Analista y desarrollador usaron `databricks-claude-sonnet-5`; el verificador usó `databricks-claude-haiku-4-5`. Una primera ejecución se detuvo antes de crear rama por una respuesta de Sonnet en bloques; el cliente fue corregido y el reintento completó el flujo.
- GitHub muestra **0 checks** para este PR hacia `develop` y ningún despliegue de esa rama. La validación remota comprueba la fórmula SQL equivalente; **no ejecuta el notebook PySpark completo**. La aprobación y el merge siguen siendo humanos.

## Costos y verificaciones

El registro del intento exitoso estima **USD 0,0559425** por las tres llamadas a modelos, usando las tarifas aproximadas inferidas de las capturas del calculador de Databricks. Esta cifra no incluye la llamada del intento fallido, invocaciones diagnósticas, App ni warehouse. Para conocer el costo facturado total hay que consultar la telemetría de Databricks.

La suite local termina con **21 pruebas aprobadas**; lint y `databricks bundle validate -t dev` también aprobaron. Se verificó que el PEM autentica la GitHub App y que su instalación puede leer `develop` del único repositorio permitido. La clave está en el secreto de Databricks y no se versionó.

## Revisión humana pendiente

Revisar el [diff y los criterios de aceptación del PR #6](https://github.com/srinconr-Crea/Naturapet_DLH/pull/6/changes), decidir si se requiere una ejecución PySpark o un check de CI adicional y aprobar o solicitar ajustes. El harness no hará merge ni desplegará el cambio de NaturaPet.
