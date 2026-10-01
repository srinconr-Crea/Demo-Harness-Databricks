# Proposal

## Why

El motor y la UI ya trabajan con un perfil, pero el arranque exige un YAML dentro del código distribuido y el target dev y el lanzador fijan valores del piloto. Para ofrecer un producto independiente y continuar probando con NaturaPet, cada instalación debe poder seleccionar un cliente mediante configuración de despliegue sin editar Python ni HTML.

## What Changes

- Adoptar una App por cliente con el mismo código del harness; excluir selector multicliente y cambio de cliente en caliente.
- Cargar un perfil externo aprobado por el operador mediante `HARNESS_CLIENT_PROFILE_PATH`, con validación, SHA-256 esperado y fallo cerrado. El despliegue entrega el archivo; el arranque no clona un repo para obtener autorizaciones.
- Permitir que la fuente versionada del perfil esté en `.harness/client.yaml` del cliente, pero activar solo una copia concreta aprobada fuera del checkout de HU. Proteger `.harness/` en edición y publicación.
- Separar valores del piloto de la definición reutilizable del bundle; entregar un procedimiento de empaquetado local de despliegue y configuración de recursos por instalación, sin secretos en archivos versionados.
- Conservar temporalmente `HARNESS_CLIENT_PROFILE` como modo legado explícito; rechazar selección ambigua y no usarlo como fallback de un perfil externo inválido. Migrar el piloto al modo externo y retirar su YAML del árbol de runtime genérico.
- Registrar el hash del perfil por intento y llamada; bloquear continuación bajo políticas distintas y preservar consulta histórica.
- Parametrizar el lanzador Windows y consultar la URL de la App seleccionada. Mantener identidad visual del producto y nombre de cliente dinámico, sin agregar campos de HU.
- Separar guía genérica, ejemplos de cliente y operación del piloto, conservando evidencias y sus enlaces.

## Capabilities

### New Capabilities

- `single-client-deployment`: configuración externa y reproducible de una instalación dedicada a un cliente, bundle reutilizable, arranque parametrizado e identidad visual.

### Modified Capabilities

- `client-policy`: selección confiable y validación del perfil externo, compatibilidad explícita y protección de `.harness/`.
- `observability-control`: procedencia del perfil por intento y llamada y rechazo de recuperación con configuración diferente.

## Impact

`app/start_server.py`, `harness/contracts.py`, `conversation.py`, `conversation_webapp.py`, contratos de llamadas, controles de publicación, `config/clients/`, `databricks.yml`, recursos que necesiten variables, `iniciar-harness.bat`, scripts de empaquetado, README, docs, ejemplos y pruebas. Los nuevos campos de procedencia serán opcionales para lectura histórica, con política explícita de reintento para intentos antiguos sin hash.

La implementación comprobará el piloto con sus recursos demo_harness existentes y un segundo cliente sintético local. Esta propuesta no despliega, crea permisos ni modifica NaturaPet; la preparación OpenSpec y el merge de cliente siguen siendo humanos. Se conservan Sonnet obligatorio, Haiku asesor, pruebas y publicación feature/* con PR.
