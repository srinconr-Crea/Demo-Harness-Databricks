# Políticas

El agente Developer declara `blast_radius` con `gate_pushes: true`, siguiendo el esquema que carga Omnigent 0.15.0. Las [pruebas controladas](../docs/reproducir-gobernanza.md) mostraron que push y force push llegaron al shell, por lo que esta configuración no acredita un control efectivo. No hay una regla validada que limite específicamente `main`, un repositorio o `databricks bundle deploy`. El perfil Databricks del host conserva permisos reales: una instrucción en el prompt no sustituye un límite de permisos.
