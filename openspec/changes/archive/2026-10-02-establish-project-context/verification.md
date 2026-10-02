# Verificación del contexto del proyecto

## Revisión y alcance

Base al iniciar: `80c66cec963c1f64777df45c4e4b34226857097b`.
La rama feature/context-proposals coincidía con esa base. Por instrucción explícita
del usuario, la publicación se realiza en `Db_Spec_Harness`, comprobada idéntica
a origin antes de publicar. Esa instrucción reemplaza para este cambio el PR y
destino feature previstos en la tarea 3.2; no autoriza cambios a ramas protegidas
ni despliegue cliente. El usuario también pidió redeplegar la App del harness.

Archivos funcionales de runtime, API, bundle y perfiles no se modificaron.
El paquete de la App no consume el contexto OpenSpec del producto; el contexto
nuevo se conserva en este repositorio. El redepliegue mantiene código y bindings
actuales y no implica implementar memoria/cache/compactación de la App.

## Ejercicio de reanudación desde archivos

Se reconstruyó el estado de `manage-hu-agent-context` consultando proposal,
design, tasks y CLI list, sin usar mensajes anteriores como evidencia. Es un
ejercicio manual de lectura de fuentes, no una prueba de un segundo modelo o
chat independiente.

- Objetivo: gestionar contexto por HU mediante selección, cache, memoria,
  compactación y prompts por rol/fase.
- Decisiones propuestas: memoria por HU sin transferencia automática entre
  clientes; cache de fuentes; compactación conservadora. No son capacidades
  implementadas por existir en el diseño.
- Estado observado: 0 de 23 tareas completas; planificación disponible.
- Siguiente paso: revisión y elección humana de ese cambio antes de apply.
- Fuentes: `openspec/changes/manage-hu-agent-context/{proposal,design,tasks}.md`
  y sus deltas. La tarea de contexto del proyecto no completa tareas de la App.

Resultado: objetivo, alcance, estado y próximo paso recuperables desde el repo.
El indicador de artefactos completos de status no se confundió con tareas
implementadas; para estas se usó el recuento de list.

## Ejercicio de discrepancia

El cambio antiguo `replace-analyst-with-openspec-planning/tasks.md`, tareas 1.3
y 4.4, describe inicialización automática por HU. Aunque sigue sin archivarse,
su contenido conserva una modalidad anterior. Se contrastó con:

- `docs/operacion.md`, incorporación única del cliente: preparación humana.
- `openspec/specs/client-workspace/spec.md`: checkout preparado requerido.
- `src/agents/harness/harness/openspec.py`, `prepare_client_workspace`: rechaza
  config/specs/changes ausentes; no inicializa cliente.
- `tests/test_openspec.py`: pruebas de preparación requerida y ausencia de init.

Resultado: discrepancia identificada y explicada como histórica. No se modificó
ni archivó el cambio antiguo y no se atribuyó una aprobación nueva a sus tareas.
La guía nueva ordena contrastar requisitos y comportamiento, sin elevar el
histórico a autoridad. No hay decisión pendiente que impida este cambio documental.

## Comprobaciones

- Nuevas pruebas: 6 passed en 0.10 s, con temporales accesibles.
- Adaptador OpenSpec: 11 passed en 31.28 s.
- La primera suite completa obtuvo 23 failed, 175 passed, 1 skipped por rutas
  largas al reemplazar archivos de snapshots en Windows. Se repite con un
  basetemp corto; este problema de entorno no se corrigió cambiando el runtime.
- Paquete `.deployments/naturapet-dev-context-20261002`: bundle validate --strict
  con perfil CREA_DEV, target dev, Validation OK.

## Sync y despliegue

- Sync agent-driven de `project-context`: cuatro requisitos añadidos con todos
  sus escenarios; contenido cotejado con el delta. Validación estricta de specs:
  13 passed, 0 failed. Sin placeholders Purpose.
- Perfil elegido explícitamente por el usuario: CREA_DEV. No se seleccionó
  automáticamente desde la lista de perfiles.
- Antes de desplegar: App STOPPED; los tres registros persistidos consultados
  estaban complete/failed. Ninguna HU activa en esa consulta.
- Paquete preparado desde runtime/perfil actuales; sus hashes coinciden con
  naturapet-dev-v3. Solo bundle sync y bundle run harness, sin bundle deploy de
  infraestructura ni cambios a recursos NaturaPet.
- CLI: App started successfully. URL:
  https://demo-dbx-harness-mvp-7405606739630987.7.azure.databricksapps.com
- Smoke del Job 611081415041874 con identidad distinta de la App:
  positivo 711855639497789, dos pruebas pasaron; negativo 516496401575380,
  fallo sintético rechazado como esperado. Script finalizó con exit code 0.

- Comprobación autenticada posterior: compute ACTIVE, deployment SUCCEEDED
  (`01f1be7f3efa156ca0df1c6b3eefcc98`); GET / devolvió 200 HTML y GET
  /configuration devolvió 200 JSON. No se creó ninguna HU cliente para el smoke.

## Resultado final local y cierre

- Suite completa con ruta corta en TEMP y Node explícito en PATH: **198 passed,
  1 skipped, 1 warning en 825.19 s**. La advertencia es de deprecación de
  Starlette/httpx, no de este cambio.
- `rules` y `operations` de config comparados por YAML contra HEAD base:
  idénticos. Contexto general: 2.599 bytes UTF-8, menor a 8 KiB.
- Diff revisado: documentación, contexto general, spec y pruebas; sin cambios
  a fuentes runtime, infraestructura o perfil cliente.
- Sync cotejado: cuatro requisitos y todos sus escenarios coinciden con el delta.
- Archivo realizado después de comprobar 9/9 tareas:
  `openspec/changes/archive/2026-10-02-establish-project-context/`.
- La propuesta hermana mantiene 0/23 tareas y no se sincroniza ni archiva.
- Publicación solicitada: commit y push no forzado a `Db_Spec_Harness`.
