# Spec Delta

## ADDED Requirements

### Requirement: Trazabilidad de selección y prompts
El harness SHALL registrar por HU/intento/revisión/etapa/llamada política, versión/hash de prompt/contrato, fuentes/hash, decisión de contexto, razones de inclusión/exclusión, bytes completos antes/después, estimación identificada y cache hit/miss/invalidaciones. SHALL conservar evidencia protegida sin exponer memoria/prompts restringidos ni inventar históricos.

#### Scenario: Contexto reducido
- **WHEN** una llamada reutiliza cache y elimina duplicados
- **THEN** sus fuentes, decisiones preservadas, exclusiones y bytes enviados son auditables sin revelar contenido protegido en hilo público

#### Scenario: Histórico anterior
- **WHEN** una llamada no contiene campos nuevos
- **THEN** aparecen ausentes y no se presentan como decisiones observadas

### Requirement: Medición comparable sin ahorro ficticio
La evaluación SHALL comparar escenarios con mismas entradas, respuestas y solicitudes de contexto, registrando llamadas, bytes enviados, latencia y usage/costo estimado solo cuando existe. Cache/reducción local no SHALL generar llamadas ficticias ni presentarse como ahorro facturado. SHALL verificar preservación de decisiones y controles, separando mediciones locales de pruebas remotas.

#### Scenario: Cache sin reducción de entrada
- **WHEN** un hit evita lectura local pero envía los mismos bytes al modelo
- **THEN** se informa reutilización de I/O sin atribuir reducción de tokens

#### Scenario: Uso ausente
- **WHEN** endpoint no proporciona usage
- **THEN** costo queda ausente, no cero, y no se afirma ahorro de costo comprobado

#### Scenario: Comparación y estrés
- **WHEN** se ejecutan fixtures comparables y estrés acotado de múltiples turnos
- **THEN** se conservan decisiones/autorizaciones requeridas o se bloquea correctamente por presupuesto, sin promesa universal de duración
