# Design

## Context

Ver `proposal.md` para el problema. El repositorio ya contiene README, operación, AGENTS, contexto OpenSpec y specs. El contexto actual mezcla mapa estable con endpoints y estrategias concretas. Existe además un cambio no archivado con tareas completadas que conserva instrucciones antiguas sobre inicialización automática: no debe tratarse como fuente vigente sin contrastarlo. `tests/test_project_structure.py` se menciona en documentación, pero no existe en este checkout; no se presupone como verificación disponible.

## Goals / Non-Goals

**Goals:** permitir reconstrucción reproducible y selectiva; separar decisión propuesta, requisito vigente y evidencia; mantener referencias sin crear un manual monolítico. El diseño cruza varias fuentes documentales y necesita un acuerdo explícito de mantenimiento.

**Non-Goals:** recordar automáticamente todos los chats, modificar el runtime de HUs, conectar servicios externos, migrar repositorios cliente o corregir/archivar cambios históricos ajenos como parte de este alcance.

## Decisions

### 1. Un mapa pequeño y fuentes con responsabilidades distintas

`openspec/config.yaml` conserva propósito, stack general, mapa activo, reglas estables y referencias. Presupuesto propuesto: bloque context de máximo 8 KiB UTF-8, sin usarlo como límite del runtime cliente. Roles/modelos concretos siguen en YAML de runtime; detalles funcionales, en specs. AGENTS añade un punto de entrada al protocolo, conservando todos los límites existentes. README y operación enlazan `docs/contexto-proyecto.md` en vez de duplicarlo.

Alternativa descartada: un documento gigante que copie código, specs y decisiones. Aumentaría divergencia y costo de lectura. Se conserva el mapa técnico actual porque ayuda a localizar la implementación real.

### 2. Protocolo de reanudación con referencias

La guía prescribe: identificar rama/SHA y modificaciones locales; leer puntos de entrada; resolver estado OpenSpec mediante CLI cuando esté disponible; elegir specs y cambio relevantes; contrastar código y pruebas; resumir objetivo, decisiones vigentes, propuestas, incertidumbres y siguiente paso. La conclusión cita rutas y, cuando importa, revisión/hash. No exige generar un archivo nuevo en cada chat. Si CLI falla, se declara lectura manual y no se falsifica su estado.

Un chat nuevo sobre validación de cantidades lee la spec y pruebas relacionadas, sin cargar catálogos cliente ni todos los archivos archivados. La ausencia de contexto se expone, no se rellena con recuerdos.

### 3. Decisiones y discrepancias

Las decisiones de cambio permanecen en design; al concluir, el comportamiento va a specs mediante sync. Solo una decisión transversal que necesite contexto histórico adicional genera un documento breve en `docs/decisions/`, con estado, fuentes, cambio origen y sustituciones. No se crea un catálogo paralelo de requisitos. La guía indica cómo registrar drift en el cambio de trabajo y cuándo detener una decisión dependiente, sin bloquear tareas no afectadas.

### 4. Coherencia comprobable

Crear `tests/test_project_context.py` para referencias canónicas que apuntan a rutas reales, parseo YAML y presupuesto de context. No intentar verificar por regex toda la semántica de la arquitectura. Complementar con dos ejercicios manuales sin historial: retomar un cambio pendiente y detectar contradicción entre histórico y comportamiento actual. El éxito exige referencias correctas y no atribuir implementación a una propuesta.

## Risks / Trade-offs

- [Guía desactualizada] -> checklist de actualización de fuente canónica y referencias en cada cambio que altere principios.
- [Documentación confundida con autoridad] -> mantener límites explícitos y contrastar evidencias; un archivo cliente no amplía permisos.
- [Lectura excesiva] -> recuperar por tarea y no precargar archivos completos de todo el proyecto.
- [Pruebas estructurales insuficientes] -> revisión humana y ejercicios de reanudación prueban la semántica que los enlaces no cubren.

## Migration Plan

El usuario eligió este cambio y solicitó publicación directa en `Db_Spec_Harness` y redepliegue de la App existente; esa elección reemplaza el destino feature/PR inicialmente previsto para este trabajo. Ejecutar comprobaciones pertinentes y suite antes de publicar. El contexto del producto se conserva en Git y no se inyecta en la App: su redepliegue conserva runtime, perfil y bindings, sin infraestructura nueva ni migración de datos. Reversión: revertir cambios documentales y comprobaciones sin tocar registros de HUs; el paquete previo de App permanece disponible. Antes de apply, comparar con el estado actual por si la propuesta hermana u otro cambio ya modificó las fuentes.
