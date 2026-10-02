# Tasks

## 1. Contratos y política

- [x] 1.1 Revalidar módulos, rutas de llamada y schemas contra SHA de apply; registrar diferencias con diseño y comprobar independencia del scaffold.
- [x] 1.2 Añadir envelope, decisiones, selección y procedencia opcional; verificar históricos/nuevos, estados inválidos, aislamiento y ausencia de hashes/aprobaciones inventadas.
- [x] 1.3 Configurar presupuesto total de entrada/reserva, estimación, TTL/LRU/bytes y engine; documentar defaults y probar límites inválidos, system incluido, política inmutable por HU y ausencia de compactor.

## 2. Prompts y herramientas

- [x] 2.1 Crear catálogo/compositor para explorer/planner/developer/openspec_verifier/verifier; documentar contratos y probar roles desconocidos, hashes reproducibles y versión fijada.
- [x] 2.2 Integrar todas las rutas, incluida asesora, conservando skills/snapshots; verificar cuerpo real, frontera de autoridad y presupuesto completo en pruebas de skills/modelos/conversación.
- [x] 2.3 Definir schemas y documentación de list_tree/search_text/read_file, tamaños, errores y truncamientos; probar campos desconocidos, traversal, tipos inválidos y tools no autorizadas por fase.
- [x] 2.4 Validar output por rol/artefacto/estrategia antes de transición/edición; probar preguntas inválidas, operación prohibida y manifiesto fuera de perfil, sin cambiar routing/API.

## 3. Cache y selección

- [x] 3.1 Implementar cache por intento con perfil/base/candidato/inventario; documentar I/O frente a tokens y probar TTL/LRU/bytes, corrupción, acceso revocado y aislamiento.
- [x] 3.2 Integrar revalidación en RepoContext; probar archivo cambiado en apply, altas/bajas de búsqueda y truncamiento no tratado como evidencia completa.
- [x] 3.3 Implementar mínimos por rol y orden por aplicabilidad/vigencia/referencia; documentar mapa de fuentes y probar regla vigente antigua frente a nota reciente incompatible, dependencias y faltantes.
- [x] 3.4 Aplicar árbol antes de llamada y tras context_request; comprobar razones de selección/cache/recuperación/conflicto/bloqueo y ausencia de llamadas auxiliares/reinicio automático.

## 4. Memoria y recuperación

- [x] 4.1 Extraer decisiones inequívocas autorizadas y hechos con origen/hash, conservando aclaración ambigua íntegra; probar cero/compras/negativos, inferencia no promovida y conflicto que espera aclaración.
- [x] 4.2 Implementar sustitución y stale por fuente; documentar vigencia/TTL/retención y probar decisión humana sin expiración temporal, origen conservado y aprobación vinculada a hash/revisión originales.
- [x] 4.3 Persistir memoria/envelopes/selecciones por hash en checkpoint; probar fallo antes/después de confirmar, corrupción y reconstrucción en otro checkout sin modificar hashes aprobados.
- [x] 4.4 Integrar update/retry/reinicio con versiones fijadas; actualizar operación y probar múltiples aclaraciones, espera restaurada, aprobación invalidada y ausencia de autorización heredada.

## 5. Reducción y presupuesto

- [x] 5.1 Deduplicar por hash y excluir derivaciones obsoletas/no pertinentes con razones; documentar reglas y probar reducción repetida, una copia íntegra requerida y skills/instructions preservadas.
- [x] 5.2 Ensamblar vista estructurada desde originales y verificar cobertura de IDs/refs/hashes; probar decisión omitida, referencia fabricada, contradicción y aclaración ambigua íntegra.
- [x] 5.3 Bloquear si mínimo completo y reserva no caben; documentar recuperación y probar consulta/cancelación disponibles, cero aumento automático y cero compactor.

## 6. Observabilidad y activación

- [x] 6.1 Enlazar prompt/selección/exclusiones/bytes/cache a eventos y llamadas; documentar métricas y probar usage ausente, evidencia protegida y ausencia de costos ficticios locales.
- [x] 6.2 Conservar API/UI e históricos opcionales; ampliar pruebas webapp de ACL, no exposición y ausencia de selección inventada en históricos.
- [x] 6.3 Implementar activación de nuevos intentos e incompatibilidad de activos; documentar rollback y tabla humana de síntomas/comprobaciones/acciones y probar política cambiada y retry sin aprobación heredada.

## 7. Verificación integrada

- [x] 7.1 Ejecutar suite completa y OpenSpec estricto; verificar flujo local con cliente sintético, modelos stub y CLI real hasta PR simulado, registrando alcance/resultados reales.
- [x] 7.2 Comparar sin/con gestor con respuestas y solicitudes iguales: llamadas/bytes/latencia/usage/costo disponibles; verificar decisiones, sustitución, candidato vigente y autorizaciones, sin ahorro no medido.
- [x] 7.3 Ejecutar estrés acotado de 40 turnos con repetición/sustituciones/reinicio; registrar preservación y bloqueo al exceder presupuesto, sin promesa universal.
- [x] 7.4 Antes de activación real ejecutar smoke positivo/negativo solo sandbox demo_harness y warehouse autorizado cuando aplique; distinguir evidencia local/remota sin tocar cliente.
- [x] 7.5 Tras implementación verificada sincronizar/archive y preparar publicación en la rama existente Db_Spec_Harness expresamente autorizada con evidencia; comprobar no merge ni despliegue cliente automático y bundle estricto si se alteró infraestructura.
