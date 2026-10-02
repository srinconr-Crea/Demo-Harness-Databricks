# Tasks

## 1. Contratos y política versionada

- [ ] 1.1 Revalidar módulos, schemas de salidas y configuración contra el SHA vigente al iniciar apply, y registrar el inventario afectado; verificar diferencias con este diseño sin asumir implementación de la propuesta hermana.
- [ ] 1.2 Añadir contratos de envelope, decision, compaction y procedencia opcional para históricos en `contracts.py`; agregar pruebas de deserialización antigua/nueva, campos inválidos y aislamiento, verificando que no se rellenan hashes ni aprobaciones ficticios.
- [ ] 1.3 Definir política confiable de presupuestos, reserva de salida, umbrales, TTL/LRU/bytes de cache y versión del engine; documentar defaults y estimación de tokens, y probar rechazo de límites inválidos y cambios de política por HU.

## 2. Prompts por rol y fase

- [ ] 2.1 Crear catálogo confiable y compositor `prompt_contracts.py` con base común, rol, constraints y output para explorer/planner/developer/verifier/advisor y compactor; documentar contratos e incluir pruebas de rol desconocido, hashes reproducibles y política fijada por intento.
- [ ] 2.2 Integrar compositor en `SkillCatalog.compose` y `ModelClient.complete` conservando skills íntegras y snapshots; extender `tests/test_skills.py` para verificar que instructions cliente no reemplazan el system prompt ni exceden presupuesto silenciosamente.
- [ ] 2.3 Implementar validadores de output final y context_request específicos por rol/artefacto, conservando contratos públicos y routing actuales; probar JSON válido pero operación prohibida, preguntas inválidas y manifiesto fuera de perfil antes de editar.

## 3. Cache y selección de contexto

- [ ] 3.1 Implementar cache por intento y claves con perfil, base y estado del candidato/inventario; documentar I/O frente a tokens y agregar pruebas de hit/miss, TTL/LRU, corrupción y acceso revocado sin filtración entre clientes.
- [ ] 3.2 Integrar revalidación con `RepoContext` para lecturas/búsquedas y no cachear evidencia truncada como completa; probar archivo cambiado durante apply, alta/baja que afecta una búsqueda y lectura fuera de política.
- [ ] 3.3 Implementar árbol de decisión en `context_manager.py` antes de llamada y tras cada ronda; documentar razones y agregar pruebas tabuladas de uso directo, cache, memoria, recuperación, contradicción y bloqueo por presupuesto.

## 4. Memoria y persistencia

- [ ] 4.1 Extraer decisiones confirmadas desde aclaraciones autorizadas y hechos verificados con referencias, estados y sustituciones; documentar scope por HU y probar que una inferencia del modelo no se promueve y un conflicto pide aclaración.
- [ ] 4.2 Persistir memoria/envelopes como artefactos protegidos con referencias en checkpoint coordinado; probar fallo antes/después de confirmar checkpoint, integridad y reconstrucción en otro checkout sin modificar hashes aprobados.
- [ ] 4.3 Integrar recuperación, update y retry con versiones fijadas; actualizar operación y agregar regresiones en `tests/test_conversation.py` y `tests/test_skill_conversation.py` para varias aclaraciones, aprobación invalidada y ausencia de herencia de autorizaciones.

## 5. Compactación condicional

- [ ] 5.1 Implementar medición de presupuesto/reserva y reducción determinista de duplicados/derivaciones obsoletas; documentar umbrales y probar que no se compacta contexto pequeño ni se recortan skills o instrucciones obligatorias.
- [ ] 5.2 Implementar resumen estructurado con decisiones/preguntas/referencias ensambladas desde originales y narrativa opcional; probar referencias fabricadas, decisión omitida, contradicción, no reducción y rechazo seguro de resúmenes inválidos.
- [ ] 5.3 Incorporar llamada Sonnet de compactor únicamente cuando la reducción determinista sea insuficiente y exista presupuesto; configurar contrato/routing, documentar costo y probar límite de llamadas, ausencia de recursión y registro de resultados rechazados.
- [ ] 5.4 Persistir compactación aceptada y reconstruirla por hash/revisión; probar reinicio esperando aprobación y mínimo obligatorio demasiado grande, conservando consulta/cancelación y bloqueando la llamada sin ampliar límites.

## 6. Observabilidad y activación

- [ ] 6.1 Enlazar decisiones, métricas y hashes de prompt/contexto con `agent_calls` y eventos; documentar lectura protegida y probar usage ausente, costo de compactor rechazado y ausencia de costos ficticios por cache o fases deterministas.
- [ ] 6.2 Conservar API/UI actuales, detalle bajo demanda y compatibilidad de intentos anteriores; extender `tests/test_conversation_webapp.py` con históricos sin campos nuevos, control de acceso y no exposición de prompts/memoria restringida.
- [ ] 6.3 Implementar activación para nuevos intentos, detección de incompatibilidad de activos y rollback documentado; probar política cambiada, consulta histórica y retry humano sin heredar aprobación.

## 7. Verificación integrada

- [ ] 7.1 Ejecutar suite completa y validar estrictamente OpenSpec; verificar de punta a punta con cliente sintético local, modelos stub y CLI real: aclaración, propuesta/update, aprobación, apply, pruebas, verify, sync/archive y publicación simulada.
- [ ] 7.2 Antes de activación real, ejecutar smoke sintético positivo y negativo en sandbox autorizado demo_harness y warehouse permitido cuando aplique; registrar evidencia separada de pruebas locales, sin recursos ni despliegue del cliente.
- [ ] 7.3 Comparar escenario fijo sin/con gestión: llamadas, bytes enviados, latencia, usage/costos informados y preservación de decisiones; verificar cero pérdida de decisiones/autorizaciones y no afirmar ahorros sin medición comparable.
- [ ] 7.4 Sincronizar/archive tras implementación y verificación y preparar PR en feature con evidencia; verificar no merge ni despliegue automático. Si cambia bundle durante implementación, revisar alcance y ejecutar bundle validate estricto antes de publicar.
