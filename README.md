# Demo Harness Databricks

Personalización versionada de Omnigent para una demo local de desarrollo en NaturaPet. Omnigent 0.15.0 corre en `localhost:6767`; Codex/GPT-6-Sol es el executor. Este repositorio contiene agentes, instrucciones y políticas; el código de datos permanece en `Naturapet_DLH`.

## Estructura

- `agents/developer/config.yaml`: agente principal con roles Architect y Reviewer como subagentes.
- `prompts/`: requisito común del piloto.
- `policies/`: límites y pruebas de gobernanza de la demo.
- `tools/`: instrucciones para Databricks CLI y Genie en modo lectura.
- `.omnigent/`: lugar reservado para configuración de proyecto sin secretos.

## Fase local

1. Clonar `https://github.com/srinconr-Crea/Naturapet_DLH.git` desde `develop` en una carpeta nueva y crear `codex/demo-gold-gate-omnigent`.
2. Confirmar `databricks current-user me --profile CREA_DEV`, `databricks bundle validate --target dev --profile CREA_DEV` y acceso a Genie `01f14d4947151439be25af51c40e1111`.
3. Desde la raíz de la clonación de NaturaPet, ejecutar el agente con el CLI de Omnigent del host:

   ```text
   omni run <ruta-absoluta>/agents/developer/config.yaml --model gpt-6-sol --server http://127.0.0.1:6767 -p "<requisito del piloto>"
   ```

4. Revisar pruebas, diff, trazas de políticas y la intervención de Reviewer antes de publicar un PR draft hacia `develop`. Si el ejecutor o los subagentes fallan, registrar la brecha; un prompt no prueba gobernanza.

La [evaluación local](docs/evaluacion-local.md) recoge resultados, PR y brechas.
El [prototipo mínimo](docs/harness-prototipo.md) define la siguiente prueba de
controles antes de decidir una fase managed.

No guardar tokens, perfiles ni credenciales en Git. Esta demo no despliega bundles ni ejecuta jobs. La conexión OAuth integrada de Omnigent no está activa en la instancia local actual; Git y Databricks CLI usan la identidad del host.

## Fuentes

- [Especificación YAML de Omnigent](https://github.com/omnigent-ai/omnigent/blob/main/docs/AGENT_YAML_SPEC.md)
- [Políticas de Omnigent](https://omnigent.ai/docs/policies/builtin)
- [Repositorio NaturaPet](https://github.com/srinconr-Crea/Naturapet_DLH/tree/develop)
