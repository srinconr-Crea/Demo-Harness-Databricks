# Instrucciones de la demo

Trabaja únicamente sobre una clonación nueva de `Naturapet_DLH/develop` y su rama `codex/demo-gold-gate-omnigent`. Lee el `AGENTS.md`, `databricks.yml`, `resources/` y los notebooks involucrados antes de editar.

No despliegues bundles, ejecutes jobs, importes notebooks al workspace, cambies `qa` o `prod`, ni fusiones PRs. Usa siempre `--profile CREA_DEV` en Databricks CLI. Ejecuta pruebas locales y `databricks bundle validate --target dev --profile CREA_DEV` antes de proponer el PR. Mantén credenciales fuera de Git.

Architect delimita el cambio, Developer implementa y Reviewer inspecciona el diff y la evidencia. Registra qué rol intervino y qué política permitió, rechazó o pidió aprobación.
