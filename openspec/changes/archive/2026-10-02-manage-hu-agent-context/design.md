# Design

## Context

Ver proposal.md para motivación. SHA inspeccionado: 487eff3626b08296aff72016763cc37cae75337a. conversation.py conserva aclaraciones como texto; repo_context.py reenvía context_history por ronda; skills.py compone MEDIATED_SYSTEM y snapshots; models.py acepta system prompt por llamada. Existen validaciones por fase, pero no gestor explícito de memoria/cache/selección. El asesor independiente tiene una ruta de llamada distinta. establish-project-context ya fue archivado: su protocolo no sustituye el contexto del runtime cliente.

## Goals / Non-Goals

**Goals:** opción 2 con selección reproducible, memoria verificable, fuentes vigentes, reducción determinista y comparación de métricas.

**Non-Goals:** compactor LLM/context_compactor, resumen semántico automático, aprendizaje del historial, memoria entre HUs/clientes, vector DB, provider prompt caching, cache de respuestas finales, cambios de autorización y limpieza del scaffold. Compactación asistida requiere otro cambio y evidencia de necesidad.

## Decisions

### 1. Separar fuentes, derivaciones y autoridad

ContextEnvelope versionado: cliente/repo, run/attempt/revision/stage/role, SHA base, checkpoint/generación, perfil, versiones de política/prompts/skills, fuentes path/hash/ref, decisiones, preguntas y métricas. SelectionRecord conserva referencias incluidas/excluidas, razones y bytes antes/después. Aprobaciones y manifiestos se verifican desde originales, nunca desde vistas reducidas.

context_manager.py coordina selección/cache; prompt_contracts.py compone y valida; conversation.py conserva transiciones; RepoContext aplica permisos; ModelClient conserva transporte/routing/registro. Alternativa descartada: pedir a un LLM decidir qué recordar o confirmar decisiones; no garantiza preservación ni aislamiento.

### 2. Relevancia y vigencia por rol

La política confiable define familias de evidencia necesarias, no rutas arbitrarias desde la HU. Relevancia significa relación verificable con decisiones aplicables, dependencias OpenSpec, manifiesto y componente afectado. Vigencia significa identidad/revisión/hash compatibles con el estado evaluado, no fecha más reciente.

| Rol | Contexto mínimo |
| --- | --- |
| explorer | HU, preguntas pendientes, aclaraciones vigentes y evidencia necesaria para delimitar alcance |
| planner | Decisiones aplicables, feedback, skill/instructions/template/rules y dependencias del artefacto |
| developer | Plan/manifiesto aprobados, decisiones aplicables, apply y bytes/hashes actuales de archivos que modificará |
| openspec_verifier | Specs/tareas, decisiones, diff y pruebas reales del candidato |
| verifier | Decisiones y evidencia pertinentes para revisión asesora, con límites y truncamientos declarados |

Orden reproducible: mínimos obligatorios, decisiones/preguntas aplicables, fuentes vinculadas a artefacto/manifiesto, complementos autorizados. Desempatar por referencia/ruta; recencia solo entre revisiones comparables de una misma fuente. Una nota reciente no sustituye una regla vigente: registrar discrepancia y pedir aclaración cuando bloquee. Si no puede demostrarse que una aclaración es prescindible, conservarla íntegra o bloquear por presupuesto, sin heurística semántica para descartarla.

El gestor no presume comprender semánticamente la HU. Los roles solicitan evidencia adicional con context_request autorizado; recuperarla o declarar carencia. No se añade ranking vectorial ni expansión de herramientas.

### 3. Árbol antes de cada llamada y ronda

```text
Validar identidad, perfil, checkpoint y versiones
  --> incompatibles: bloquear; conservar consulta/cancelacion
  --> compatibles: validar decisiones y minimo por rol
        --> conflicto aplicable: solicitar aclaracion
        --> evidencia faltante: cache valida?
              --> si: revalidar acceso/hash/inventario
              --> no: recuperar con RepoContext
        --> deduplicar y retirar derivaciones obsoletas/no pertinentes
        --> medir prompt completo y reserva de salida
              --> cabe: llamar al rol y registrar seleccion
              --> no cabe: bloquear con diagnostico recuperable
```

Reevaluar tras cada context_request. Sin llamadas auxiliares, resumen LLM ni reinicios automáticos por síntomas ambiguos. Retry continúa siendo acción humana explícita.

### 4. Cache descartable y candidato

Cache en proceso por intento con LRU, TTL y bytes máximos. Clave: cliente/repo/perfil, SHA base, generación/checkpoint, operación/argumentos y hash de archivo o inventario del alcance. Revalidar allows_read e integridad en cada hit. Cambios durante apply invalidan lecturas; altas/bajas invalidan búsquedas. Denegaciones, errores, secretos y truncamientos no se cachean como evidencia completa. Reinicio produce miss y recuperación.

Reutilizar I/O no implica menos tokens: medir bytes realmente enviados. Se descarta cache basada solo en SHA base porque el candidato puede cambiar.

### 5. Ciclo de vida de decisiones

DecisionRecord: id/tipo/texto/scope, run/attempt/revision, origin_ref/hash, actor, estados proposed/confirmed/superseded/conflict/stale y sustitución. Confirmar únicamente texto humano autorizado inequívoco o hechos comprobados. Una extracción del modelo permanece propuesta; no agregar confirmaciones humanas por cada registro. Ante extracción ambigua, conservar aclaración original íntegra y pedir precisión solo si afecta una decisión dependiente.

Una decisión humana no expira por tiempo: queda sustituida mediante origen autorizado inequívoco o en conflicto pendiente. Un hecho de repositorio pasa a stale al cambiar su fuente; recuperarlo antes de usarlo. Aprobaciones siguen revisión/hash y controles vigentes. TTL aplica a cache; retención aplica al almacenamiento protegido de originales y artefactos, sin borrar intentos activos o PR pendientes.

