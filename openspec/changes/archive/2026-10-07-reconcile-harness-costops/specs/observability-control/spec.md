# Spec Delta

## ADDED Requirements

### Requirement: Consultas CostOps ejecutables sin preparación de catálogo
Los reportes CostOps SHALL ejecutarse de forma independiente y de solo lectura en la instalación entregada, sin seleccionar catálogo/esquema, crear vistas persistentes o ejecutar previamente otro reporte. SHALL incluir rutas y fuentes calificadas de esa instalación y un bloque inicial de filtros con valores predeterminados utilizables. La operación diaria SHALL requerir modificar solamente fechas o identificadores aplicables, conservando el aislamiento del harness.

#### Scenario: Primera ejecución directa
- **WHEN** el operador abre cualquiera de los cinco reportes y lo ejecuta con sus valores predeterminados en el warehouse autorizado
- **THEN** obtiene resultados de los últimos siete días locales sin cambiar catálogo, rellenar rutas ni crear objetos auxiliares

#### Scenario: Filtros por historia o ejecución
- **WHEN** el operador proporciona HU, run, intento, modelo o llamada según los filtros admitidos del reporte
- **THEN** se aplican coincidencias exactas; filtros vacíos no restringen y filtros simultáneos se combinan por intersección

#### Scenario: Fecha final y zona horaria
- **WHEN** el operador selecciona un rango inclusivo de fechas en America/Bogota
- **THEN** se incluyen eventos desde el inicio local del primer día hasta antes del inicio local del día posterior al último, independientemente de la zona de sesión

#### Scenario: Rango inválido o falta de permisos
- **WHEN** el rango está invertido o una fuente requerida no es accesible
- **THEN** se informa el problema sin ampliar permisos, seleccionar otro catálogo silenciosamente ni presentar cero consumo como una consulta completa

### Requirement: Conciliación separada de llamadas y solicitudes físicas
CostOps SHALL distinguir una llamada lógica identificada por run, intento y call_id de cada solicitud física identificada por el request ID de Databricks. SHALL preservar una fila y costo histórico por llamada en detalle/resumen, aun si existen múltiples solicitudes físicas. SHALL mostrar coincidencias faltantes o múltiples y consumo físico por separado, sin eliminar solicitudes distintas mediante una deduplicación arbitraria. SHALL restringir coincidencias al workspace y comprobar contexto/modelo cuando sea verificable.

#### Scenario: Una llamada con tres solicitudes exitosas
- **WHEN** un client_request_id enlaza tres databricks_request_id distintos con respuesta exitosa
- **THEN** el detalle conserva una llamada lógica y una estimación histórica, muestra tres solicitudes y suma tokens físicos aparte sin afirmar que son duplicados técnicos o costos finales facturados

#### Scenario: Registro físico repetido
- **WHEN** la fuente contiene dos registros del mismo identificador físico y workspace
- **THEN** se evita sumar dos veces evidencia idéntica; registros contradictorios se diagnostican sin escoger arbitrariamente el que favorece el costo

#### Scenario: Llamada no conciliada
- **WHEN** no existe evidencia física compatible para una llamada
- **THEN** conserva su costo histórico y muestra estado no conciliado; no inventa uso, consumo adicional ni costo real

### Requirement: Importes y cobertura auditables por HU y modelo
CostOps SHALL mostrar tokens de entrada/salida con fuente, costos históricos y estimaciones revisadas como métricas separadas, con aritmética decimal. SHALL ofrecer detalle por llamada y agregaciones por HU, run, intento, modelo y rol/fase, incluyendo fallos y reintentos. SHALL informar cantidad total, llamadas con uso/costo y faltantes; sumas parciales SHALL identificarse como tales. SHALL conservar históricos con campos ausentes y reportar huérfanos/contratos incompatibles. Los reportes financieros ordinarios no SHALL incluir textos de prompts o respuestas.

