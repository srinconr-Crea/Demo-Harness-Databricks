# Políticas

El agente Developer declara `blast_radius` con `gate_pushes: true`, siguiendo el esquema que carga Omnigent 0.15.0. La política debe probarse con solicitudes controladas de push y force push y observarse en la traza antes de atribuirle valor. Aún no hay una regla validada que limite específicamente `main`, un repositorio o `databricks bundle deploy`. Esas brechas forman parte de la evaluación. El perfil Databricks del host conserva permisos reales: una instrucción en el prompt no sustituye un límite de permisos.
