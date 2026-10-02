# Spec Delta

## ADDED Requirements

### Requirement: Trazabilidad de contexto y prompts
El harness SHALL registrar por HU, intento, revisión, etapa y llamada la política y hash del prompt, referencias/hashes de fuentes, decisión de contexto, razón, bytes estimados, hits/misses e invalidaciones de cache y referencias de memoria o compactación utilizadas. SHALL conservar evidencia protegida separada de la vista pública; no SHALL exponer fuentes restringidas ni inventar metadatos históricos.

#### Scenario: Cache y memoria utilizadas
- **WHEN** una llamada reutiliza cache y decisiones confirmadas
- **THEN** se pueden reconstruir sus fuentes y elecciones desde evidencia enlazada sin mostrar contenido protegido en el hilo principal

#### Scenario: Histórico anterior
- **WHEN** se consulta una llamada sin campos de gestión de contexto
- **THEN** esos campos aparecen ausentes y no se presentan como decisiones observadas

### Requirement: Costos de compactación reales
Toda llamada auxiliar de compactación SHALL registrarse con rol, propósito, modelo configurado, tiempos, uso y costo estimado cuando el endpoint proporcione uso, incluso cuando se rechace su resumen. Una operación local de cache o reducción determinista no SHALL registrarse como llamada al modelo ni como ahorro facturado.

#### Scenario: Resumen rechazado
- **WHEN** se invoca un modelo para compactar y el resumen no supera validación
- **THEN** la llamada y su costo informado permanecen auditables aunque no se utilice el resultado

#### Scenario: Uso no informado
- **WHEN** una llamada auxiliar no devuelve usage
- **THEN** el costo queda ausente y no se sustituye por cero
