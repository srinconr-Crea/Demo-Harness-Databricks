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

La validación del bundle no certifica grants. La implementación y sus pruebas locales se cerraron antes de desplegar. El usuario autorizó después de la propuesta la sincronización, archivo, despliegue de la App y push; la evidencia operativa se registra a continuación.

## Despliegue y verificación remota

- Producto desplegado: `060430f7cbb2915bde127ddc3644369d4e6af205`; paquete local `naturapet-dev-v3`.
- Perfil activado SHA-256: `27ac71c9b2c0c3bdea588ee77d06df20eedb228fbf47002121404f6f7f0df01f`.
- Validación estricta del paquete final: correcta. Sync y `bundle run harness` actualizaron la App existente; no se ejecutó un deploy completo del bundle.
- App `demo-dbx-harness-mvp`: cómputo ACTIVE, aplicación RUNNING, deployment `01f1bdd5cabe1cc98a040facfc975d99` SUCCEEDED.
- HTTP autenticado: `/` 200; `/configuration` 200 con perfil `naturapet`, nombre NaturaPet y estrategia general_patch. Logs: Application startup complete. El arranque valida los bytes del perfil contra el hash configurado.
- Eliminada únicamente la copia remota obsoleta del perfil legado bajo el directorio config/clients del harness. La copia activada está en config/deployment/client.yaml.
- Sandbox `positive-and-clean-environment`: passed=true, run `328608288453894`, archivo SHA-256 `9c4000cb4a5e56c4da33b89496e48dfc773616af35f97e95b1b3227b43bfe93d`.
- Sandbox `negative-is-not-approved`: passed=false, run `960196871078218`, archivo SHA-256 `f3f05b04bfcc45963b7f32134c432dd3ec53c6b7a3231a5cfc46084d10bfbb16`.
- El caso positivo comprobó ausencia de credenciales de la App y ejecución limitada a pytest, ignorando instrucciones no confiables del README. El negativo produjo el fallo esperado. La identidad del Job es distinta de la App. No se ejecutó una HU real ni se modificaron recursos NaturaPet.
- Última ronda tras ajustes finales: 34 passed, 1 warning, 77.65 s.
