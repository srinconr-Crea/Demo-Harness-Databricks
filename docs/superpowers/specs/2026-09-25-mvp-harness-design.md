# Diseño del MVP del harness Databricks

## Resultado esperado

Una sola Databricks App recibe manualmente una HU con cinco bloques: arquitectura, origen/destino, reglas de negocio, requisitos no funcionales y validaciones. El servicio consulta el perfil NaturaPet, analiza el cambio con Claude Sonnet 5, genera una modificación acotada en una rama `feature/*`, verifica con pruebas deterministas y Claude Haiku 4.5, publica la rama y abre un PR hacia `develop`. La aprobación, merge y despliegue son humanos.

## Límites de propiedad

El repositorio `Demo-Harness-Databricks` contiene scaffold, App, motor, políticas y perfiles YAML. El código NaturaPet solo cambia en `feature/*`; la App no actualiza catálogos, jobs, rutas ni repositorios de trabajo existentes. Las pruebas remotas usan recursos nuevos y separados del entorno NaturaPet. La GitHub App se instala únicamente en el repositorio autorizado.

## Flujo

1. Pydantic valida la HU y el perfil de cliente; valores fuera de rutas y ramas autorizadas fallan antes de llamar un modelo.
2. GitHub App obtiene un token de instalación breve para leer el commit exacto de `develop`; el token no se escribe en logs ni URL.
3. Sonnet 5 produce plan y propuesta de edición estructurada. El piloto restringe la edición al notebook Silver comercial y a pruebas nuevas relacionadas; cambios arbitrarios fuera de rutas permitidas se rechazan.
4. El motor aplica el cambio sobre un checkout temporal, añade pruebas de cálculo y ejecuta validación local de sintaxis, contratos y DAB. La validación remota, cuando esté configurada, corre en sandbox nuevo sin escribir datos NaturaPet.
5. Haiku 4.5 revisa diff y evidencia. El gate determinista exige tests aprobados, rutas permitidas y rama basada en `develop`; el modelo no puede anularlo.
6. El motor publica `feature/*` y abre PR hacia `develop`. Un reintento identifica la misma HU y reutiliza rama/PR.

## Modelo de datos y controles

La entrada, perfil, workflow, routing y costos se definen en YAML/Python versionados. La App contiene una sola pantalla de formulario y resultado. Hay límites técnicos de tamaño, iteraciones y duración, sin tope monetario inicial. Cada llamada registra tokens y estimación en USD. GitHub App requiere solo Contents RW, Pull Requests RW y Metadata R, con instalación en NaturaPet. Las claves se leen desde recurso Secret de Databricks.

## Piloto

HU: agregar `margen_sobre_costo_pct = margen_bruto / costo_total` en `fact_ventas_cabecera`, con NULL si el costo es cero o NULL. Probar valor normal, costo cero y costo NULL con datos sintéticos. El PR debe incluir código, pruebas, verificación, costos y explicación de que no hubo merge ni despliegue.

## Riesgos observables

El scaffold genera AgentServer conversacional, por lo que se adapta a FastAPI de formulario conservando DAB y evaluación que aportan valor. El uso de modelos es tokenizado; las capturas muestran un escenario de 1+1 tokens que subestima el costo de una HU. El notebook NaturaPet depende de `dbutils` y de rutas de workspace, así que los tests de transformación deben aislar la función y el sandbox remoto nunca ejecutar la carga completa.
