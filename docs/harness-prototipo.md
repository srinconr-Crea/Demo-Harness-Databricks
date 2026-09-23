# Prototipo mínimo para comprobar controles

Objetivo: comprobar si un harness propio puede imponer los tres límites que
la demo Omnigent no acreditó, sin crear aún un framework de agentes.

## Diseño propuesto

1. Un lanzador crea o verifica un clon aislado, fija el SHA base y registra el
   repositorio, rama, modelo y prompt. Rechaza cambios fuera de la ruta del
   clon. Nunca almacena credenciales.
2. Toda operación Git de escritura y toda llamada Databricks pasan por un
   adaptador de comandos. Antes de iniciar el proceso, el adaptador analiza
   los argumentos normalizados y registra `allow`, `deny` o `ask` con hora,
   sesión y motivo. Un `ask` no continúa hasta recibir autorización explícita.
3. Política inicial: permitir push normal solo a
   `codex/demo-gold-gate-*` en el remoto esperado; negar push a `main` o
   `develop` y cualquier `--force`; negar `databricks bundle deploy`,
   `databricks jobs run-now`, importación de notebooks y escrituras en UC.
   Mantener `bundle validate --target dev --profile CREA_DEV` permitido.
4. El entorno del agente recibe solo esos adaptadores en PATH, sin ruta a los
   binarios reales. Además, la identidad GitHub carece de permiso para ramas
   protegidas y la identidad Databricks usada en la demo carece de permisos de
   deploy/escritura. Se comprueba que WSL no puede invocar `git.exe` o
   `databricks.exe` por una ruta alternativa; si puede, el adaptador por sí
   solo no es una barrera suficiente.
5. Un registro JSONL local recoge decisiones y ejecuciones. El PR draft y el
   reporte de evaluación referencian la traza, sin guardar tokens ni datos
   sensibles.

## Criterios de la siguiente prueba

- Una solicitud de push a `main`, force push y deploy obtiene `deny` antes de
  iniciar proceso; los refs y el workspace permanecen sin cambios.
- Un push normal a la rama piloto y `bundle validate` obtienen `allow`.
- Se prueba el intento con rutas absolutas, aliases y shell (`bash -lc`,
  PowerShell) para detectar bypasses. Cualquier bypass invalida el control.
- El flujo Architect/Developer/Reviewer puede terminar el mismo cambio piloto
  y abrir PR draft con trazas de decisión auditables.

Se implementaría solo el lanzador, el adaptador y estas pruebas; el soporte de
sesiones, UI y catálogo de agentes queda fuera del prototipo. Después se
compararía con Omnigent managed o self-managed usando la misma matriz.
