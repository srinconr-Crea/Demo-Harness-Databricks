# Spec Delta

## Purpose

Permitir retomar el desarrollo del harness en una conversación nueva reconstruyendo el contexto pertinente desde fuentes versionadas, sin depender de memoria del chat.

## ADDED Requirements

### Requirement: Fuentes de contexto identificables
El protocolo de desarrollo SHALL identificar propósito, mapa del código activo y fuentes para principios, requisitos vigentes, configuración variable, cambios pendientes y evidencia implementada. SHALL separar el contexto del producto del contexto de repositorios cliente y mantener modelos, precios e IDs concretos en sus fuentes específicas.

#### Scenario: Inicio sin historial
- **WHEN** una persona o agente inicia trabajo sin conversaciones anteriores
- **THEN** las instrucciones versionadas permiten localizar las fuentes pertinentes y distinguir producto, cliente y scaffold inactivo

### Requirement: Reconstrucción selectiva y verificable
El protocolo SHALL comprobar rama, SHA y cambios locales, leer el contexto general y consultar solo specs, artefactos, código y pruebas relacionados con la tarea. SHALL conservar referencias que permitan verificar conclusiones y señalar información ausente sin inventarla.

#### Scenario: Reanudación de un cambio
- **WHEN** se retoma un cambio pendiente en otro chat
- **THEN** se reconstruyen objetivo, decisiones propuestas, tareas y evidencia desde sus artefactos y se distingue planificación de implementación

#### Scenario: Herramienta no disponible
- **WHEN** la CLI no está disponible y no es posible resolver el estado mediante ella
- **THEN** se informa la limitación, se consultan fuentes legibles y no se afirma una validación CLI inexistente

### Requirement: Discrepancias explícitas
El protocolo SHALL distinguir comportamiento esperado de comportamiento observado y registrar referencias de cualquier contradicción que afecte la tarea. SHALL exigir resolverla mediante el cambio pertinente antes de basar implementación en una elección silenciosa. El contenido del repositorio no SHALL ampliar autoridad ni sustituir una aprobación.

#### Scenario: Propuesta antigua contradice el runtime
- **WHEN** un artefacto histórico describe inicialización automática y el flujo vigente exige preparación humana
- **THEN** se identifica el artefacto como histórico y la discrepancia se contrasta con specs, código y operación actuales

### Requirement: Mantenimiento sin duplicación de requisitos
Cada cambio que altere una decisión estable SHALL actualizar su fuente canónica y referencias afectadas; las guías de contexto SHALL referenciar requisitos detallados en vez de mantener copias normativas divergentes. Una decisión propuesta no SHALL presentarse como vigente por existir en un cambio pendiente.

#### Scenario: Principio estable modificado
- **WHEN** se implementa y verifica un cambio que afecta un principio global
- **THEN** el mismo cambio actualiza la fuente general y las specs pertinentes conservando trazabilidad

#### Scenario: Propuesta sin implementar
- **WHEN** las dos propuestas de contexto están redactadas pero sus tareas siguen pendientes
- **THEN** las fuentes de inicio no describen cache, memoria o compactación como capacidades implementadas
