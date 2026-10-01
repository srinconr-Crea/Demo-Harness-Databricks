# Configuración independiente por cliente

Cambio: `decouple-client-configuration`. Rama solicitada: `Db_Spec_Harness`.

## Validación local

- Suite completa: 183 passed, 1 skipped, 1 warning, 743.71 s. La advertencia existente corresponde a Starlette/httpx.
- Pruebas enfocadas de configuración, aceptación, recuperación y almacenamiento: 43 passed, 117.89 s.
- Dos clientes sintéticos recorrieron planificación, aprobación, aplicación, pruebas y publicación simulada usando el mismo producto. No se modificó el repositorio NaturaPet.
- OpenSpec y bundle del paquete piloto: validación estricta satisfactoria.
- Revisión del diff y manifiesto: configuración del cliente fuera de defaults genéricos; perfiles entregados con hash; paquete y runtimes excluidos de Git; ningún secreto inline.

## Preparación operativa

El almacén remoto del piloto tenía dos registros completos y uno fallido, sin HUs pendientes. Se conservan sus registros, recursos demo_harness, App y warehouse sintético. Los históricos siguen legibles; un nuevo intento requiere el perfil vigente y nuevas aprobaciones.

El rollback utiliza la revisión anterior del producto y su configuración legada explícita, o el paquete anterior con su perfil y hash correspondientes. No se borran checkpoints ni se heredan aprobaciones entre políticas.

La validación del bundle no certifica grants. La implementación y sus pruebas locales se cerraron antes de desplegar. El usuario autorizó después de la propuesta la sincronización, archivo, despliegue de la App y push; la evidencia operativa se añadirá tras esa ejecución.
