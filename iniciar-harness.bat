@echo off
setlocal
set "DATABRICKS_AUTH_STORAGE=plaintext"
databricks apps start demo-dbx-harness-mvp --profile CREA_DEV
if errorlevel 1 (
  echo No se pudo iniciar demo-dbx-harness-mvp. Revisa el perfil CREA_DEV.
  exit /b 1
)
start "" "https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com"
endlocal
