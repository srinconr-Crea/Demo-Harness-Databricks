# Configuración de una instalación

Cada App atiende un cliente y utiliza el mismo código del producto. El operador
elige un perfil aprobado y parámetros de infraestructura antes del despliegue.
La HU no puede seleccionar cliente ni ampliar autorizaciones.

## Perfil fuente y perfil activo

El perfil fuente puede versionarse en `.harness/client.yaml` en el repositorio
cliente o conservarse en configuración operativa. Contiene repositorio, rama
base, identificadores públicos GitHub App, rutas, límites, pruebas y nombre UI;
nunca claves privadas, tokens o contraseñas. El harness no descarga ese archivo
para activar políticas. `.harness/` queda solo lectura para todas las HUs.

Una persona revisa una revisión concreta del perfil y entrega sus bytes al
empaquetador local. Este copia el archivo a
`src/agents/harness/config/deployment/client.yaml` en el paquete de instalación
y calcula SHA-256. El runtime recibe:

```text
HARNESS_CLIENT_PROFILE_PATH=config/deployment/client.yaml
HARNESS_CLIENT_PROFILE_SHA256=<sha256 de los bytes aprobados>
```

La ruta relativa se resuelve contra la raíz de la App; no es una ruta de tu PC.
El archivo debe estar entregado a la App. El hash verifica integridad de bytes;
la revisión y selección del operador constituyen la aprobación operativa.

El arranque rechaza perfil inexistente, ilegible, enlace, mayor de 128 KiB,
YAML inválido, campos desconocidos, secretos o hash ausente/divergente. Los
diagnósticos no incluyen el YAML. El perfil se carga una sola vez por proceso.
El selector legado `HARNESS_CLIENT_PROFILE=<nombre>` sigue disponible si la
instalación proporciona su YAML en `config/clients/<nombre>.yaml`; nunca se
usa como fallback. Ambos selectores simultáneos y hash sin ruta se rechazan.

## Crear el paquete

El YAML de entorno tiene `bundle_name`, `workspace_host` y `variables`. Las
variables corresponden a las declaradas en `databricks.yml`: catálogo, esquema,
almacenamiento, App, warehouse, endpoints, referencias al secreto y principal
sandbox. No incluyas credenciales. Usa un bundle_name distinto por instalación
para separar estado de despliegue; App, registros, coordinación y sandbox deben
ser exclusivos. Los endpoints pueden compartirse mediante sus ACL.

```powershell
src/agents/harness/.venv/Scripts/python.exe scripts/prepare_installation.py `
  --installation <id> --client-profile <perfil-aprobado.yaml> `
  --environment <entorno-aprobado.yaml>
cd .deployments/<id>
databricks bundle validate --strict -t dev --profile <perfil-cli>
databricks bundle deploy -t dev --profile <perfil-cli>
databricks bundle run harness -t dev --profile <perfil-cli>
```

El empaquetador no despliega, consulta repos remotos ni cambia permisos. Rechaza
destinos existentes y genera un manifiesto con revisión y hashes de fuentes y
perfil. El directorio `.deployments/` se ignora en Git; conserva el paquete y su
configuración aprobada bajo acceso operativo para reproducibilidad y rollback.
Para reconstruir, usa un id nuevo. La configuración del perfil entregado se
incluye explícitamente en sync del paquete y no en el paquete de pruebas del Job.

Antes de habilitar HUs, comprueba GitHub App, preparación OpenSpec integrada,
ACL de registros, tabla de coordinación y sandbox. El Job usa identidad distinta
de la App, sin secretos GitHub ni acceso a modelos o recursos del cliente.
Validar bundle no demuestra permisos ni ejecución real. Ejecuta la prueba
sintética positiva y negativa descrita en la guía del piloto.

## Cambiar configuración y recuperar

Cada intento y llamada conservan procedencia y hash del perfil. Los bytes viven
por referencia en `profiles/<sha256>.yaml` bajo el almacén protegido; no se
exponen como contenido por la API ni se agregan a prompts. Configura retención
sin borrar snapshots de intentos pendientes. El perfil funcional puede aportar
política acotada a un prompt, como ya ocurría, pero no su archivo íntegro.

Antes de migrar, drena HUs pendientes. Un perfil diferente o un histórico sin
hash bloquea continuación y aprobación; consulta y cancelación siguen sujetas
a la autorización habitual. Un reintento humano explícito del mismo repositorio
crea un intento nuevo, vuelve a planificar y exige aprobación nueva. Otro repo
requiere otra instalación. No reutilices autorizaciones ni borres checkpoints.

Rollback: redeplegar revisión y paquete previos con su perfil y recursos. Nunca
utilices registros de un cliente en otra instalación. El registro histórico
sigue legible sin inventar procedencia, tokens o costos.

## Capacidades y presupuestos de modelos

`config/defaults/agents.yaml` define `max_tokens` como fallback y
`role_max_tokens.planner: 64000`. `config/defaults/models.yaml` define por endpoint
`endpoint_capabilities` con `max_output_tokens` y `json_schema`; son configuración
confiable de instalación y no pueden cambiarse desde una HU. La solicitud rechaza
límites incompatibles y entrada más reserva que excedan el contexto; no degrada
silenciosamente el presupuesto. Configuraciones históricas con solo max_tokens
mantienen su fallback.

Antes de habilitar 64000 o esquema en otra instalación, comprobar el endpoint real
con una salida sintética breve y conservar metadata, solicitud efectiva,
finish_reason, usage y duración. Un techo de 64000 no exige generar esa cantidad.
El piloto CREA_DEV verificó presupuesto y esquema el 5 de octubre de 2026; esa
evidencia no garantiza la misma capacidad o latencia en otros endpoints.

Antes de actualizar, drenar trabajadores y conservar paquete previo. Lectores
antiguos pueden descartar los campos de recuperación nuevos: un rollback requiere
lectores compatibles o detener admisión hasta resolver compatibilidad. No borrar
checkpoints ni continuar históricos con una procedencia distinta.

## Inicio desde Windows

```powershell
.\iniciar-harness.bat <app-name> <perfil-cli>
```

El lanzador inicia la App indicada y consulta su URL. No tiene valores implícitos
del piloto. La UI mantiene Databricks Development Harness y toma el nombre del
cliente desde `ui.display_name`, conservando HU y descripción como entrada.

Consulta el [ejemplo NaturaPet](../examples/naturapet/README.md) para los valores
del piloto. Las evidencias anteriores conservan su ubicación y significado.
