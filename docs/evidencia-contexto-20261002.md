# Evidencia de gestión de contexto — 2026-10-02

Cambio: manage-hu-agent-context. Base de apply: `487eff3626b08296aff72016763cc37cae75337a`, rama `Db_Spec_Harness`. El usuario autorizó publicar en esta rama existente y actualizar la App con perfil `CREA_DEV`; esta instrucción sustituye para este trabajo del producto la recomendación de PR feature. No se publica ni despliega un candidato cliente.

## Alcance comprobado

Las rutas activas son ConversationEngine → contextual_answer para explore/apply/verify, propose_client_change → contextual_answer para propose/update, y la llamada asesora independiente. Se integraron las cinco; sync/archive siguen deterministas. ModelClient registra procedencia en llamadas exitosas y fallidas; start_server la conserva en AgentCallContract. Almacén local/volumen comparte implementación de snapshots protegidos. La UI conserva acciones y contrato público. No se depende de agent.py, graph.py, tools.py ni eval/ del scaffold.

La diferencia con el diseño conceptual es deliberadamente conservadora: no hay ranking semántico ni extracción universal. Se preserva el texto original y se verifican decisiones estructuradas inequívocas; el reconocedor explícito de cero/compras sirve al escenario especificado, sin afirmar detección general de contradicciones. La selección depende de contrato, permisos, hashes y duplicados exactos. Nuevos dominios necesitarán sus reglas explícitas y pruebas, o aclaración humana.

## Verificación local

La suite ampliada terminó con 223 passed, 1 skipped y un timeout ambiental de git show (1484,96 s). El único caso fallido, publicación automática con timeout asesor, pasó aislado: 1 passed en 30,95 s. Quedan así verificados los 224 casos ejecutables, sin afirmar que la ejecución agrupada tuvo cero fallos. El flujo con gestor habilitado y CLI OpenSpec real también pasó aislado en 157,88 s, hasta PR simulado, con base avanzada, reinicio y aprobación nueva. Las últimas invalidaciones de cache y comparación reforzada de procedencia se verificaron con 24 casos específicos aprobados y el flujo de recuperación aprobado aislado.

- Suite de compatibilidad con política deshabilitada: 198 passed, 1 skipped; 767 s. La omitida es el smoke PySpark sin entorno Spark local.
- Pruebas específicas iniciales: 25 passed. Después de reforzar comparación del texto/actor/estado con el original, otras 25 passed.
- Repetición final: 24 passed y un timeout ambiental de git show al recuperar checkpoint. Ese mismo flujo pasó al repetirlo aislado: 1 passed en 34,44 s. No se amplió el timeout del producto.
- OpenSpec: cambio válido con --strict; 15 specs principales válidas después de sync.
- Bundle de instalación: validate --strict -t dev con CREA_DEV, aprobado. No se modificó infraestructura.
- Ruff de los módulos nuevos y pruebas específicas: aprobado. La ejecución amplia detecta deuda previa de estilo/imports en módulos y pruebas existentes; no se presenta como suite de lint global aprobada. git diff --check no presenta errores.

El primer intento de suite con ruta larga de Windows sufrió MAX_PATH en snapshots; se repitió usando basetemp corto. Los permisos del sandbox local sobre TemporaryDirectory obligaron a ejecutar las pruebas con la aprobación automática de herramientas. Son limitaciones ambientales registradas, no cambios en los controles del harness.

## Comparación y estrés

scripts/measure_context.py reproduce las mismas cuatro solicitudes read_file y la misma respuesta final en ambos modos, conservando aclaración original y fuente. El modo baseline envió 123772 bytes en cinco llamadas; el gestor, 58134 bytes en las mismas cinco llamadas, incluyendo system. Cache: tres hits y un miss. La latencia es medición local con stub y depende del equipo; el JSON adjunto conserva el valor observado. Usage y costo son ausentes en ambos modos. No se deduce ahorro facturado ni latencia del endpoint.

El estrés ejecuta 40 turnos, 39 sustituciones explícitas, 40 reconstrucciones desde snapshots de disco y comprobación de bloqueo por presupuesto. Conserva todos los originales y una regla vigente. Las pruebas adicionales cubren 40 resultados duplicados, modificación del candidato, altas/bajas del inventario, permiso revocado, origen alterado, conflicto, TTL/LRU/bytes y decisión humana antigua. No equivale a 40 llamadas reales a Sonnet ni a una garantía universal.

## Verificación remota y límites

Workspace: adb-7405606739630987.7.azuredatabricks.net, perfil CREA_DEV. Job `611081415041874`, `[dev srinconr] demo_harness_sandbox`, identidad distinta de la App. Volumen demo_harness_sandbox del catálogo demo_harness_databricks_dev. Warehouse `9e696889dea65361`, demo-harness-sandbox-wh.

- Run positivo `953412753433157`: dos pruebas pasan; entorno sin credenciales y sin ejecutar instrucción maliciosa del README.
- Run negativo `610792323143424`: falla sintética detectada y passed=false; no se convierte en aprobación.
- Tabla demo_harness_run_state: consulta agrupada sin filas antes de activación. No había intentos que drenar.

La App existente es demo-dbx-harness-mvp. El paquete usa el perfil cliente instalado sin cambios, los mismos recursos vinculados y context.enabled=true únicamente en la instalación. El default versionado del producto permanece false. Fuente nueva: /Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-context-20261002. El snapshot previo para rollback es /Workspace/Users/8910cd3e-32f6-4c75-b16f-b5ff3ea258d2/src/01f1be7f3efa156ca0df1c6b3eefcc98. El Job conserva su fuente anterior; no necesita una actualización para este cambio.

Despliegue `01f1be9bb4d719a7b01994e5ce6c1e3c`: SUCCEEDED, App iniciada el 2026-10-02 a las 19:59:10 UTC. GET autenticados / y /configuration devuelven HTTP 200; el archivo remoto de política confirma enabled=true. No se necesitó cambiar recursos ni consultar secretos. Las tres deltas se verificaron contra sus specs principales antes de mover el cambio a openspec/changes/archive/2026-10-02-manage-hu-agent-context; conserva sus 26 tareas completas y .openspec.yaml.

No se ejecutó una HU contra NaturaPet, ni se cambiaron sus tablas/jobs/pipelines. El cambio de limpieza remove-unused-harness-scaffold continúa pendiente y queda fuera de esta publicación.
