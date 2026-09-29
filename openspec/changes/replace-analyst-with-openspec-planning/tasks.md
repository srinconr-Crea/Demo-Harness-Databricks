# Tasks

## 1. CLI y aislamiento

- [x] 1.1 Fijar versión de OpenSpec y preparar su instalación junto con Node en la App; verificar `openspec --version` y `databricks bundle validate --strict -t dev`.
- [x] 1.2 Implementar `harness/openspec.py` con ejecución sin shell, raíz temporal por intento, límites de tiempo/salida y fallo cerrado; verificar pruebas de rutas, timeout y CLI ausente.
- [x] 1.3 Cargar los archivos OpenSpec del commit base cliente y ejecutar `openspec init --tools none` en cada workspace antes del desarrollador; verificar clientes con y sin OpenSpec y aislamiento entre perfiles.

## 2. Planner y controles

- [x] 2.1 Definir salida estructurada del planner y routing `planner/developer/verifier` con `planner: databricks-claude-sonnet-5`; verificar modelo fijado, validación de respuestas y lectura de llamadas históricas `analyst`.
- [x] 2.2 Generar propuesta, specs, diseño y tareas con `openspec instructions ... --json` y Sonnet 5; verificar que la inicialización precede la llamada al desarrollador, un intento produce cuatro artefactos y un reintento usa otra identidad.
- [x] 2.3 Validar los artefactos con `openspec validate --strict` y cotejar el manifiesto con perfil, estrategia y expresión deterministas; verificar rechazo por archivo, modelo, expresión y estructura inválidos antes de editar.
- [x] 2.4 Sustituir el gate `analyst` de `workflow.py` por la planificación validada y entregar sus artefactos al desarrollador y al verificador; verificar la secuencia y el rechazo del verificador en `tests/test_workflow.py`.
- [x] 2.5 Actualizar `docs/agents/roles.md` y el contrato de agentes para reflejar `planner`; verificar que la documentación coincide con el routing y la suite de roles.

## 3. Persistencia y consulta

- [x] 3.1 Ampliar los contratos de intento para referencias, hashes y estado de validación, manteniendo compatibilidad con JSON existentes; verificar pruebas de deserialización histórica.
- [x] 3.2 Registrar cada llamada Sonnet 5 del planner en `runs/agent_calls/*.json` mediante el callback actual, con tokens y costo estimado cuando exista uso; verificar varias llamadas, fallo y ausencia de usage.
- [x] 3.3 Guardar artefactos completos por intento en almacenamiento local y volumen UC, con redacción y ACL actuales; verificar recuperación, hashes y aislamiento entre intentos en pruebas de store.
- [x] 3.4 Exponer referencias y estado de planificación en `/runs/{run_id}` y documentar su lectura en `docs/operacion.md`; verificar respuestas completas, fallidas y reintentos en pruebas web.

## 4. Publicación controlada

- [x] 4.1 Exigir en cada perfil un prefijo OpenSpec confiable y validar sus rutas con la política actual; verificar que un perfil sin prefijo no inicia desarrollo.
- [x] 4.2 Extender GitHub App para publicar código y documentos autorizados en un commit coherente y comparar el conjunto completo al reutilizar ramas; verificar éxito, divergencia y archivos adicionales en pruebas de integración.
- [x] 4.3 Archivar el cambio validado tras implementar y probar, preparar inicialización, specs resultantes y documentos históricos para el cliente; verificar el conjunto exacto del PR tanto con cliente nuevo como ya inicializado.
- [x] 4.4 Documentar la inicialización automática del repositorio cliente y la revisión humana del PR; verificar que el procedimiento no indica merge ni despliegue automático.

## 5. Verificación de integración

- [x] 5.1 Ejecutar la suite local completa y `databricks bundle validate --strict -t dev`; registrar resultados y corregir fallos antes de publicar el harness.
- [x] 5.2 En entorno aislado, ejecutar una historia sintética con cliente sin OpenSpec y comprobar inicialización previa al desarrollo, artefactos en el PR, gates, llamadas Sonnet 5 y costos JSON sin merge; registrar evidencia.
