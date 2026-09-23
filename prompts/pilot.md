# Piloto Gold: bloquear un resultado FAIL

En `notebooks/gobierno/gold/05_quality_checks.ipynb`, el notebook publica
`gold_quality_checks` y luego termina con éxito aunque un mes tenga
`gold_quality_status` diferente de `PASS`. Haz que el notebook conserve la
publicación del diagnóstico y después falle la tarea con un mensaje que
identifique los meses afectados. Incluye el estado nulo. Conserva el fallo
existente ante un resultado vacío.

Escribe primero pruebas locales para `PASS`, `FAIL`, estado nulo, resultado
vacío y orden publicación-fallo. Ejecuta la suite Python y
`databricks bundle validate --target dev --profile CREA_DEV`.

Lee `AGENTS.md` y limita el diff al cambio. No despliegues, ejecutes jobs,
escribas en Unity Catalog, fusiones ni hagas push a `main` o `develop`.
