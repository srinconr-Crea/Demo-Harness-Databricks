# Publicación de la App CostOps — 2026-10-07

Publicación posterior a la entrega inicial, autorizada por el operador. La App `demo-dbx-harness-mvp` quedó en **RUNNING** y el despliegue `01f1c25ae28c16108b65387c4622fe1f` terminó en **SUCCEEDED**.

- Código publicado: `3b4a167a5db4b59231a7033ecf19e3638e90fb98`, de `Db_Spec_Harness`.
- Fuente: `/Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-costops-20261007-3b4a167`.
- Snapshot: `/Workspace/Users/8910cd3e-32f6-4c75-b16f-b5ff3ea258d2/src/01f1c25ae28c16108b65387c4622fe1f`.
- Perfil: `CREA_DEV`; perfil cliente de instalación preservado, SHA-256 `27ac71c9b2c0c3bdea588ee77d06df20eedb228fbf47002121404f6f7f0df01f`.

Se verificaron los hashes de los **42 archivos** del snapshot, incluyendo las tarifas revisadas, contratos y persistencia de snapshots. Los bindings de recursos permanecen iguales y los hashes de **141 JSON históricos** no cambiaron. La revisión previa confirmó ejecuciones en estados finales. Al iniciar el cómputo detenido, Databricks restauró primero el despliegue anterior; una vez terminado se publicó el paquete nuevo.

La raíz, `/configuration` y la consulta de los runs `339bbcda32a848b18743cdc4c1cc06e9` y `4684261fbd554fea87185a765dc754f8` respondieron **HTTP 200**. No se crearon HUs ni se invocaron modelos para esta comprobación. El smoke verifica disponibilidad y los bytes publicados; no acredita una nueva HU completa ni una llamada facturada con el contrato v4.

Las nuevas llamadas utilizan el código publicado con tarifas revisadas y snapshot opcional v4. Los registros anteriores conservan sus costos. [App publicada](https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com).

`deployment.json` conserva IDs, hora UTC de verificación, checks HTTP y hashes del paquete. El commit que incorpora esta evidencia es documental y no altera el paquete publicado. La verificación de implementación previa permanece en `verification.md` (495 pruebas aprobadas).
