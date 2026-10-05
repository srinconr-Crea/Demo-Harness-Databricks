# Verificación de contratos de artefactos del planner

Cambio: `fix-planner-artifact-contracts`. Base:
`3938ac1c870171baef68dd3fb8d9d47c92e919c9`, rama `Db_Spec_Harness`.

## Implementación

El prompt versionado `role-contracts-v2` distingue el manifiesto de código/pruebas
de los artefactos OpenSpec y pide una sola serialización de content. Solo proposal
general_patch solicita summary/manifest. Los otros artefactos y silver_safe_ratio
conservan sus campos propios. El envelope JSON existente sigue admitiendo rondas
de contexto; la aceptación semántica y política son comprobaciones posteriores.

La validación compartida rechaza entradas OpenSpec, campos/tipos, operaciones,
rutas, extensiones y duplicados fuera de contrato sin filtrar entradas. Los
mensajes identifican índice y motivo; no reproducen rutas arbitrarias del modelo.
El original permanece en la evidencia protegida existente.

Antes de escribir se comprueban encabezados requeridos por el template confiable,
secciones delta y tareas reales. Los bloques de código no suministran estructura
del documento. No se decodifica content por segunda vez ni se sustituyen escapes
globalmente. Se conservan LF/CRLF, Unicode, comillas y escapes legítimos. La CLI
OpenSpec sigue validando el plan completo.

## Pruebas y revisión

Se reprodujeron primero los defectos con pruebas que fallaron por ausencia de la
validación. La revisión independiente detectó un cierre de fence incorrecto y
checkboxes de código indentado aceptados: las dos reproducciones fallaron antes
de corregirlas. El módulo final de regresión pasó 17 pruebas, incluyendo la
conservación del checkpoint parcial y failed en ambas modalidades de contexto.

La ejecución focal inicial pasó 74 pruebas de contexto, OpenSpec y recuperación.
La suite completa usa el Python de `.venv` con pytest, cuatro grupos por archivo,
`-q -p no:cacheprovider --tb=short --basetemp <TEMP>/hbN`. Es el ejecutor equivalente
permitido en las tareas ante restricciones de cache/temporales uv en el sandbox;
las rutas cortas evitan el límite Windows. Los cuatro grupos pasaron: 65, 65, 78 y 61 pruebas (269 en total). Las dos
regresiones añadidas después pasaron en la ejecución final de 17 pruebas del
módulo afectado: 271 pruebas distintas verificadas. Los logs están en
`.deployments/verification-artifact-contracts/`.
Las advertencias de Starlette/httpx existentes se distinguen de fallos.

Pasaron `git diff --check`, `openspec validate fix-planner-artifact-contracts
--strict`, `openspec validate --specs --strict` (15 specs) y la validación estricta
del paquete bundle con target dev/perfil CREA_DEV. No se cambiaron infraestructura,
perfil cliente, modelos, presupuesto 64000 ni reglas de retry.

La validación es sintética/local. No se invocó al planner remoto ni se reintentó
la HU real. Su último fallo ya está persistido; la consulta previa al despliegue
encontró cero HUs activas y la App STOPPED. El control de representación detecta
salidas defectuosas; no garantiza que un modelo nunca vuelva a generarlas.

## Publicación

Las tres delta specs se sincronizaron y las principales pasaron validación.
El cambio quedó archivado en
`openspec/changes/archive/2026-10-05-fix-planner-artifact-contracts/`, con 15/15
tareas completas y las tres delta specs verificadas contra sus principales.

Se desplegó únicamente la App `demo-dbx-harness-mvp`, con CREA_DEV, sin publicar
recursos del bundle. Deployment `01f1c0f60aca1f13a22f0dea77b149b3`, SNAPSHOT,
`SUCCEEDED` a las 19:50:58 UTC del 5 de octubre. Se comprobó la App RUNNING y
`Application startup complete` en logs; luego el cómputo quedó STOPPED.
El snapshot de prompt_contracts.py, openspec.py y prompts.yaml coincide por SHA256
con el paquete probado. Se conservaron los bindings operativos existentes.

La HU real permaneció idéntica antes/después del despliegue, SHA256
`7198beba289a62452eaf119441cbe6e069f83302def43c23a6e1c86d59b59f78`.
La consulta posterior encontró cero HUs activas. El warehouse del harness se
restauró a STOPPED porque el arranque de la App lo activó desde ese estado.
Los cambios preexistentes del ejemplo y la preparación cliente quedan fuera de
este cambio y de su commit. La publicación apunta a `origin/Db_Spec_Harness`.
