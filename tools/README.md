# Herramientas

La fase local usa Databricks CLI con `--profile CREA_DEV` para lecturas y `bundle validate --target dev`. Genie se consulta con el espacio `01f14d4947151439be25af51c40e1111` para contexto analítico de Gold. El conector `MCPDatabricksNaturaPet` disponible en Codex solo expone Genie, no edición de notebooks ni despliegue; no se presupone que Omnigent pueda cargar ese conector.
