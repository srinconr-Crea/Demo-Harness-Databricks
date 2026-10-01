# Tasks

## 1. Carga externa y protección de política

- [x] 1.1 Implementar selección externa de perfil en contracts/arranque con ruta relativa a ROOT o absoluta, límite 128 KiB, rechazo de enlaces, lectura única, validación YAML y SHA-256 esperado; verificar archivo válido, ausente, ilegible, inválido, grande, traversal y hash faltante o divergente con pruebas sin credenciales.
- [x] 1.2 Conservar modo legado explícito, rechazar ambos modos simultáneos, hash sin ruta y selección ausente sin fallback; verificar selección válida por nombre y todos los rechazos en pruebas de arranque.
- [x] 1.3 Proteger .harness/ determinísticamente en edición, manifiesto, estado final y publicación; verificar create/modify/delete bajo alcance repository, candidato manipulado y que el YAML del checkout no sustituye el activo.
- [x] 1.4 Documentar selección, límites y frontera de confianza en la guía de configuración; verificar que ejemplos distinguen archivo fuente, copia activada y variables runtime sin claves privadas ni tokens.

## 2. Procedencia y recuperación

- [x] 2.1 Extender contratos de intento y llamada con procedencia opcional de perfil y snapshot protegido por referencia; verificar persistencia, checkpoints, coincidencia de hash en llamadas y lectura de JSON históricos sin backfill.
- [x] 2.2 Comprobar perfil y repositorio en worker, acciones y publicación antes de consumir autorizaciones; verificar recuperación con mismo hash y bloqueo con bytes distintos aun conservando nombre y versión.
- [x] 2.3 Implementar reintento explícito con nueva planificación para históricos sin hash o perfil cambiado en el mismo repo, rechazando otro repo; verificar nueva aprobación, conservación del historial y consulta/cancelación autorizadas del intento bloqueado.
- [x] 2.4 Documentar cambio de política, drenaje de intentos, snapshots y recuperación en operación; verificar que el procedimiento no propone reutilizar aprobaciones, borrar checkpoints ni exponer el perfil en prompts o respuestas públicas.

## 3. Paquete por instalación y migración del piloto

- [x] 3.1 Separar variables de cliente y entorno del bundle genérico y agregar parámetros necesarios de ubicación y hash de perfil sin renombrar recursos del piloto; verificar configuraciones renderizadas y referencias de resources con pruebas de YAML.
- [x] 3.2 Crear empaquetador local para .deployments/<id> con destinos validados, selección de fuentes, perfil entregado y manifiesto de revisión/hash/variables; verificar dos paquetes con mismo código, paths runtime resolubles, rechazo de colisiones y exclusión de secretos, runtimes, registros y perfiles ajenos.
- [x] 3.3 Ignorar paquetes generados y excluirlos de sincronización no intencional; verificar reglas Git/sync y que config/deployment/client.yaml se entrega únicamente en el paquete seleccionado y no al sandbox.
- [x] 3.4 Mover el perfil NaturaPet a examples/naturapet y añadir ejemplo sintético, conservando configuración operativa del piloto y pruebas de su alcance; verificar que el runtime genérico no contiene perfiles cliente activos y que silver_safe_ratio conserva compatibilidad.
- [x] 3.5 Actualizar guía de despliegue con preparación, variables, ACL, recursos por instalación, validación y rollback; verificar comandos desde el paquete y revisar prepare_app_only_deployment.py y provisión para que no dependan de valores retirados del target genérico.

## 4. Inicio y presentación del producto

- [x] 4.1 Parametrizar iniciar-harness.bat o su helper con App y perfil CLI y consultar URL mediante salida estructurada; verificar mediante CLI simulada parámetros con espacios, ausencia de argumentos, errores, URL ausente/inválida y apertura de la App correcta sin URL fija.
- [x] 4.2 Mantener identidad común y nombre dinámico del cliente en UI y /configuration, conservando formulario HU/descripción; verificar dos configuraciones con nombres distintos, fallback visual y ausencia de perfil íntegro o secretos en respuesta.
- [x] 4.3 Actualizar README y operación genéricos y guía del piloto, eliminando hints sin consumo del ejemplo y preservando evidencia histórica; verificar enlaces locales y que pasos del producto no presuponen NaturaPet ni CREA_DEV.

## 5. Verificación integrada

- [x] 5.1 Ejecutar recorridos locales con dos clientes sintéticos preparados y el mismo código, desde empaquetado y arranque hasta aprobación, pruebas y publicación simulada; verificar separación de repos, UI, políticas, registros y sandbox, más bloqueo por cambio de perfil tras reinicio, sin escribir en NaturaPet.
- [x] 5.2 Ejecutar suite completa del harness y validación estricta OpenSpec; registrar resultados en verification.md del cambio y corregir fallos antes de publicar.
- [x] 5.3 Ejecutar databricks bundle validate --strict -t dev --profile CREA_DEV desde el paquete del piloto con sus recursos actuales; registrar evidencia o bloqueo operativo sin sustituirlo por una afirmación de grants verificados ni ejecutar deploy/run.
- [x] 5.4 Revisar diff final, manifiesto de paquete y ausencia de valores cliente en defaults activos; registrar preparación de migración y rollback y dejar despliegue cloud y smoke test real como operación posterior humana, sin marcar evidencia local como despliegue realizado.
