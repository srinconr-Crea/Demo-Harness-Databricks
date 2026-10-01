# Instalación piloto NaturaPet

Este directorio conserva configuración del piloto fuera del runtime común:
`client-profile.yaml` es la copia fuente aprobable y `environment.yaml` contiene
referencias operativas, sin credenciales. El perfil mantiene general_patch v3 y
su alcance funcional; `.harness/` queda protegido por el producto.

```powershell
src/agents/harness/.venv/Scripts/python.exe scripts/prepare_installation.py `
  --installation naturapet-dev --client-profile examples/naturapet/client-profile.yaml `
  --environment examples/naturapet/environment.yaml
cd .deployments/naturapet-dev
databricks bundle validate --strict -t dev --profile CREA_DEV
```

El paquete mantiene bundle `demo_harness_databricks`, App `demo-dbx-harness-mvp`,
catálogo `demo_harness_databricks_dev`, esquema de desarrollo
`dev_srinconr_demo_harness_databricks`, warehouse `demo-harness-sandbox-wh`
(`9e696889dea65361`), Job `611081415041874` e identidad sandbox
`dac4cb01-380f-4af5-b594-132d6d693beb`. No desplegar el mismo bundle_name desde
otra instalación ni renombrar esos recursos durante esta migración.

La clave privada sigue en el secret scope `demo-harness-databricks`. No copies
su valor a perfiles, paquetes, logs ni comandos. La App y el Job ya tienen
identidades distintas; comprobar ACL al recrear recursos o el runner Workspace.

Para actualizar únicamente el código de la App existente, valida el paquete,
sincroniza sus fuentes con `databricks bundle sync -t dev --profile CREA_DEV`
y despliega la App mediante `databricks bundle run harness -t dev --profile CREA_DEV`.
El despliegue completo del bundle se reserva a cambios revisados de recursos.
Antes de migrar, comprobar que no haya HUs activas. Después del despliegue:

```powershell
src/agents/harness/.venv/Scripts/python.exe scripts/smoke_sandbox.py `
  --profile CREA_DEV --app-name demo-dbx-harness-mvp --job-id 611081415041874 `
  --volume-dir /Volumes/demo_harness_databricks_dev/dev_srinconr_demo_harness_databricks/demo_harness_sandbox
.\iniciar-harness.bat demo-dbx-harness-mvp CREA_DEV
```

Ejecuta el smoke y lanzador desde la raíz del producto. Conserva paquete previo
para rollback. Los intentos antiguos sin hash requieren reintento explícito y
aprobación nueva; las publicaciones ya confirmadas no se repiten.

La preparación de OpenSpec en `srinconr-Crea/Naturapet_DLH` sigue siendo manual
y debe estar integrada en develop antes de una HU. Esta migración no crea ni
modifica `.harness/client.yaml` allí; puede incorporarse posteriormente mediante
PR humano. No ejecutar jobs, pipelines ni desplegar recursos NaturaPet.

Evidencias históricas: [OpenSpec](../../docs/evidence/2026-09-30-openspec/verification.md).
Guía común: [configuración de instalación](../../docs/configuracion-instalacion.md).
