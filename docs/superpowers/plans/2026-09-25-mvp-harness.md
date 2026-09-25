# MVP Harness Databricks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desplegar un harness separado que convierta la HU Silver aprobada en un PR revisable hacia NaturaPet `develop`.

**Architecture:** Una Databricks App FastAPI alberga el formulario y un orquestador determinista. Adaptadores invocan Foundation Model API, GitHub App y validadores; YAML separa política general y perfil NaturaPet.

**Tech Stack:** Python 3.13 local, Python de Databricks Apps, FastAPI, Pydantic, Databricks SDK, Foundation Model API, GitHub REST, pytest, DAB.

**Spec:** `docs/superpowers/specs/2026-09-25-mvp-harness-design.md`

## Global Constraints

- Rama del harness `MVP-Databricks-Harness`; repo cliente intacto salvo rama `feature/*` y PR hacia `develop`.
- Una sola App con una sola interfaz manual de HU.
- Sonnet 5 para análisis y desarrollo; Haiku 4.5 para verificación; sin API OpenAI.
- Sin límite monetario inicial, con contabilidad de tokens y límites técnicos.
- Databricks sandbox separado; dejar App detenida y entregar BAT de arranque/apertura.

## Review Focus

- HU incompleta: devolver campos faltantes sin llamar modelos.
- Ruta fuera de política: rechazar antes de escribir o publicar.
- Reintento de HU: no duplicar PR ni rama.
- Costo/uso ausente en respuesta del modelo: registrar desconocido, nunca cero supuesto.
- Error de prueba remota: bloquear publicación y preservar evidencia.

---

### Task 1: Contratos, perfil y costo

**Files:** `src/agents/harness/harness/contracts.py`, `config/clients/naturapet.yaml`, `config/defaults/models.yaml`, `tests/test_contracts.py`.

**Interfaces:** `Story`, `ClientProfile`, `load_profile(path)`, `estimate_cost(model, input_tokens, output_tokens)`.

- [ ] Escribir pruebas para HU completa/incompleta, rutas permitidas y precio mensual de capturas.
- [ ] Ejecutar `pytest tests/test_contracts.py -q` y comprobar fallos esperados.
- [ ] Implementar validación tipada y carga YAML; declarar endpoints y tarifas como configuración, no secretos.
- [ ] Repetir tests y documentar supuestos de precio.

### Task 2: Adaptadores y edición

**Files:** `src/agents/harness/harness/models.py`, `github.py`, `notebook_edit.py`, `tests/test_adapters.py`.

**Interfaces:** `ModelClient.complete(role, messages)`, `GithubAppClient.create_feature_pr(...)`, `apply_notebook_change(...)`.

- [ ] Probar parsing de respuesta, cálculo con uso real, autorización de rutas y división segura del piloto.
- [ ] Ejecutar tests y comprobar fallos.
- [ ] Implementar JWT/token de instalación, lectura y publicación Git sin exponer secretos, y editor del notebook.
- [ ] Repetir tests con mocks; comprobar que no hay rutas de producción ni token en logs.

### Task 3: Orquestador, gates y UI

**Files:** `src/agents/harness/harness/workflow.py`, `app/start_server.py`, `app/templates/index.html`, `tests/test_workflow.py`, `tests/test_ui.py`.

**Interfaces:** `run_story(story, deps) -> RunReport`; POST `/run`, GET `/runs/{id}`.

- [ ] Probar que gates fallidos bloquean push/PR y reintentos reutilizan ID.
- [ ] Ejecutar tests y comprobar fallos.
- [ ] Implementar flujo determinista, trazas y un único formulario manual con resultados.
- [ ] Repetir tests y abrir interfaz localmente.

### Task 4: DAB, secretos y GitHub App

**Files:** `databricks.yml`, `src/agents/harness/app.yaml`, `config/defaults/workflow.yaml`, `docs/deploy.md`, `iniciar-harness.bat`.

**Interfaces:** Databricks App `demo-harness-databricks-harness`; Secrets referenciados vía `valueFrom`.

- [ ] Verificar `bundle validate -t dev` antes de deploy.
- [ ] Crear GitHub App con permisos mínimos y guardar clave fuera de Git.
- [ ] Desplegar una App nueva, verificar endpoints y permisos de modelos, luego detenerla.
- [ ] Guardar URL real en BAT y verificar comandos de start/open.

### Task 5: Piloto y PR

**Files:** Rama `feature/*` de NaturaPet, evidencia bajo `docs/pilot/` en harness.

**Interfaces:** PR a `develop`, sin merge.

- [ ] Ejecutar HU aprobada con datos sintéticos y pruebas remotas en sandbox aislado.
- [ ] Revisar diff, tests, costo, rama y ausencia de escritura en recursos NaturaPet.
- [ ] Hacer push a `feature/*`, abrir PR a `develop` y adjuntar su URL a la tarea.
- [ ] Confirmar App `STOPPED`, rama harness publicada y documentación final reproducible.
