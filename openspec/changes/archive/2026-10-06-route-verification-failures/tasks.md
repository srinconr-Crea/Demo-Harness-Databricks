# Tasks

## 1. Contratos y clasificación de fallos

- [x] 1.1 Añadir contratos versionados de categoría/hallazgo con evidencia, criterio afectado y alcance requerido, y verificar en tests de contratos rechazo de categorías desconocidas, tipos inválidos y recomendaciones que intenten ampliar permisos.
- [x] 1.2 Distinguir en adaptadores error del candidato, indisponibilidad del runner y evidencia inconclusa; verificar fixtures de error Python/SQL, fallo funcional, sandbox inaccesible y passed=false sin diagnóstico, sin clasificar automáticamente todos como implementación.
- [x] 1.3 Implementar decisión de transición validada contra plan/perfil/manifiesto, incluidos hallazgos mixtos, ambiguos y defectos del harness; verificar que solo implementación autorizada llega a correcting y scope_spec espera aprobación antes de escribir.
- [x] 1.4 Actualizar contratos confiables developer/Sonnet y documentación de roles con clasificación y cobertura; verificar composición y hashes con gestor de contexto activado/desactivado, manteniendo modelos, siete skills y contrato asesor Haiku vigentes.

## 2. Destinos OpenSpec y coherencia del plan

- [x] 2.1 Añadir capacidades tipadas nuevas/modificadas a proposal y validarlas contra inventario autorizado; verificar capacidad existente bronze-ingestion, varias capacidades, ruta anidada existente, nueva declarada, capacidad ausente y traversal en tests de planner/OpenSpec.
- [x] 2.2 Generar specs por ruta declarada y comprobar destinos/requisitos MODIFIED contra base más validación estricta; verificar que el caso de bronze-ingestion deja de producir specs/<change_id>/spec.md y que un defecto impuesto por runtime falla sin ciclos de update.
- [x] 2.3 Gestionar deltas obsoletos durante update conservando versiones históricas; verificar con CLI real en cliente sintético que el conjunto final contiene solo las capacidades de la propuesta vigente y puede sincronizarse/archivarse sin capacidad espuria.
- [x] 2.4 Actualizar guía de planificación/operación para destinos por capacidad y feedback específico; verificar referencias y mantener OpenSpec cliente separado del árbol del harness.

## 3. Cobertura y edición acumulada

- [x] 3.1 Implementar cobertura tipada por entrada y comprobar already_conformant con hashes actuales antes de escrituras; verificar listas vacías con cobertura completa, omisiones, hashes alterados y afirmaciones sin evidencia.
- [x] 3.2 Validar subconjuntos de operaciones y efecto acumulado contra base/manifiesto, incluidos modify de archivos creados en el intento; verificar que create aprobado no exige recrear el test y que delete de un archivo solo autorizado para modify sigue rechazado.
- [x] 3.3 Conservar atomicidad, límites acumulados y changed_code_paths derivados del diff base/candidato; verificar que una corrección parcial mantiene la prueba de todos los componentes afectados y que una ruta fuera de manifiesto no se escribe parcialmente.
- [x] 3.4 Actualizar documentación de editor/manifiesto con distinción entre operación sobre checkout y efecto base/candidato; verificar ejemplos de operación parcial y ausencia de ampliación implícita.

## 4. Etapa correcting y verificación vigente

- [x] 4.1 Introducir candidate_revision/hash y etapa correcting conservando aprobación/revisión/hash del plan; verificar flujo test fallido -> correcting -> verify sin planner, sin aprobaciones ficticias y con rechazo ante bytes del plan alterados.
- [x] 4.2 Aplicar reparación semántica Sonnet dentro del manifiesto y ejecutar nuevamente validación técnica/Sonnet; sustituir expectativa indiscriminada de test_sonnet_rejection_needs_new_plan por casos de implementación y scope_spec, comprobando que el segundo invalida aprobación y espera revisión.
- [x] 4.3 Construir paquete de contexto con plan completo, notas, bloqueos, lecturas/hash y pruebas/candidato, y habilitar retrieval acotado de verify; verificar lectura io.py transferida, evidencia obsoleta, presupuestos y notas sin ejecución en ambos modos de contexto.
- [x] 4.4 Mantener estado de tareas separado de bytes aprobados hasta finalización determinista; verificar implementación/pruebas completas con sync/archive/PR pendientes y bloqueo de publicación tras modificar bytes ya verificados.
- [x] 4.5 Documentar las rutas de corrección y clasificación en README/operación/roles; verificar concordancia con las specs y que Haiku conserva su invocación asesora sin añadir métricas o configuración de desactivación.

## 5. Límites, persistencia y progreso visible

- [x] 5.1 Persistir máximo compartido de dos correcciones lógicas por intento mediante checkpoint/CAS; verificar fallo técnico seguido de rechazo semántico, tercer fallo, doble trabajador, reinicio y update sin reiniciar ni duplicar el contador.
- [x] 5.2 Persistir huellas de bloqueo/progreso pertinente y detener recurrencias sin avance antes de otra llamada equivalente; verificar cambios solo de prosa/timestamps/IDs, operations vacías, reparación parcial real y recuperación acotada de evidencia.
- [x] 5.3 Versionar contratos por intento y recuperar correcting bajo procedencia compatible; verificar consulta histórica sin campos inventados, intento antiguo activo, incompatibilidad de rollback, retry humano autorizado y retry obsoleto/competidor sin publicaciones duplicadas.
- [x] 5.4 Añadir correcting y causa al progreso/eventos/interfaz, separando éxito histórico de verify pendiente del candidato actual; verificar respuestas API y flujo UI con fixture local, conservando borradores, redacción de datos y costos reales por llamada.
- [x] 5.5 Actualizar documentación de recuperación/despliegue con drenaje, compatibilidad y rollback; verificar que no autoriza migrar silenciosamente aprobaciones ni reanudar estados nuevos con runtime antiguo.

## 6. Verificación integrada

- [x] 6.1 Reproducir localmente con CLI real y modelos simulados la secuencia del caso f9c8: dos archivos ya aplicados, rechazo de destino delta y operations vacías; verificar ruta correcta, cobertura sin scope_changed ficticio, ausencia de vueltas repetidas y conservación de 11 criterios sintéticos sin usar datos/recursos cliente.
- [x] 6.2 Verificar flujo integrado de implementación corregida -> pruebas -> Sonnet -> sync/archive -> PR simulado con autorización original; verificar también alcance adicional -> nueva aprobación, fallo infraestructura y defecto harness sin publicación. Comprobar Haiku favorable/desfavorable/indisponible sin alterar rutas obligatorias o presupuesto.
- [x] 6.3 Ejecutar suite tests/ con el comando operativo del repositorio y validación OpenSpec estricta; registrar revisión y alcance de evidencia local, sin atribuirle despliegue o smoke remoto. Si se solicita smoke remoto posteriormente, usar exclusivamente recursos demo_harness_* y Job/warehouse autorizados.
- [x] 6.4 Revisar correspondencia de artefactos con implementación y evidencia, y preparar sync/archive solo cuando tareas y verify estén completos; verificar que no quedan requisitos contradictorios sobre retorno indiscriminado a update ni se presenta esta propuesta como comportamiento ya desplegado.
