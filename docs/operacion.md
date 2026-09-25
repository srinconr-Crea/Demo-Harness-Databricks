# Operación del MVP

## Recursos y acceso

- Workspace Azure: `https://adb-7405606739630987.7.azuredatabricks.net`.
- App: `demo-dbx-harness-mvp`; URL: `https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com`.
- Catálogo propio: `demo_harness_databricks_dev`, con esquema y volumen gestionados por el bundle.
- SQL warehouse aislado: `demo-harness-sandbox-wh` (`9e696889dea65361`).
- GitHub App: `naturapet-databricks-harness-mvp` (App ID `5075619`, Installation ID `164865183`), instalada solo en `srinconr-Crea/Naturapet_DLH`.
- Secret scope: `demo-harness-databricks`, clave `github-app-private-key`. El valor real debe ser la clave PEM de la GitHub App; nunca se versiona.

El bundle de desarrollo se despliega con `databricks bundle deploy -t dev --profile CREA_DEV`. Después se publica el código de la App con `databricks bundle run harness -t dev --profile CREA_DEV`. Para detenerla: `databricks apps stop demo-dbx-harness-mvp --profile CREA_DEV`. El archivo `iniciar-harness.bat` vuelve a encenderla y abre su URL.

## HU piloto

El formulario viene precargado con `NP-001`. El flujo comprueba `develop`, lee `notebooks/comercial/silver/04_business_derivations.ipynb`, exige una expresión exacta para `margen_sobre_costo_pct`, valida sintaxis Python y tres filas sintéticas en el warehouse aislado, pide revisión al modelo Haiku y solo entonces crea `feature/np-001-margen-sobre-costo-en-silver-comercial` y el PR. Reintentar la misma HU recupera el PR existente si lo hay.

La validación remota ejecuta una expresión SQL equivalente, sin DDL ni datos de NaturaPet. No ejecuta el notebook PySpark ni la CI del repositorio cliente. Es una limitación del piloto que debe constar en la revisión humana del PR.

## Costos

Las capturas del calculador de Databricks muestran, en Azure US East 2 y bajo un ejemplo artificial de 43.200 peticiones al mes con 1 token de entrada y 1 de salida: Sonnet 5 USD 0,78/mes y Haiku 4.5 USD 0,39/mes. De esos valores se infieren tarifas aproximadas de USD 3/15 por millón de tokens de entrada/salida para Sonnet y USD 1,5/7,5 para Haiku. Están en `config/defaults/models.yaml`; no sustituyen la factura real. El flujo registra tokens y costo estimado de las tres llamadas cuando el endpoint informa `usage`. Warehouse y App generan costos adicionales no incluidos en ese cálculo. No hay límite monetario en el MVP.

## GitHub App y secreto

La GitHub App usa un token de instalación de corta duración. Su clave privada se carga al secreto `github-app-private-key` por stdin, nunca como argumento de comando, archivo del repo o variable versionada. No ejecutes la HU hasta cargar una clave válida. La App solicita permisos `Contents` y `Pull requests` de lectura/escritura, y `Metadata` de lectura. No tiene webhooks y solo está instalada en NaturaPet.

## Incorporar otro proyecto

1. Crear un perfil YAML nuevo siguiendo `config/clients/naturapet.yaml`, con repo, rama base, rutas permitidas y contexto del caso.
2. Crear una instalación de GitHub App con alcance exclusivo para ese repositorio y un secreto dedicado.
3. Implementar un editor y pruebas deterministas para la clase de cambio del cliente. El editor piloto solo acepta la medida concreta de NaturaPet.
4. Crear o asignar sandbox remoto separado; verificar permisos de App y costo.
5. Ejecutar pruebas locales, `bundle validate`, y un piloto sin merge automático.

La configuración de otro cliente por sí sola no activa la edición de su código: el ejecutor actual conserva controles específicos de NaturaPet.
