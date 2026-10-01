# Proposal

## Why

El Harness ya consume instrucciones CLI para planificar, pero explora, aplica y verifica con prompts propios sin cargar las skills OpenSpec del cliente. Consumir esas skills versionadas reduce duplicación y permite actualizar el workflow mediante mantenimiento humano, preservando el control del Harness y la conversación actual.

## What Changes

- **BREAKING**: la preparación del cliente pasa a ser exclusivamente manual: una persona ejecuta `openspec init --tools agents --no-animation`, configura contexto y workflows, crea el PR e integra sus cambios antes de usar la App. Se retira el onboarding automatizado soportado por el Harness.
- Exigir configuración y skills requeridas en el SHA base; la App no inicializa, actualiza ni prepara repositorios cliente.
- Añadir un lector acotado de `.agents/skills/openspec-*/SKILL.md` del checkout cliente, sin copias alternativas en la App ni permisos derivados de su contenido.
- Combinar skills de explore/propose/update/apply/verify/sync/archive, instrucciones CLI aplicables, dependencias, HU y RepoContext con los contratos JSON existentes. No se inventan subcomandos CLI explore/propose/verify/sync.
- Conservar estados, endpoints, acciones, aprobación del plan, manifiesto y publicación automática del candidato verificado; el contenido generado puede variar, el recorrido conversacional se mantiene.
- Registrar identidad y hashes de instrucciones por llamada y mantenerlos estables al recuperar el intento. Las actualizaciones de CLI y skills se coordinan fuera de las HUs mediante PR humano.

## Capabilities

### New Capabilities

- `openspec-skill-consumption`: carga segura, compatibilidad y composición por fase de skills del repositorio cliente.

### Modified Capabilities

- `client-workspace`: preparación manual externa y validación previa de skills, sin onboarding automático.
- `conversation-review`: continuidad del contrato conversacional y presentación de preparación pendiente sin pasos adicionales.
- `observability-control`: procedencia reproducible de skills e instrucciones por intento, revisión y llamada.

## Impact

Se afectan `harness/conversation.py`, `harness/openspec.py`, el nuevo `harness/skills.py`, contratos/configuración y persistencia de llamadas/checkpoints; `app/onboard_client.py` se retira del procedimiento soportado. README, operación, guía del workflow y fixtures/pruebas deben reflejar la preparación manual. La versión CLI permanece fijada y los workflows requeridos incluyen verify, ausente del perfil core instalado. No se amplían las rutas editables del cliente ni se modifican recursos Databricks, repositorios cliente, modelos autorizados, merge o despliegue en este cambio.
