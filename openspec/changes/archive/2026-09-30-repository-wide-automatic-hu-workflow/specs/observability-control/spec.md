# Spec Delta

## ADDED Requirements

### Requirement: Checklist de fases con evidencia
La App SHALL mostrar explore, propose, update cuando aplique, apply, verify, sync, archive y PR con estados y fechas derivados de eventos persistidos del intento y revisión. SHALL conservar tiempos UTC y presentarlos en America/Bogota. SHALL distinguir pendiente, en curso, correcto, fallido, bloqueado y no aplicable; ningún OK SHALL inferirse solo por alcanzar una etapa posterior. La creación del PR y sus checks SHALL mostrarse por separado.

#### Scenario: HU completa
- **WHEN** se confirma creación del PR
- **THEN** se muestra checklist de fases completadas, fechas y enlace al PR con checks reales

#### Scenario: Fallo parcial
- **WHEN** falla archive o publicación
- **THEN** la fase fallida se identifica y las posteriores no aparecen OK

#### Scenario: Reinicio o nueva revisión
- **WHEN** se recupera un intento o se actualiza el plan
- **THEN** el resumen conserva historia y no reutiliza éxitos obsoletos como evidencia vigente

#### Scenario: Recomendación o check pendiente
- **WHEN** Haiku tiene hallazgos o los checks están pending o unavailable
- **THEN** se distinguen de fallos obligatorios y de creación exitosa del PR
