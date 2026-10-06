# Proposal

## Why

La ejecución `4684261fbd554fea87185a765dc754f8` falló en aplicación y en su reintento porque el desarrollador devolvió `base_sha256` donde el editor exige `expected_sha256`. El flujo de correcciones clasificado reemplaza la instrucción que enumera los campos de operaciones por una descripción genérica, por lo que el modelo no recibe el contrato completo que después se valida.

## What Changes

- Proporcionar un contrato confiable y único de salida del desarrollador, basado en los tipos del editor, con campos, tipos, reglas condicionales y ejemplos exactos de create/modify/delete.
- Adjuntar ese contrato a todas las llamadas de aplicación y corrección, incluidas las rondas de contexto, con gestor habilitado o deshabilitado; la descripción de tareas no podrá sustituirlo.
- Explicitar archivo completo UTF-8, hash de bytes actuales y cobertura de cada ruta del manifiesto, distinguiendo propuesta de operación de pruebas ejecutadas.
- Emitir diagnósticos acotados por entrada/campo, conservando rechazo, respuesta original y procedencia sin convertir aliases ni eliminar campos desconocidos.
- Verificar prompts efectivos y recorridos de aceptación/rechazo con pruebas sintéticas. Mantener contratos históricos y silver_safe_ratio diferenciados.
- Mantener Sonnet 5.5, tarifas, presupuestos, pruebas obligatorias y reintento humano existentes. No incorporar llamadas automáticas de reparación ni activar JSON Schema remoto.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `agent-prompt-contracts`: contrato explícito del desarrollador por estrategia/modalidad y diagnósticos seguros para operaciones inválidas.

## Impact

Producto del harness: `harness/prompt_contracts.py`, `harness/patch.py`, `harness/conversation.py`, `harness/repo_context.py`, `config/defaults/prompts.yaml` y pruebas de contratos/contexto/correcciones. Se actualizará la guía de operación y la versión/hash de prompts. No requiere dependencias, migración de registros, cambios de infraestructura ni edición del repositorio o recursos NaturaPet. Esta propuesta no acredita implementación ni despliegue y no reejecuta la HU fallida.
