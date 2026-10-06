# Contratos explícitos del desarrollador

Cambio `explicit-developer-operation-contracts`, base `c1208cbae21eba7ecd1a933d70a02bb74fc6b4b6`, rama `Db_Spec_Harness`. El incidente observado fue `4684261fbd554fea87185a765dc754f8`: ambas salidas finales de aplicación usaron base_sha256 en lugar de expected_sha256. Se conserva como histórico, sin reintento automático ni modificación.

## Implementación y alcance

El descriptor derivado de FileOperation/ManifestCoverage se añade en contextual_answer antes de preparar/serializar el prompt, en aplicación, corrección y rondas de contexto. Cada modalidad recibe sus campos; los ejemplos filtran operaciones por perfil. Catálogo `role-contracts-v6`, modelo Sonnet 5.5 y presupuestos anteriores. Los mensajes de forma solo imprimen índice y campos conocidos o etiquetas genéricas; la modalidad sin gestor también registra aceptación rechazada. Política y hashes no reciben tratamiento de formato recuperable.

No se cambia el perfil aprobado, recursos de NaturaPet ni el sandbox. El contenido y SHA-256 de la respuesta siguen conservándose en evidencia protegida, sin aliases aceptados ni llamadas correctoras.

## Verificación local

Primer ciclo unitario: 15 failed, 1 passed, 2 deselected; fallos esperados por contrato ausente y diagnósticos genéricos. Se corrigió además un fixture cuyo perfil no autorizaba src/. La primera ejecución integral incluía una firma incorrecta de retry en el nuevo test; se corrigió a failure_id, sin cambiar el producto.

Revisión independiente: detectó op como lista/dict antes de validar tipo y cambio de retry en max_files. Ambos se corrigieron. Regresión adicional previa a la corrección: 6 failed, 5 passed; después de aplicar la guardia de tipo y conservar ValueError para el límite, 28 passed, 2 deselected. La segunda revisión no dejó bloqueos.

Comando unitario:

```powershell
$env:PYTHONUTF8='1'
src/agents/harness/.venv/Scripts/python.exe -m pytest tests/test_developer_operation_contracts.py -q -p no:cacheprovider -k 'not checkpoint' --basetemp="$env:TEMP/dcg2"
```

Los temporales Windows de pytest requieren ejecución fuera del sandbox; el intento restringido inicial falló por permisos, no por producto. Se conserva la advertencia existente Starlette/httpx. Logs locales ignorados en `.deployments/developer-contract-*.log`.

Suite nueva completa: 30 passed, 0 failed (191,68 s). El recorrido reforzado con compilación y evaluación del candidato sintético pasó en ambas modalidades: 2 passed, 28 deselected (283,94 s). Comprueba rechazo sin publicación, retry humano con failure_id/revisión, restauración de checkpoint, valores evaluados 3/4 tras aplicación/corrección y PR simulado después de verificar. No se ejecutó una HU cliente real.

El descriptor para el perfil aprobado ocupa 3.410 bytes UTF-8. Las pruebas verifican presencia en snapshots, límite acotado y bloqueo por presupuesto sin truncamiento ni modificación de límites.

La suite del proyecto se distribuye en seis grupos de node IDs únicos, con temporales separados: 464 casos recolectados, tamaños 78/78/77/77/77/77. Las corridas iniciales redundantes se detuvieron tras las correcciones de revisión. Resultado final: 464 passed, 0 failed, 0 skipped; los seis grupos terminaron con exit_code 0 en 1.121,59 s de tiempo total. Véase suite-results.json para duraciones individuales. OpenSpec validate --strict pasó para el cambio y las 15 especificaciones principales; git diff --check pasó sobre el alcance. Esta evidencia local no acredita todavía despliegue.

## Preflight operativo

Perfil CLI seleccionado por el usuario: CREA_DEV. App `demo-dbx-harness-mvp`, compute STOPPED; nueve registros, dos complete, seis failed y uno cancelled, sin pendientes. Se conservan hashes exactos de cada registro y todos los bindings para comparar después del despliegue. Fuente previa de rollback: `/Workspace/Users/srinconr@creasistemas.com/apps/demo-harness-corrections-20261006`.

Paquete local `developer-contracts-20261006`: bundle validate --strict -t dev --profile CREA_DEV terminó Validation OK. Su app.yaml se copió byte a byte de la fuente previa y el perfil entregado coincide: SHA256 `27ac71c9b2c0c3bdea588ee77d06df20eedb228fbf47002121404f6f7f0df01f`. Esta validación no demuestra ejecución remota.

## Entrega y verificación remota

OpenSpec sincronizado y archivado en 2026-10-06-explicit-developer-operation-contracts, con 12/12 tareas. Commit de producto 9cb7c69588d46a240b0f80cc71e28edce0ebdbfc publicado y comprobado en origin/Db_Spec_Harness antes de cargar el paquete. Los cambios locales previos ajenos al ajuste quedaron fuera del commit.

La sesión OAuth de CREA_DEV se renovó al detectar refresh token inválido. El arranque de la App generó primero un despliegue de su fuente anterior; se esperó a que terminara antes de enviar la fuente de verificación. No hubo cambios de bindings ni edición de históricos.

Verificación con identidad de App: cuatro llamadas reales a databricks-claude-sonnet-5-5, coste estimado USD 0.025228 (no facturación). Cada modalidad on/off pidió una lectura y produjo una operación canónica con hash de bytes actuales; se aplicó exclusivamente en un directorio temporal sintético. Ambas rechazaron además un alias inyectado sin nueva llamada ni escritura. Uso, costo e identificadores originales están protegidos en el volumen del harness; deployment.json contiene el resumen sin textos de prompts/respuestas.

Despliegue final 01f1c1c9cfd41716a59e93172acfaa2f: SUCCEEDED y App RUNNING. Se compararon SHA-256 de los 41 archivos del snapshot contra el paquete publicado y se comprobó ausencia del verificador temporal. GET /, /configuration y el histórico 4684261fbd554fea87185a765dc754f8 devolvieron 200. Los nueve históricos conservaron sus bytes; el incidente mantiene failed y su error original. Perfil, app.yaml y bindings permanecen iguales.

La prueba remota acredita el contrato y ejecución sintética, no una HU real ni un PR cliente. El cambio de catálogo a role-contracts-v6 mantiene el control de compatibilidad para continuar intentos previos; no se forzó retry del incidente.
