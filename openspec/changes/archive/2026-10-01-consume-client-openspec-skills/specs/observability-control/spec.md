## ADDED Requirements

### Requirement: Procedencia de instrucciones por fase
El harness SHALL registrar por intento, revisión y llamada la fase, SHA base, ruta relativa y SHA-256 de skills consumidas, versión CLI e identidad y hash de instrucciones CLI aplicables. SHALL vincular evidencia con run_id, attempt_id y call_id, incluidos fallos y rondas de contexto, preservando tokens y costos existentes. Los históricos SHALL admitir procedencia ausente sin rellenarla artificialmente. El registro resumido no SHALL sustituir bytes o referencias protegidas necesarias para reproducir instrucciones.

#### Scenario: Varias rondas del modelo
- **WHEN** un rol realiza solicitudes de contexto antes de devolver su respuesta final
- **THEN** cada llamada registra la misma procedencia de fase y su propio call_id, tokens y costo cuando estén disponibles

#### Scenario: Fase determinista
- **WHEN** sync o archive se ejecutan sin invocar un modelo
- **THEN** su evento registra las skills e instrucciones consumidas y la evidencia real sin inventar llamadas o costos

#### Scenario: Recuperación
- **WHEN** un intento se restaura desde un checkpoint
- **THEN** se comprueban hashes de skills y compatibilidad del runtime con la procedencia guardada antes de continuar

#### Scenario: Instrucciones cambiadas
- **WHEN** los bytes de las skills o el runtime requerido no coinciden con lo registrado
- **THEN** se bloquea la continuación sin actualizar instrucciones ni reutilizar una aprobación como si nada hubiera cambiado

#### Scenario: Lectura histórica
- **WHEN** se consulta un registro sin campos de procedencia
- **THEN** se conserva legible y la procedencia aparece ausente
