# Evidencia del piloto NP-001 (preparación)

**Estado:** la ejecución de extremo a extremo y el PR de NaturaPet están pendientes de cargar la clave privada de la GitHub App en el secreto `demo-harness-databricks/github-app-private-key`. El secreto contiene temporalmente un marcador inválido; no hay PR del piloto.

## Verificaciones realizadas

- Se clonó `develop` de NaturaPet en una carpeta temporal de lectura, sin modificar su repositorio. El editor produjo una única línea nueva en `notebooks/comercial/silver/04_business_derivations.ipynb`; el diff unificado tuvo 10 líneas y la celda resultante compiló como Python. La medida apareció exactamente una vez.
- El SQL warehouse aislado `demo-harness-sandbox-wh` ejecutó tres filas sintéticas: costo 10 y margen 20 dio 2; costo cero y costo NULL dieron NULL. La consulta terminó `SUCCEEDED` (statement `01f1b8fa-1f0b-126b-b35c-495070b05af7`). No usó tablas ni DDL de NaturaPet.
- Sonnet 5 respondió una invocación mínima con 22 tokens de entrada y 9 de salida. Haiku 4.5 respondió con 18 de entrada y 13 de salida. El endpoint Sonnet 5 rechazó `temperature`; el cliente del harness ya omite ese parámetro. Haiku devolvió JSON en bloque Markdown; el parser acepta ese formato.
- La App arrancó en Databricks, mostró el formulario único y guardó una ejecución de prueba en el volumen UC mediante Files API. La ejecución de prueba fue rechazada deliberadamente por no corresponder a la medida piloto. Después de verificar el arranque, la App quedó detenida. El warehouse aislado también quedó detenido.
- El commit `3325c944ff59affade21c1398fbc70aa480bcaab` está publicado en la rama `MVP-Databricks-Harness`. La suite local cerró con 20 pruebas aprobadas, lint aprobado y `databricks bundle validate` aprobado.

Con las tarifas aproximadas inferidas de las capturas, las dos invocaciones mínimas costarían unos USD 0,0003255 en conjunto. Es una estimación de diagnóstico; el costo de una HU real y el de App/warehouse se medirán después.

## Pendientes para cerrar el piloto

1. Cargar el PEM auténtico de la GitHub App en el secreto del harness sin versionarlo ni imprimirlo.
2. Encender la App, enviar la HU precargada y verificar las tres llamadas a modelos, la prueba remota, la rama `feature/*` y el PR hacia `develop`.
3. Revisar el diff y los checks del PR. El SQL remoto comprueba la fórmula, pero no ejecuta el notebook PySpark completo; la revisión humana debe tenerlo presente.
4. Volver a detener la App y el warehouse después de la ejecución.
