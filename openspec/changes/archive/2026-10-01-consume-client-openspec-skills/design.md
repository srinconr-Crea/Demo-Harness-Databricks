# Design

## Context

Ver `proposal.md` para la motivación. `conversation.py` mantiene la máquina de estados y recrea un checkout temporal por etapa; `prepare_client_workspace()` se ejecuta antes de restaurar el checkpoint. `propose_client_change()` ya consulta instrucciones de cuatro artefactos, pero usa rutas y orden fijos y no entrega explícitamente contenido de todas las dependencias. Explore/apply/verify usan prompts propios. `contextual_answer()` solo admite solicitudes acotadas de lectura y respuestas JSON; `ModelClient` selecciona el endpoint y registra cada llamada. `mark_tasks_complete()` y `archive --yes` completan el flujo final; archive sincroniza specs. El onboarding actual genera un PR con `--tools none` y solo recoge `openspec/`, contrario al nuevo límite acordado.

La CLI está fijada a 1.13.2. El paquete instalado ofrece el destino agents y seis workflows core: propose/explore/apply/update/sync/archive; verify existe pero requiere selección adicional. Las skills son datos del cliente, no código ejecutable ni nuevas políticas. El diseño aplica a la conversación FastAPI activa; históricos mantienen lectura y modalidad de publicación original.

## Goals / Non-Goals

**Goals:** sustituir instrucciones de workflow duplicadas por skills del checkout, preservar contratos de salida y controles deterministas, registrar procedencia suficiente para recuperación y hacer explícita la preparación manual.

**Non-Goals:** intérprete genérico de SKILL.md, ejecución automática de shell o de herramientas listadas en frontmatter, nuevas estrategias, nuevas aprobaciones, migración artificial de históricos, actualización durante HUs o un segundo orquestador.

## Decisions

### 1. Preparación y mantenimiento humanos

Documentar un procedimiento manual con la versión CLI compatible: seleccionar explore/propose/update/apply/verify/sync/archive, ejecutar init con agents, configurar el proyecto y revisar el PR antes del merge. Especificar la selección custom soportada por la CLI fijada, sin depender de preferencias globales implícitas; comprobar que los siete SKILL.md existen antes de dar por preparado al cliente. Retirar `app/onboard_client.py` y los helpers automáticos de inicialización/publicación del procedimiento soportado y de la entrada ejecutable. La App solo valida archivos integrados en la base.

Alternativa descartada: cambiar el onboarding automático a agents. No cumple la preparación exclusivamente humana y precisaría publicar rutas adicionales desde el Harness. Fixtures sintéticas se preparan explícitamente para pruebas, sin reintroducir init en el camino de HU.

### 2. Lector pequeño y acotado

Crear `skills.py` con mapa fijo fase -> nombre de skill y un resultado con contenido íntegro, nombre, ruta relativa, hash y generatedBy. Leer `.agents/skills/<nombre>/SKILL.md` exclusivamente del checkout del intento. Validar todos los componentes de ruta contra enlaces/reparse points, archivo regular, UTF-8 y frontmatter seguro. Nunca importar módulos ni seguir referencias externas de la skill automáticamente. Otros archivos de contexto solo se consultan bajo RepoContext y política existente.

Propuesta de límites configurables en perfil confiable: 128 KiB por skill, 1 MiB de catálogo por intento y 512 KiB de prompt compuesto por llamada; sobrepasarlos bloquea con diagnóstico y no trunca instrucciones. Comprobar name y generatedBy; inicialmente exigir generatedBy igual a la versión CLI soportada, con tabla explícita de compatibilidad para futuras versiones probadas. No usar metadatos para seleccionar modelos, herramientas o permisos. `.agents/skills/` permanece solo lectura y nunca entra en el manifiesto de desarrollo ni en el PR de una HU.

Alternativa descartada: empaquetar una copia fallback en la App. Ocultaría una preparación incompleta y duplicaría el mantenimiento.

### 3. Adaptar ejecución y formato, conservar el workflow

El sistema fija política, modo de ejecución mediado y contrato JSON; el prompt de usuario contiene la skill completa separada de HU/contexto. El adaptador declara que las lecturas pasan por context_request, la escritura por resultados estructurados y los comandos los ejecuta el Harness. No elimina secciones mediante heurísticas. Las indicaciones interactivas de una skill se traducen a summary/questions o feedback; una skill no puede añadir gates humanos. Cambiar texto producido es aceptable, cambiar estados o acciones no lo es.

| Fase | Skill | Contexto CLI/artefactos | Ejecutor y resultado |
| --- | --- | --- | --- |
| Explore | openspec-explore | inventario/specs/config autorizados | explorer, summary/questions |
| Propose | openspec-propose | status e instructions por artefacto | planner, content/summary/manifest |
| Update | openspec-update-change | instrucciones, dependencias y revisión anterior | planner, nueva revisión |
| Apply | openspec-apply-change | instructions apply y contextFiles autorizados | developer, operaciones; ratio conserva expresión/editor |
| Verify | openspec-verify-change | specs/tasks/diff y pruebas | openspec_verifier obligatorio; Haiku asesor sin gate nuevo |
| Sync/archive | openspec-sync-specs y openspec-archive-change | status, instrucciones archive soportadas y comparación delta/main | preflight y archive deterministas con evidencia |

