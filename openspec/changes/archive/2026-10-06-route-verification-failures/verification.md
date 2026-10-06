# Evidencia de implementación

Base revisada: `8765443801731830786285878b577896c81a853c`, rama `Db_Spec_Harness`.

## Alcance

El cambio clasifica los fallos obligatorios, conserva el plan aprobado durante correcciones de implementación y limita a dos sus correcciones lógicas. Los cambios de alcance esperan otra aprobación. Se validan capacidades OpenSpec, cobertura sin reescritura y diff acumulado. Haiku conserva su función asesora.

Las pruebas usan repositorios y modelos simulados, Git real y CLI OpenSpec real cuando corresponde. La reproducción f9c8 conserva once criterios sintéticos de normalización; no reproduce datos ni afirma recuperar exactamente la suite histórica. No reejecuta la HU cliente ni publica un PR real en su repositorio.

## Comprobaciones focalizadas

- Clasificación, contratos y progreso: 17 passed en `test_failure_routing.py` y `test_ui_corrections.py`.
- Validadores Python/SQL/YAML y runner: 7 passed.
- Contratos confiables, logging de candidato e interfaz: 24 passed.
- Transferencia de lecturas con hashes actuales: 2 passed, ambos modos de contexto.
- Tiempo acumulado de contexto, observaciones y controles existentes: 5 passed. El límite configurado se conserva; la latencia del modelo no consume ni renueva tiempo de operaciones.
- Destino OpenSpec real, dos archivos aplicados, cobertura sin operaciones y once criterios: 2 passed, incluyendo estado de tareas posterior a verify y PR simulado.
- `openspec validate route-verification-failures --strict`: válido.
- Revisión independiente: resueltos reinicio del contador al cambiar base, doble consumo de lecturas y falsa señal de progreso por cambios ajenos o prosa. La publicación exige verificación vigente del candidato y bytes del plan aprobado.

## Suite completa y cierre

Se ejecutó `python -m pytest tests -q -p no:cacheprovider` con un directorio temporal externo al checkout: 424 passed, 1 failed y 1 skipped en 2213,56 segundos. El único fallo correspondió a la fixture f9c8 cargada al iniciar la suite, cuyo delta MODIFIED omitía el escenario base `Input`. Se corrigió conservando ese escenario y se volvió a ejecutar el módulo completo: 2 passed en 140,04 segundos. No se relajó la validación OpenSpec para resolverlo.

Las modificaciones posteriores relativas a tiempo de operaciones de contexto, referencias recuperables, metadatos del candidato y estado final de tareas se comprobaron mediante las ejecuciones focalizadas indicadas arriba. La revisión y las pruebas no dejan fallos conocidos pendientes; estos resultados combinan una ejecución general con verificaciones focalizadas posteriores, sin afirmar que la ejecución general original terminó con cero fallos.

Se revisó la correspondencia de las cuatro specs delta, los contratos, el flujo y la documentación. La sincronización conserva requisitos y escenarios existentes. La validación del bundle y el despliegue se distinguen de estas pruebas locales y no se atribuye aquí evidencia de un smoke remoto.
