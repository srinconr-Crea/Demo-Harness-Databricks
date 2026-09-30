# Tasks

## 1. Política y edición general

- [x] 1.1 Añadir política prefixes/repository, rutas solo lectura y prohibidas, extensiones y operaciones explícitas con compatibilidad de perfiles existentes; verificar contratos y fixtures de general_patch y silver_safe_ratio en tests/test_contracts.py y tests/test_general_patch.py.
- [x] 1.2 Centralizar permisos de lectura/escritura y aplicarlos a patch, checkout, snapshots, restauración y publicación; verificar archivos raíz, nombres protegidos exactos, prefijos similares, enlaces, traversal, unidad Windows y rechazos sin edición parcial.
- [x] 1.3 Filtrar rutas prohibidas del paquete sandbox conservando dependencias y pruebas de lectura autorizada; verificar integridad, hashes, límites y ausencia de secretos con tests/test_sandbox_job.py.
- [x] 1.4 Documentar política y ejemplo general en docs/operacion.md y fixtures; verificar que el perfil NaturaPet no amplía su alcance implícitamente y la activación general exige pruebas configuradas.

## 2. Contexto y planificación

- [x] 2.1 Implementar contexto de árbol, búsqueda y lectura con presupuestos, hashes y truncamiento; verificar consultas dirigidas, rutas solo lectura, rechazo de secretos/enlaces y agotamiento sin fuga de contenido.
- [x] 2.2 Integrar solicitudes tipadas en explorer/planner/developer y separar prompts y contratos por estrategia; verificar rondas acotadas, registro de llamadas/costos y contrato ratio conservado en pruebas de modelos y conversación.
- [x] 2.3 Persistir resumen natural, manifiesto de archivos/operaciones y plan de pruebas dentro del hash aprobado; verificar rechazo de archivo adicional y de aprobaciones obsoletas en tests/test_openspec.py y tests/test_conversation.py.
- [x] 2.4 Acumular aclaraciones y reevaluar explore antes de propose; entregar todos los specs delta y tareas de la revisión a developer/verificador; verificar preguntas sucesivas y HU clara sin esperas innecesarias.
- [x] 2.5 Documentar presupuestos, contratos y significado de cambios previstos en docs/agents y operación; verificar coherencia con prompts y payloads reales.

## 3. Adaptadores y sandbox

- [x] 3.1 Crear registro confiable de adaptadores y selección por extensión, eliminación e impacto configurado; verificar matriz de pruebas para código, configuración, dependencias y ausencia de comandos arbitrarios de la HU.
- [x] 3.2 Añadir validación SQL Databricks, YAML/JSON con esquemas configurados, TOML, Markdown y texto; fijar dependencias y verificar fixtures válidas/invalidas por tipo y bloqueo sin prueba funcional requerida.
- [x] 3.3 Separar notebook_validate de python_compile y validar esquema, lenguaje, celdas y magias admitidas; verificar notebooks Python/SQL mixtos y rechazo de contenido inválido o lenguaje sin cobertura obligatoria.
- [x] 3.4 Extender runner con pytest_sandbox y databricks_bundle_validate sobre targets e includes autorizados, sin deploy; verificar bundle válido/inválido, suites fallidas, objetivos ausentes, timeout, salida acotada y uso exclusivo de identidad sandbox.
- [x] 3.5 Vincular evidencia al candidato, revisión y adaptadores ejecutados; verificar que indisponibilidad obligatoria bloquea y que pasar sintaxis no sustituye pruebas funcionales.
- [x] 3.6 Actualizar dependencias y recursos del Job si corresponde y documentar matriz de cobertura y configuración por cliente; verificar instalación reproducible y bundle validate --strict del harness si cambia infraestructura.

## 4. Haiku asesor

- [x] 4.1 Separar resultado asesor y captura acotada de fallo de Haiku del gate Sonnet/pruebas; verificar rechazo, timeout y JSON inválido sin bloqueo ni incremento de correction_count, y fallo Sonnet bloqueante.
- [x] 4.2 Persistir advisory, referencias de llamadas, errores redactados y costos disponibles; verificar recuperación histórica, ausencia de usage y que errores de integridad/persistencia no se silencian como fallos asesores.
- [x] 4.3 Documentar rol asesor y gates obligatorios en README y docs/agents; verificar que mensajes no presentan revisión no disponible como aprobada.

## 5. Publicación automática y compatibilidad

- [x] 5.1 Versionar modalidad de autorización: nuevos intentos por plan e históricos con revisión de diff original; verificar lectores y reanudación de awaiting_diff_review sin fabricar aprobaciones.
- [x] 5.2 Transicionar del candidato verificado/sincronizado/archivado a publishing automáticamente y exponer diff consultable; verificar flujo con una aprobación del plan y sin acción de aprobación final.
- [x] 5.3 Comprobar manifiesto, plan, evidencia, SHA base y bytes exactos antes de publicar; verificar manipulación de candidato, base avanzada y nueva aprobación, rama divergente y ausencia de diff.
- [x] 5.4 Mantener publicación idempotente tras reinicio o fallo parcial; verificar reutilización exacta de rama/PR y rechazo de archivos remotos adicionales con pruebas GitHub y conversación.
- [x] 5.5 Actualizar README, docs/operacion.md, AGENTS.md y contexto OpenSpec con autorización acordada y migración; verificar que siguen exigiendo feature/*, revisión/merge humano y ausencia de deploy automático.

## 6. Conversación y checklist

- [x] 6.1 Presentar propuesta natural y cambios previstos, preguntas y comentarios; mover eventos técnicos, artefactos, costos y diff a detalle bajo demanda; verificar interfaz para HU clara, ambigua y update.
- [x] 6.2 Conservar borrador de comentarios durante polling y actualización por run/revisión; verificar escritura intercalada con eventos y reinicio de revisión sin pérdida de texto.
- [x] 6.3 Emitir evidencia diferenciada para sync y archive y construir checklist durable con fecha America/Bogota; verificar fallo parcial, reintento, revisión nueva y fases no aplicables sin OK ficticio.
- [x] 6.4 Mostrar enlace al PR, recomendaciones Haiku y checks GitHub separados; verificar estados passed/pending/failed/unavailable y que no se detiene automáticamente la App.
- [x] 6.5 Actualizar guía de interfaz y recuperación; verificar acciones/API vigentes y autorización de consultas en tests/test_conversation_webapp.py.

## 7. Verificación integral

- [x] 7.1 Ejecutar suite local completa y openspec validate --strict del cambio; registrar resultados y resolver fallos, sin publicar código con pruebas pendientes.
- [x] 7.2 Verificar recorrido completo en cliente sintético: explorar, actualizar, aprobar, editar múltiples tipos, probar, recibir advisory, sync/archive y PR automático; registrar evidencia y checklist sin usar recursos NaturaPet ni merge.
- [x] 7.3 Verificar negativos integrados de ruta protegida, prueba ausente/fallida, base avanzada y recuperación después de archive/publicación; registrar evidencia de bloqueo y ausencia de PR duplicado.
