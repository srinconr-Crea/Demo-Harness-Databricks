# Planner: capacidades y destinos OpenSpec

El planner de `propose` y `update` declara `capabilities` en el JSON de la propuesta, además de `content` y del resumen/manifiesto cuando el perfil los requiere. Cada entrada contiene exactamente `kind` (`new` o `modified`) y `path`, el identificador relativo de la capacidad. Por ejemplo: `{"kind":"modified","path":"bronze-ingestion"}`. Una ruta anidada existente como `data/bronze` conserva ese identificador exacto. No se infieren destinos a partir de la prosa ni del nombre del cambio.

El inventario autorizado entrega el contenido íntegro de las specs de base. `modified` exige una capacidad existente; `new` exige que no exista. Las rutas rechazan traversal, separadores Windows, rutas absolutas, duplicados y segmentos ajenos al formato de identificador. Declarar una capacidad nunca autoriza al desarrollador a escribir OpenSpec: el manifiesto solo controla código y pruebas dentro del perfil aprobado.

El harness pide un delta por capacidad con `capability`, `base_spec` y `output_path`: `specs/<path>/spec.md` dentro del cambio cliente. Los requisitos `MODIFIED`, `REMOVED` y los orígenes `RENAMED` deben existir en esa capacidad base; `ADDED` no puede duplicar un requisito base. Una capacidad nueva solo contiene requisitos `ADDED`. La validación estricta de la CLI comprueba los cuerpos y escenarios antes de aprobación.

En `update`, el conjunto vigente reemplaza los destinos anteriores. El gestor retira del candidato los deltas obsoletos tras generar y validar sus reemplazos, conservando la evidencia histórica en el almacén/checkpoints. Solo el conjunto vigente puede sincronizarse y archivarse. Si los bytes o destinos escritos por el runtime contradicen el contrato validado, termina con `harness_defect`; ese defecto no justifica otra vuelta del planner cliente.

El feedback debe identificar capacidad, requisito, ruta/operación, criterio afectado y evidencia pertinente. Una ampliación del contrato exige nueva revisión y aprobación. Una corrección de implementación conserva el plan aprobado y corresponde a `correcting`; una lista vacía de operaciones por sí sola no declara alcance adicional. Véanse [roles](roles.md) y [operación](../operacion.md). Las specs usadas por la HU pertenecen al checkout cliente preparado; `openspec/` de este repositorio describe el producto harness.

El adaptador histórico `plan_client_change` conserva su contrato original; los intentos nuevos utilizan los destinos tipados.