No agregar llamadas LLM en sync/archive: sus guías se cargan y registran en el contexto del preflight, pero la operación soportada de sincronización sigue siendo la que realiza archive. Registrar resultados sync y archive a partir de cambios reales, sin doble sincronización ni interpretar Markdown como comandos. Si la guía/configuración requiere operaciones no soportadas, bloquear explícitamente. La verificación prepara el candidato como hoy; nuevas capacidades de fusión semántica quedan fuera de este cambio.

### 4. CLI validado y dependencias explícitas

Ampliar `OpenSpecCLI` con consultas status/list/show necesarias y validadores distintos para artefactos, apply y archive; sus JSON tienen formas diferentes. Mantener ejecución sin shell, timeout y argumentos fijos. Propose/update consultan status y dependencias, conservando el esquema spec-driven y sus cuatro artefactos; leer dependencias completas bajo raíces autorizadas y presupuestos antes de cada generación. Apply exige estado ejecutable y valida contextFiles/rutas antes de pasar su contenido al desarrollador. Ningún resolvedOutputPath ni ruta de dependencia sustituye las políticas de escritura.

Alternativa descartada: ejecutar explore/propose/verify/sync como comandos. Son workflows de skills; no existen esos subcomandos en la CLI inspeccionada.

### 5. Procedencia fijada al intento y a la aprobación

Antes de explorar, validar y registrar el catálogo requerido contra la base. Revalidarlo tras restaurar checkpoint y antes de cada llamada. Añadir campos opcionales de procedencia a contratos/store/ModelResponse: fase, base_sha, skills con ruta/hash/generatedBy, versión CLI y comando/hash de instrucciones normalizadas. Guardar un snapshot protegido de instrucciones aplicables enlazable desde eventos/llamadas; no depender de input_text truncado para reproducirlas. Normalizar rutas absolutas temporales a referencias relativas validadas antes de calcular hashes, conservando semántica y rechazando rutas externas.

Incluir catálogo y runtime en plan_metadata para que el hash aprobado cubra esas dependencias. Cada ronda contextual hereda la procedencia por parámetros explícitos de ModelClient; no añadir claves arbitrarias al usage_context enviado al endpoint. Fallos de invocación preservan procedencia y costos existentes; fases sin modelo solo generan eventos. Verificación de recuperación compara versión/runtime y hashes: cambio incompatible bloquea, sin actualizar ni sustituir instrucciones. Un reintento nuevo sobre base actual vuelve a planificar y aprobar.

Lecturas históricas toleran ausencia de campos. Para intentos activos anteriores sin procedencia, mantener consulta/cancelación y exigir reintento explícito con cliente preparado para ejecutar bajo el nuevo motor; no reconstruir ficticiamente catálogo aprobado ni volver al prompt antiguo como fallback. Conservar publication_mode en registros antiguos.

### 6. Conversación y controles existentes

No cambiar endpoints, botones, estados ni polling. El error de preparación identifica archivos/workflows faltantes en detalle y muestra mensaje natural de mantenimiento manual. Mantener leases, idempotencia, checkpoints, decisiones por expected_revision/hash y rechazo de base avanzada. Sonnet y pruebas son obligatorios; ratio y general_patch conservan validaciones y sandbox. Publicación requiere candidato íntegro autorizado, con OpenSpec y código juntos en feature/*; las skills consumidas no se editan.

## Risks / Trade-offs

- Skills del cliente con instrucciones conflictivas -> aislamiento de autoridad, contratos y controles deterministas; probar solicitudes de shell, modelos y permisos adicionales.
- Prompts más largos -> presupuestos explícitos y registro real por llamada; no prometer costo o latencia iguales ni omitir instrucciones para ahorrar tokens.
- Skills/CLI desalineados -> compatibilidad explícita y PR de mantenimiento previo; el requisito de versión exacta inicial es deliberadamente conservador.
- Clientes existentes y procesos activos -> preparación manual de skills y reintento explícito para procesos sin procedencia; lectura histórica sigue disponible.
- Hashes inestables por rutas temporales -> normalización validada y prueba de recuperación en directorios diferentes.
- Expectativas de ejecución directa en skills -> adaptación de herramientas/formato en el sistema y rechazo de operaciones no soportadas; no interpretar las skills como programas.

## Migration Plan

1. Implementar lector, validadores CLI, procedencia y composición manteniendo el runtime fijado.
2. Actualizar fixtures, pruebas y documentación; retirar onboarding automático y documentar selección manual incluyendo verify.
3. Verificar con cliente sintético preparado manualmente y CLI real el recorrido hasta PR simulado, controles negativos y recuperación; ejecutar suite local completa.
4. Antes de activar para clientes reales, una persona integra su PR de skills compatibles. No crear esos PR ni desplegar desde esta implementación.
5. Ante fallo, detener admisión del perfil y conservar checkpoints/registros; rollback de App solo con runtime compatible con los intentos guardados. No generar skills automáticamente para desbloquear.
