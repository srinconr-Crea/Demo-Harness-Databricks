# Editor y cobertura del manifiesto

El manifiesto aprobado define el efecto permitido respecto del SHA base: crear
un archivo ausente, modificar uno existente o eliminarlo. La operación del
developer actúa sobre los bytes actuales del checkout. Durante una corrección,
un archivo creado en el intento puede recibir `modify` con su hash actual y
conservar `create` como efecto acumulado. Una entrada `modify` de la base no
autoriza `delete`, ni una ruta admitida por el perfil queda autorizada por estar
fuera del manifiesto.

La respuesta contiene `operations` y una entrada `coverage` por cada ruta del
manifiesto. `applied` corresponde a una operación del lote propuesto;
`already_conformant` requiere `sha256` de los bytes actuales; `blocked` requiere
un motivo y detiene la aplicación. Para una eliminación ya realizada,
`already_conformant.sha256` identifica los bytes exactos de la base, y el editor
comprueba además que el archivo existía en esa base y está ausente del candidato.
La cobertura no acredita por sí misma corrección funcional: las pruebas y Sonnet
siguen siendo obligatorios.

Por ejemplo, si el manifiesto aprobó modificar `src/a.py` y crear
`tests/test_a.py`, una corrección puede devolver solo `modify` de `src/a.py`,
con `coverage` de estado `applied` para esa ruta y `already_conformant` con el
hash actual para el test. El conjunto sujeto a pruebas conserva ambos archivos
del diff acumulado. Si la corrección modifica el test creado, utiliza `modify`
con `expected_sha256` actual aunque su entrada aprobada siga siendo `create`.

`validate_manifest_coverage` valida el candidato proyectado sin escribir y
devuelve las rutas de código que difieren de la base. Rechaza cobertura omitida,
duplicada, fuera de manifiesto, hashes obsoletos, estados incompatibles y cambios
acumulados no aprobados antes de aplicar el lote. Los límites de archivos se
comprueban sobre manifiesto, lote y diff acumulado; los límites de bytes se
comprueban sobre el lote y el acumulado, contando por archivo cambiado el mayor
tamaño entre base y candidato, incluida la eliminación. Los artefactos OpenSpec
siguen bajo su gestor propio.

Una lista `operations=[]` con cobertura completa y válida puede pasar a verify
desde la orquestación. El editor de operaciones no recibe ese lote vacío y
conserva su rechazo original. La ausencia de operaciones o cobertura no concede
conformidad ni amplía permisos. La validación previa conserva atomicidad frente
a lotes inválidos; el lease del workflow mantiene exclusivo el checkout durante
la validación y aplicación.
