# Tasks

## 1. Contrato compartido y rechazo previo a lectura

- [x] 1.1 Agregar regresiones en pruebas de contexto para la respuesta real con lista de tres operaciones, null, escalares, mezcla con salida final, op desconocido, campos extra y tipos/tamaños inválidos; verificar que fallan con el runtime previo y que ninguna solicitud rechazada ejecuta lectura, búsqueda o inventario.
- [x] 1.2 Centralizar formas, tipos, límites y ejemplos de contexto en `prompt_contracts.py`, integrarlos en `repo_context.py` y `context_manager.py`, y versionar los prompts afectados; verificar igualdad del contrato enviado con gestor habilitado/deshabilitado y hashes de procedencia conservados.
- [x] 1.3 Validar presencia, envoltorio y solicitud antes de ejecutar contexto, marcar invalid_contract y levantar el error de respuesta recuperable con diagnóstico seguro; verificar todos los casos negativos de 1.1 y que el mensaje público no expone valores arbitrarios del modelo.
- [x] 1.4 Cubrir operaciones válidas sucesivas, salida final, ruta denegada, enlaces, secretos, presupuestos, rol sin retrieval y planner con schema; verificar que los casos válidos terminan, las denegaciones mantienen su feedback y no aparecen reparaciones automáticas ni ejecución parcial de lotes.
- [x] 1.5 Actualizar `docs/operacion.md` y la guía pertinente de contexto con las tres formas y una operación por turno; verificar que ejemplos coinciden con el contrato y no prometen filtrado path para list_tree/search_text.

## 2. Evidencia persistida y reintento humano

- [x] 2.1 Extender pruebas de `test_response_recovery.py` y contexto con fallo de formato en exploring/proposing/updating; verificar state failed coherente en ejecución, intento, coordinación y checkpoint, acceptance=invalid_contract en la misma llamada, finish_reason y uso conservados, y vínculo a evidencia original sin llamada ficticia.
- [x] 2.2 Verificar y ajustar solo donde sea necesario la integración de retry en motor, API y UI existentes; comprobar que una persona autorizada ve Reintentar etapa para nuevos fallos recuperables y que retry restaura etapa, aclaraciones y artefactos íntegros, registra llamadas nuevas y exige aprobación vigente del plan.
- [x] 2.3 Agregar regresiones de reinicio, revision/failure_id obsoletos, actor no autorizado, perfil/contexto/procedencia incompatibles, checkpoint alterado y carrera CAS/lease; verificar ausencia de llamadas o cambios de estado indebidos y ausencia de retry automático.
- [x] 2.4 Agregar fixture histórico sintético con el mensaje original, acceptance=parsed y retryable=false; verificar que consulta/reinicio mantienen esos valores y no ofrecen retry retroactivo ni recalculan costos.
- [x] 2.5 Documentar diagnóstico, alcance de retry nuevo y procedimiento de HU nueva para el caso histórico en `docs/operacion.md`; verificar que no propone editar registros/checkpoints ni heredar aprobación.

## 3. Migración de configuración a Sonnet 5.5

- [x] 3.1 Obtener tarifas específicas de Sonnet 5.5 para la región de instalación, registrar fuente/fecha y separar estimaciones de facturación en evidencia; verificar que no se copian tarifas previas sin sustento y bloquear activación si falta una estimación documentada.
- [x] 3.2 Actualizar validación confiable de `models.py` y routing en `config/defaults/models.yaml` para exigir Sonnet 5.5 en los cuatro roles obligatorios y mantener Haiku 4.5 asesor; actualizar pruebas de `test_integrations.py` para verificar endpoint efectivo por rol y rechazo de Sonnet 5 u otros endpoints en el runtime nuevo.
- [x] 3.3 Configurar tarifas por endpoint y capacidades inicialmente no verificadas sin aumentar límites de agents/context; verificar límites efectivos 64.000/12.000, reserva de entrada, ausencia de fallback silencioso, costo ausente sin usage y costos históricos conservados con pruebas unitarias.
- [x] 3.4 Actualizar `examples/naturapet/environment.yaml` y referencias activas de README/guías sin editar evidencias históricas; verificar que un paquete renderizado alinea routing y CAN_QUERY sobre Sonnet 5.5 y mantiene recursos del harness, perfil, sandbox separado y ausencia de secretos inline.
- [x] 3.5 Añadir pruebas de preparación de instalación/routing-permisos y documentar migración por paquete completo y rollback en `docs/configuracion-instalacion.md`; verificar rechazo o detección de configuración incoherente y conservación de históricos/procedencia.

## 4. Compatibilidad remota y preparación operativa

- [x] 4.1 Con CREA_DEV ejecutar smoke sintético breve de Sonnet 5.5 con límite efectivo 64.000 y el schema real del planner, comprobando solicitud individual de contexto y salida final; registrar endpoint, request sin secretos, finish_reason, usage, costo estimado y duración. Verificar soporte de schema antes de habilitar json_schema=true; si no lo soporta, documentar flag false con validación textual; si no acepta el presupuesto requerido, detener activación.
- [x] 4.2 Verificar identidad y permiso CAN_QUERY de la App para Sonnet 5.5 como evidencia separada del operador, sin modificar recursos cliente; comprobar que la instalación no se declara lista si ese acceso falta y registrar el resultado con fuente/fecha.
- [x] 4.3 Preparar paquete de instalación completo y conservar paquete previo para rollback; ejecutar `databricks bundle validate --strict -t dev --profile CREA_DEV` desde el paquete y revisar resultados. Esta validación es obligatoria si cambian `databricks.yml` o `resources/`; verificar que solo referencia recursos del harness y el warehouse sandbox aprobado.

## 5. Verificación integrada y cierre

- [x] 5.1 Ejecutar la suite completa con `uv run --project src/agents/harness --with pytest pytest tests -q -p no:cacheprovider` y OpenSpec validate del cambio en modo strict; verificar salida sin fallos y revisar diff para confirmar que no sobrescribe trabajo local previo ni cambia recursos NaturaPet.
- [x] 5.2 Ejecutar recorrido integrado con cliente local sintético y CLI OpenSpec real: solicitudes sucesivas, lista rechazada, retry humano, revisión del plan y verificación obligatoria; comprobar que publicación simulada solo ocurre con aprobación vigente y que el registro distingue llamadas/etapas y modalidad histórica.
- [x] 5.3 Entregar evidencia separada de pruebas locales, compatibilidad de endpoint, permisos y paquete validado, con pendientes operativos explícitos; verificar que no se presenta disponibilidad READY como prueba de despliegue ni como resolución de la HU original.
- [x] 5.4 Cuando se autorice desplegar, drenar HUs, aplicar solo el paquete del harness y realizar smoke funcional sintético de explore/planificación y retry con la identidad de la App; registrar despliegue y resultado real sin ejecutar la HU original ni publicar PR en NaturaPet. Verificar disponibilidad del paquete previo y documentar rollback sin borrar checkpoints.
- [x] 5.5 Tras implementación y verificación, sincronizar deltas y archivar este cambio mediante los workflows correspondientes; verificar coherencia de specs principales y preservar la separación entre propuesta, implementación y despliegue comprobados.
