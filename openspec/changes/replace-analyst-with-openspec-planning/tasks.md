# Tasks

## 1. CLI y aislamiento

- [ ] 1.1 Fijar versión de OpenSpec y preparar su instalación junto con Node en la App; verificar `openspec --version` y `databricks bundle validate --strict -t dev`.
- [ ] 1.2 Implementar `harness/openspec.py` con ejecución sin shell, raíz temporal por intento, límites de tiempo/salida y fallo cerrado; verificar pruebas de rutas, timeout y CLI ausente.
- [ ] 1.3 Crear la configuración OpenSpec temporal a partir del perfil cliente y del commit base, sin copiar el contexto de este repositorio; verificar pruebas con dos perfiles aislados.

## 2. Planner y controles

- [ ] 2.1 Definir salida estructurada del planner y routing `planner/developer/verifier`; verificar validación de respuestas y lectura de llamadas históricas `analyst` en pruebas de contratos.
- [ ] 2.2 Generar propuesta, specs, diseño y tareas con `openspec instructions ... --json` y Foundation Model API; verificar que un intento produzca cuatro artefactos y un reintento use otra identidad.
- [ ] 2.3 Validar los artefactos con `openspec validate --strict` y cotejar el manifiesto con perfil, estrategia y expresión deterministas; verificar rechazo por archivo, modelo, expresión y estructura inválidos antes de editar.
- [ ] 2.4 Sustituir el gate `analyst` de `workflow.py` por la planificación validada y entregar sus artefactos al desarrollador y al verificador; verificar la secuencia y el rechazo del verificador en `tests/test_workflow.py`.
- [ ] 2.5 Actualizar `docs/agents/roles.md` y el contrato de agentes para reflejar `planner`; verificar que la documentación coincide con el routing y la suite de roles.

## 3. Persistencia y consulta

- [ ] 3.1 Ampliar los contratos de intento y llamada para referencias, hashes, estado de validación y rol planner, manteniendo compatibilidad con JSON existentes; verificar pruebas de deserialización histórica.
- [ ] 3.2 Guardar artefactos completos por intento en almacenamiento local y volumen UC, con redacción y ACL actuales; verificar recuperación, hashes y aislamiento entre intentos en pruebas de store.
- [ ] 3.3 Exponer referencias y estado de planificación en `/runs/{run_id}` y documentar su lectura en `docs/operacion.md`; verificar respuestas completas, fallidas y reintentos en pruebas web.

## 4. Publicación controlada

- [ ] 4.1 Añadir al perfil la habilitación explícita de rutas OpenSpec y validar las rutas con la política actual; verificar que un perfil no habilitado no publica documentos.
- [ ] 4.2 Extender GitHub App para publicar código y documentos autorizados en un commit coherente y comparar el conjunto completo al reutilizar ramas; verificar éxito, divergencia y archivos adicionales en pruebas de integración.
- [ ] 4.3 Archivar el cambio validado tras implementar y probar, preparar specs resultantes y documentos históricos para perfiles habilitados; verificar el conjunto exacto del PR y que perfiles sin habilitación conservan artefactos solo en el harness.
- [ ] 4.4 Documentar la preparación de un repositorio cliente con OpenSpec y la revisión humana del PR; verificar que el procedimiento no indica merge ni despliegue automático.

## 5. Verificación de integración

- [ ] 5.1 Ejecutar la suite local completa y `databricks bundle validate --strict -t dev`; registrar resultados y corregir fallos antes de publicar el harness.
- [ ] 5.2 En entorno aislado, ejecutar una historia sintética con OpenSpec instalado en la App y comprobar artefactos, gates, registro de costos y PR sin merge; registrar evidencia y dejar deshabilitada la publicación OpenSpec en perfiles no preparados.