Update conserva cambios humanos y recalcula aplicabilidad. Retry reconstruye lo permitido del mismo run, revalida hechos y nunca hereda autorizaciones. No compartir memoria entre HUs/clientes.

Ejemplo sintético: M12 confirma D1 «cero permitido en compras» y D2 «negativos rechazados». Planner/developer reciben ambas con M12/hash. Corrección humana inequívoca genera D3 «cero rechazado», sustituye D1 y conserva origen. Contradicción sin sustitución clara requiere aclaración. Modificar validaciones.py invalida lectura anterior; verify recibe candidato vigente.

### 6. Reducción determinista y presupuesto

Medir prompt completo: system, skills/instructions, contratos de herramientas, datos seleccionados e historial; reservar salida según endpoint confiable. Conservar guardrail de bytes y estimación conservadora documentada si no hay tokenizer compatible; nunca confundir estimación con usage.

Orden: deduplicar por hash; excluir fuente obsoleta tras obtener versión vigente; retirar complementos sin relación verificable; ensamblar vista de decisiones/preguntas/referencias desde originales. Conservar una copia íntegra de evidencia requerida. Una referencia sin contenido suficiente no acredita inspección del modelo. No truncar/resumir skills, instrucciones, restricciones ni aclaraciones ambiguas requeridas.

Cada retiro registra motivo/ref recuperable; verificar cobertura exacta de IDs, refs y hashes requeridos. Si mínimo y reserva no caben, bloquear sin compactor ni aumento automático. Se retiran umbrales anteriores 80%/30%: la deduplicación se evalúa siempre y no necesita un disparador de compactación asistida.

### 7. Prompts y herramientas por roles reales

Catálogo confiable en config, base común, rol/fase, restricciones y output. Mantener explorer/planner/developer/openspec_verifier obligatorio/verifier asesor; no introducir alias advisory/advisor ni context_compactor. Sync/archive siguen deterministas. Planner varía por artefacto/estrategia: manifest no es obligatorio en todos.

| Tool | Entrada | Respuesta |
| --- | --- | --- |
| list_tree | op, sin ruta libre | paths/truncated; rechazo o límites explícitos |
| search_text | op/query string acotada | matches con path/line/text/hash y truncamiento declarado |
| read_file | op/path relativa | path/hash/content/truncated o razón de rechazo |

Definir campos permitidos, tipos, tamaños y rechazo de desconocidos compatibles con operaciones actuales. Describir argumentos, respuestas y errores junto al contrato de herramientas en payload; restricciones comunes en system. Sin shell ni tools importadas de skills. Solo roles/fases con retrieval autorizado reciben tools; no añadir retrieval al asesor automáticamente.

Fijar hash/version de prompt/contrato por intento y llamada con snapshots. Validar schema y después política/manifiesto. Probar cuerpo realmente enviado en todas las rutas, incluida asesora, y casos concretos de fallo por restricción.

### 8. Persistencia, diagnóstico y evaluación

Memoria/envelopes/selecciones como artefactos protegidos con hash y referencia en checkpoint coordinado. Ignorar derivaciones no confirmadas; reconstruir alteradas desde originales o bloquear sin borrar estado. Campos opcionales para históricos, engine/política/prompts fijados en activos sin migración silenciosa. Mantener API/UI y detalle bajo demanda sin exposición de memoria/prompts restringidos.

Registrar selección/exclusión/invalidación/conflicto/bloqueo, referencias, bytes completos antes/después, cache y estimación. Solo llamadas reales tienen usage/costo cuando informado; reducción local no genera llamadas ni ahorro facturado ficticio.

Guía en docs/operacion.md: síntoma, comprobaciones, acción y responsable. Repetición/falta de progreso no identifica una causa única; revisar fuentes antes de descartar derivación o solicitar retry. Conflicto exige aclaración, no compactación. Mapa de fuentes por referencia a specs/config, sin duplicar autoridad.

Comparación sin/con gestor: mismos fixtures, decisiones, respuestas y context_requests; llamadas, bytes, latencia y usage/costos disponibles. Verificar decisiones completas, sustitución, conflicto, candidato, reinicio e aislamiento. Estrés de 40 turnos sintéticos acotados como escenario, no garantía universal. Criterios: preservación y presupuesto; ahorro solo si medido.

## Risks / Trade-offs

- [Pérdida de matices por selección] -> mínimos completos y aclaraciones ambiguas íntegras.
- [Recencia desplaza regla] -> aplicabilidad y sustitución autorizada, discrepancia explícita.
- [Cache no reduce tokens] -> métricas separadas de I/O y bytes enviados.
- [Presupuesto insuficiente sin compactor] -> bloqueo recuperable; otro cambio si hay necesidad demostrada.
- [Política cambia durante espera] -> versiones fijadas y retry humano con aprobación nueva.
- [Estimación imprecisa] -> guardrail completo de bytes y reserva conservadora.

## Migration Plan

1. Contratos/política/prompts deshabilitados por defecto, con pruebas locales.
2. Integrar gestor/checkpoint; activar solo nuevos intentos sintéticos.
3. Suite y flujo local con modelos stub/CLI real; comparación y estrés con evidencia.
4. Antes de activación real, smoke positivo/negativo solo demo_harness y sandbox/warehouse autorizados.
5. Activación por perfil/runtime aprobado. Rollback deshabilita nuevos intentos y conserva originales/versiones; drenar activos o requerir retry si runtime previo no entiende engine.

Sin bundle previsto. Revalidar SHA/dependencias en apply si limpieza se ejecutó antes. Alterar infraestructura exige revisar alcance y validar bundle estricto.
