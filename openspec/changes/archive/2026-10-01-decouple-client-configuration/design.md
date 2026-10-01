# Design

## Context

Ver `proposal.md` para la motivación. `start_server.py` carga actualmente un singleton `PROFILE` desde `config/clients/<HARNESS_CLIENT_PROFILE>.yaml`. `load_profile` ya valida el modelo `ClientProfile`; el selector por nombre limita traversal. El target dev incluye cliente, workspace, App e IDs concretos. El bundle entrega `src/agents/harness` como código de App. El lanzador fija App, perfil CLI y URL.

La UI ya obtiene `display_name` desde `/configuration`; no necesita rediseño para separar producto y cliente. El intento conserva nombre y versión del perfil, pero no sus bytes ni hash. Los controles actuales protegen `.agents/`, `.github/`, OpenSpec y AGENTS.md; `.harness/` requiere protección determinista adicional.

## Goals / Non-Goals

**Goals:**
- Mantener una configuración inmutable durante la vida del proceso y reproducible al recuperar intentos.
- Hacer que un operador pueda producir dos paquetes de instalación desde una misma revisión del producto, cambiando únicamente perfiles y parámetros de entorno.
- Continuar el piloto con los recursos existentes y dejar un procedimiento genérico verificable.

**Non-Goals:**
- Selector multicliente, recarga en caliente, servicio de onboarding, aprovisionamiento automático de permisos o facturación.
- Cambiar el flujo OpenSpec del cliente, modelos, alcance funcional del piloto o implementar autenticación aislada de bundle validate en el Job.
- Modificar NaturaPet o desplegar infraestructura como efecto de generar estos artefactos.

## Decisions

### 1. Copia aprobada de perfil, entregada en el paquete

El perfil fuente puede vivir en `.harness/client.yaml` del cliente o en configuración operativa externa. El operador elige una revisión, revisa sus autorizaciones y entrega sus bytes al empaquetador. El harness no descubre el repositorio a partir de un perfil remoto: el perfil aprobado ya contiene repo, base e instalación GitHub. La aprobación operativa se expresa mediante la selección explícita del archivo y hash esperado en la configuración de despliegue; el hash acredita integridad, no identidad humana ni una firma digital.

Añadir un cargador de selección que devuelve perfil y procedencia, sin colocar metadatos de carga dentro del YAML funcional. Modo externo: `HARNESS_CLIENT_PROFILE_PATH` y `HARNESS_CLIENT_PROFILE_SHA256`. Una ruta relativa se resuelve contra ROOT de la App y debe quedar dentro de ROOT; una absoluta apunta a un archivo entregado por el operador. Rechazar traversal relativo, enlaces, archivos no regulares, más de 128 KiB, hash inválido y YAML que incumpla el contrato. Leer una vez, calcular hash sobre esos mismos bytes y validarlos; no reabrir para calcular y parsear por separado. Mantener bytes y perfil en memoria, sin recarga en caliente ni lectura desde la HU. Nunca permitir credenciales privadas en el contrato del perfil.

El modo legado mantiene el selector por nombre y el directorio esperado, útil para instalaciones existentes. No se selecciona por defecto ni recupera un error externo. El producto deja de distribuir NaturaPet en config/clients; una instalación legada puede conservar su archivo provisionado hasta migrarse. Registrar y documentar el modo legado sin fijar aún una fecha de retirada.

Alternativas: leer directamente del checkout introduciría política controlable por contenido cliente y una dependencia circular para autenticación; usar un volumen montado añade recursos y ACL para el archivo sin aportar beneficio a este piloto. El empaquetado permite revisión y rollback por artefacto.

### 2. Ensamblado local por instalación y bundle genérico

Crear un script local de preparación que reciba id de instalación, perfil fuente y parámetros de entorno y genere un directorio ignorado `.deployments/<id>/`. Validar id y destino y rechazar sobrescritura accidental. Copiar de forma selectiva fuentes y definiciones del bundle; excluir .git, secretos, .venv, node_modules, registros y otros clientes. Generar `src/agents/harness/config/deployment/client.yaml` con los bytes aprobados y una configuración de variables del bundle para ese paquete. ROOT runtime resuelve `config/deployment/client.yaml`; esa ruta no depende del directorio Windows del operador.

El paquete usa la misma revisión de Python y HTML para cualquier cliente. `databricks.yml` y resources del producto contienen variables y defaults genéricos; las variables externas proveen host, App, almacenamiento, warehouse, identidad sandbox y referencias a secretos/endpoints. Un bundle generado puede contener valores concretos del entorno porque es un artefacto operativo, no código fuente común. El empaquetador no consulta GitHub, otorga permisos, ejecuta deploy ni transmite el perfil. Documentar los comandos de validación y despliegue desde el paquete.

Registrar en un manifiesto local revisión del producto, hash de perfil y parámetros no secretos. Mantener configuración operativa aprobada y paquete previo para rollback. El ejemplo NaturaPet conserva los parámetros actuales fuera del bundle genérico; otro ejemplo usa valores sintéticos. Los paquetes temporales no se incluyen en sync del producto ni en Git.

Alternativas: editar targets por cliente conserva acoplamiento en el producto; inyectar solamente una ruta sin entregar el archivo deja una instalación incompleta. No renombrar los recursos existentes del piloto en esta migración.

### 3. Aislamiento de instalación

