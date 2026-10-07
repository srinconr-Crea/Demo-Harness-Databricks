# Tarifas estimadas verificadas — 2026-10-07

Esta revisión cambia supuestos locales de estimación y añade su snapshot. No despliega la App. La App actualmente desplegada conserva sus tarifas y contrato hasta una publicación futura autorizada; las consultas entregadas muestran la reestimación por separado, sin editar JSON históricos.

## Fuentes y vigencia

La [tarjeta oficial Databricks de Proprietary Foundation Model Serving](https://www.databricks.com/product/pricing/proprietary-foundation-model-serving), consultada el 2026-10-07, publica para Standard Pay Per Token: Sonnet 5/5.5, 28.571 DBU por millón de tokens de entrada y 142.857 de salida; Haiku 4.5, 14.286 y 71.429. Es evidencia específica de cada modelo; no se aplicó un multiplicador global.

Consulta de solo lectura realizada por el agente coordinador mediante CREA_DEV en el warehouse del harness `9e696889dea65361`, el 2026-10-07:

```sql
SELECT account_id, sku_name, cloud, currency_code, usage_unit,
       price_start_time, price_end_time, pricing.effective_list.default AS usd_per_dbu
FROM system.billing.list_prices
WHERE sku_name = 'PREMIUM_ANTHROPIC_MODEL_SERVING'
  AND cloud = 'AZURE' AND currency_code = 'USD' AND usage_unit = 'DBU'
  AND price_start_time <= current_timestamp()
  AND (price_end_time IS NULL OR price_end_time > current_timestamp());
```

Resultado: cuenta `e0efe543-4cd7-41e5-a76e-9c8aad60142b`, precio `0.105000000000000000 USD/DBU`, inicio `2025-03-26T00:00:00Z`, fin null. La CLI devolvió filas sin ID de statement. La tabla conserva precios de lista y su intervalo de vigencia, según la [documentación oficial de pricing](https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/pricing).

El snapshot usa `version=harness-costops-2026-10-07`, `checked_at=2026-10-07` y `effective_from=2026-10-07T00:00:00Z`. Esta última fecha identifica el comienzo del nuevo supuesto aprobado en el repositorio; no afirma que toda la tarjeta de modelos haya comenzado a tener vigencia ese día ni que la App ya use el cambio. La vigencia observada del precio DBU es distinta, como indica la consulta.

## Cálculo Decimal reproducible

`USD/token = DBU/millón × 0.105 / 1000000`. Se conserva exactamente el producto de los valores publicados, sin redondear cada token. La precisión publicada de los DBU no garantiza precisión equivalente del importe facturado.

| Modelo | Anterior USD/MTok entrada/salida | Revisado USD/MTok entrada/salida | Revisado USD/token entrada/salida |
|---|---:|---:|---:|
| databricks-claude-sonnet-5-5 | 2 / 10 | 2.999955 / 14.999985 | 0.000002999955 / 0.000014999985 |
| databricks-claude-haiku-4-5 | 1.5 / 7.5 | 1.500030 / 7.500045 | 0.000001500030 / 0.000007500045 |

Haiku ya tenía un supuesto cercano al nuevo cálculo específico: la pequeña diferencia se debe a conservar el producto de los DBU publicados. No hereda el aumento de Sonnet. Los modelos históricos diferentes no reciben una tarifa revisada por semejanza del nombre.

Una llamada Sonnet con 1000 tokens de entrada y 200 de salida cuesta estimadamente `0.005999952 USD`. Un millón de tokens de cada tipo da Sonnet `17.999940 USD` y Haiku `9.000075 USD`.

## Persistencia y compatibilidad

Cada llamada nueva realizada por una futura publicación carga un snapshot de versión, moneda, comprobación, vigencia del supuesto, SKU, fuente, USD/DBU, DBU por millón, tarifas por token y limitaciones. `ModelClient` copia el snapshot antes de la invocación y la aceptación posterior conserva sus valores; `start_server.py` lo persiste en `AgentCallContract` v4. El campo es opcional: contratos v2/v3 conservan costo y procedencia anteriores y no se reestiman al cargar. Sin usage, tokens y costo continúan null aunque el supuesto utilizado sea conocido. Carga y cliente rechazan tarifas no positivas o no finitas; el snapshot se comprueba contra las tarifas del cálculo.

No se alteraron routing, capacidades, perfiles, número de llamadas ni límites de tokens/contexto. No existe aquí un nuevo presupuesto monetario ni se incrementa ningún límite para compensar el mayor supuesto de Sonnet.

## Limitaciones

El cálculo utiliza el precio estándar global: no incorpora el incremento por procesamiento regional que publica la tarjeta ni distingue cache read/cache write de los totales `prompt_tokens`. Estos componentes pueden cambiar los DBU facturables. La columna sigue siendo una estimación, no factura ni importe contractual con descuentos/impuestos. La facturación y sus ajustes se validan por separado con `system.billing.usage` y el precio vigente compatible; no se atribuye íntegra a una HU por usar el mismo endpoint.

## Verificación

TDD: primera ejecución de ocho casos nuevos, ocho fallidos por tarifas previas, falta de validación y snapshot ausente. Después, dos casos adicionales fallaron por tarifa no numérica y tarifa directa negativa; se corrigieron antes del green. Resultado final de `tests/test_costops_pricing.py`: **10 passed**, 0.68 s. Ejecución conjunta de los primeros ocho casos con integrations, contracts, candidate_call_logging y response_recovery: **91 passed**, 111.13 s; una advertencia previa de Starlette/httpx. La suite completa se registra en la evidencia integrada del cambio por el coordinador.