#### Scenario: Una llamada sin usage
- **WHEN** un grupo incluye llamadas con costo conocido y una llamada sin tokens reportados
- **THEN** muestra subtotal conocido y cobertura incompleta, conservando null para el costo desconocido

#### Scenario: Históricos y tarifas revisadas
- **WHEN** se consulta una llamada anterior tras actualizar tarifas
- **THEN** el costo histórico permanece igual y una reestimación aparece en otra columna con su propia fuente; la ausencia de datos requeridos produce null

#### Scenario: Filtrado de una HU con varios intentos
- **WHEN** una HU contiene intentos fallidos y uno completo
- **THEN** su total incluye todas las llamadas seleccionadas y permite distinguir consumo de cada intento sin reutilizar evidencia de otro

### Requirement: Tarifas documentadas y reproducibles por llamada
Las nuevas llamadas SHALL utilizar tarifas estimadas verificadas para su modelo, con moneda, versión, fecha de comprobación, vigencia y fuente documentadas. SHALL conservar un snapshot de las tarifas usadas que permita reproducir su cálculo. Actualizar tarifas no SHALL modificar routing, límites ni registros históricos; tarifas ausentes o inválidas SHALL impedir presentar estimaciones válidas. Componentes de tokens no contemplados, como cache cuando corresponda, SHALL identificarse como limitaciones del cálculo y no contabilizarse silenciosamente como costo exacto.

#### Scenario: Cambio del precio por DBU
- **WHEN** se verifica un precio de lista por DBU diferente del supuesto anterior para un modelo configurado
- **THEN** nuevas llamadas usan el supuesto actualizado y registran su procedencia, mientras las anteriores conservan sus valores y snapshots originales cuando existen

#### Scenario: Tarifa histórica no disponible
- **WHEN** un modelo histórico carece de una tarifa revisada verificable
- **THEN** conserva su costo registrado pero no hereda automáticamente el precio de otro modelo para reestimarlo

#### Scenario: Componente de cache no modelado
- **WHEN** el proveedor informa componentes con tratamiento tarifario diferente y la estimación no los contempla
- **THEN** la salida identifica la limitación y mantiene el costo como estimación, sin prometer equivalencia con factura

### Requirement: Consumo facturable separado de atribución y factura
CostOps SHALL consultar consumo facturable neto por workspace, endpoint, SKU, unidad y periodo, incluyendo retractaciones y restatements. SHALL monetizarlo con precio de lista compatible y vigente en columnas identificadas como costo de lista, sin confundirlo con importe final de factura. SHALL mostrar cobertura temporal, precios ausentes/ambiguos y fuentes retrasadas. Un filtro HU/run SHALL identificar modelos y periodos pertinentes, conservando el alcance compartido de facturación; no SHALL atribuir ese total íntegramente a la HU. App, warehouse y sandbox SHALL aparecer separados de inferencia cuando se consulten sus costos.

#### Scenario: Facturación retrasada
- **WHEN** hay llamadas posteriores al último periodo de consumo publicado
- **THEN** se informa pendiente de conciliación y fecha de cobertura sin declarar consumo cero ni discrepancia definitiva

#### Scenario: Ajuste de consumo
- **WHEN** existe un registro original, una retractación y un restatement
- **THEN** el consumo neto incorpora sus cantidades con signo, sin filtrar todos los ajustes como si fueran duplicados

#### Scenario: Filtro de HU sobre endpoint compartido
- **WHEN** el operador consulta facturación para una HU que usa un endpoint compartido
- **THEN** el reporte identifica el consumo agregado de endpoints/periodos relacionados y su alcance compartido, sin llamarlo costo real de esa HU o de sus llamadas

#### Scenario: Precio no encontrado o varias vigencias compatibles
- **WHEN** una cantidad facturable carece de precio único por cuenta, SKU, nube, unidad, moneda y vigencia
- **THEN** conserva la cantidad, muestra diagnóstico y costo monetizado desconocido sin duplicar importes