Cada instalación se enlaza a un repositorio y tiene sus registros, tabla de coordinación y sandbox propios; no reutilizar un almacén existente para otro cliente. Las identidades de App y sandbox son distintas. Los endpoints de modelos pueden ser compartidos mediante permisos separados; el sandbox no recibe permisos de modelos ni GitHub. Para el piloto se conservan nombres demo_harness, warehouse autorizado e IDs actuales. El segundo cliente se demuestra localmente sin crear recursos cloud adicionales.

La identidad de instalación y recursos son configuración del operador, no campos autorizables por OpenSpec. La documentación incluye comprobaciones de ACL y prueba sintética real antes de habilitar una instalación nueva. La preparación de OpenSpec sigue con siete workflows versionados, PR y merge humano previo.

### 4. Protección de configuración y procedencia durable

Agregar `.harness/` a rutas protegidas deterministas, cubriendo editor, estado final, manifiesto y GitHub publicación, aunque la política de alcance sea repository. No leer el YAML del checkout como autoridad ni incluir la copia activada en el paquete del Job.

Añadir procedencia opcional a contratos de intento y llamada: nombre, versión, repo, modo y SHA-256 de perfil. Guardar snapshot sin secretos en almacenamiento protegido por hash y enlazarlo al intento; no devolver los bytes desde `/configuration` ni incluirlos en prompts. Validar que los campos nuevos atraviesan checkpoints y joins por run_id/attempt_id/call_id. Mantener lectura de contratos históricos sin backfill.

Antes de etapas, aprobaciones y publicación, comparar hash y repositorio del intento con el perfil en memoria. Un intento sin hash o con discrepancia queda bloqueado para acciones dependientes de política, pero conserva consulta y cancelación conforme a identidad y revisión actuales. El reintento explícito en el mismo repositorio puede crear un intento nuevo bajo el perfil vigente, volviendo a explorar y planificar y exigiendo aprobación; nunca restaurar autorización anterior como vigente. Si el repositorio cambió, rechazar el reintento en esa instalación. Registrar el motivo de rechazo sin reescribir intentos históricos. La comprobación debe existir también en el worker y no solo en HTTP.

Alternativa: confiar en nombre/versión no detecta cambios de bytes sin incremento de versión. Cambios de comentarios también modifican el hash; preferimos identidad exacta y cambio de configuración deliberado para esta etapa.

### 5. Presentación y operación

Mantener título y cabecera Databricks Development Harness y mostrar el cliente desde ui.display_name. Conservar formulario de dos campos; retirar hints obsoletos del ejemplo o documentar que no forman parte del contrato visual actual. Parametrizar el lanzador con App y perfil CLI, consultar la URL mediante salida estructurada y abrir solo una URL válida devuelta para la App; no conservar valores por defecto del piloto. Preservar comportamiento autorizado de credenciales sin ampliar su persistencia.

README y guía genérica explican producto, configuración y ciclo de HU. `examples/naturapet/` contiene perfil y guía de parámetros actuales; evidencia histórica conserva ubicación y referencias para no alterar su significado. Menciones de cliente en ejemplos, pruebas del piloto e históricos son legítimas; el criterio es ausencia de identidad cliente en defaults activos, no borrar todo texto NaturaPet.

## Risks / Trade-offs

- Más instalaciones implican operación y costo de recursos separados -> una sola instalación cloud en el piloto; documentar el costo operativo sin prometer costos fijos.
- Archivo externo mal entregado o configuración ambigua -> validación local del paquete y arranque con fallo cerrado.
- Cambiar perfil invalida una HU pendiente -> drenar intentos antes de migrar; reintento explícito y plan aprobado nuevo si falta procedencia o cambia política.
- Colisión de paths o recursos entre paquetes -> id validado, destino exclusivo y checklist de variables y ACL; prueba de dos paquetes.
- El paquete conserva información del cliente -> mantenerlo ignorado y bajo acceso operativo; excluirlo de prompts y sandbox y aplicar retención del operador.
- Scripts auxiliares dependen del target actual -> revisar `scripts/prepare_app_only_deployment.py`, scripts de provisión y documentación al separar variables, con pruebas de configuración renderizada.

## Migration Plan

1. Implementar cargador y procedencia compatibles; añadir protección .harness y pruebas antes de mover el perfil.
2. Introducir empaquetador y ejemplos; trasladar perfil NaturaPet fuera de runtime genérico y conservar sus parámetros actuales en guía de piloto. No crear .harness/client.yaml en NaturaPet durante este cambio; esa fuente es opcional y requiere mantenimiento humano del cliente.
3. Generar paquetes NaturaPet y cliente sintético a partir del mismo producto; probar rutas, hash, UI, política y recuperación local sin credenciales reales.
4. Ejecutar suite y validar estrictamente bundle generado del piloto con recursos existentes. No ejecutar deploy ni alterar permisos como parte de las pruebas locales. Documentar el bloqueo si no hay autenticación operativa para validar.
5. Antes de una migración cloud posterior, el operador revisa paquete y ACL y comprueba que no haya HUs pendientes; despliega a la misma App del piloto y realiza prueba sintética del sandbox. Guardar evidencia de esta operación aparte de la evidencia local.
6. Rollback: redeplegar revisión y paquete previos con perfil y recursos originales. Mantener snapshots y registros; no intentar continuar intentos creados con un hash distinto ni borrar checkpoints.

Las llamadas adicionales de modelos no son necesarias para cargar o comprobar configuración; conservar el registro de tokens y costos por llamada existente.
