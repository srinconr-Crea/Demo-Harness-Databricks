# Tasks

## 1. Fuentes y punto de entrada

- [x] 1.1 Revalidar las fuentes afectadas contra rama/SHA vigente al iniciar apply y registrar discrepancias relacionadas en el cambio; verificar que propuestas pendientes y documentos históricos no se tratan como implementación actual.
- [x] 1.2 Simplificar `openspec/config.yaml` conservando idioma, mapa activo, principios y referencias sin endpoints/precios/IDs variables; verificar YAML válido, context máximo 8 KiB y que rules/operations conservan sus controles.
- [x] 1.3 Crear `docs/contexto-proyecto.md` con protocolo de inicio/reanudación, responsabilidades de fuentes y manejo de drift; verificar con el caso de HU de cantidades que permite localizar specs y pruebas sin precargar todo el repo.
- [x] 1.4 Referenciar la guía desde AGENTS, README y operación sin duplicar requisitos ni alterar límites; agregar comprobaciones de referencias/parseo en `tests/test_project_context.py` y verificar rutas reales, incluida corrección de referencias de pruebas inexistentes relacionadas.

## 2. Decisiones y reconstrucción

- [x] 2.1 Documentar cuándo conservar decisiones en design/specs y cuándo usar `docs/decisions/`, con estado y vínculos de origen/sustitución; verificar un ejemplo sin crear una segunda copia normativa del requisito.
- [x] 2.2 Ejecutar un ejercicio de reanudación sin historial sobre un cambio pendiente y conservar evidencia breve; verificar objetivo, decisiones propuestas, tareas, fuentes y siguiente paso correctos.
- [x] 2.3 Ejecutar un ejercicio de contradicción entre histórico e inicialización humana vigente; verificar detección, fuentes citadas y ausencia de aprobación o implementación inferida.

## 3. Verificación integrada

- [x] 3.1 Validar estrictamente el cambio y ejecutar la suite local antes de publicar; verificar que no cambió runtime, API ni política y registrar resultados reales.
- [x] 3.2 Sincronizar y archivar únicamente después de implementar y verificar este cambio; revisar diff y preparar publicación con evidencia en Db_Spec_Harness, por solicitud explícita del usuario, verificando que la propuesta hermana conserva sus tareas pendientes. El redepliegue solicitado es únicamente de la App del harness.
