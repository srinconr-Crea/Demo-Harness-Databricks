## MODIFIED Requirements

### Requirement: Modelo del planner
El harness SHALL usar `databricks-claude-sonnet-5-5` para las llamadas que generan o actualizan artefactos OpenSpec. SHALL exigir ese mismo endpoint a explorer, developer y openspec_verifier en la configuración confiable del producto, conservando `databricks-claude-haiku-4-5` como verifier asesor. SHALL impedir que la historia o el repositorio cliente cambien esa selección. La instalación SHALL alinear routing y permiso CAN_QUERY de la App al endpoint nuevo antes de admitir HUs. SHALL conservar los límites actuales de 64.000 tokens del planner y fallback de 12.000 de los otros roles, así como los presupuestos actuales de contexto; una mayor capacidad anunciada no SHALL aumentarlos automáticamente. SHALL declarar soporte JSON Schema y límites del endpoint solo con evidencia específica de compatibilidad y conservar validaciones deterministas posteriores. Una incompatibilidad SHALL bloquear la habilitación sin fallback silencioso a otro modelo.

#### Scenario: Generación del plan
- **WHEN** el planner genera o actualiza un artefacto OpenSpec
- **THEN** la llamada se envía al endpoint `databricks-claude-sonnet-5-5`

#### Scenario: Roles obligatorios y asesor
- **WHEN** la configuración actual del producto se carga para una HU nueva
- **THEN** explorer, planner, developer y openspec_verifier usan Sonnet 5.5 y verifier conserva Haiku 4.5 asesor

#### Scenario: Modelo ajeno o configuración anterior
- **WHEN** la configuración del producto nuevo asigna otro endpoint a uno de los cuatro roles obligatorios
- **THEN** se rechaza explícitamente y no se degrada a un modelo distinto

#### Scenario: Mayor capacidad anunciada
- **WHEN** el endpoint anuncia hasta 128.000 tokens de salida
- **THEN** el producto conserva 64.000 para planner y los límites actuales de otros roles, registrando el límite efectivo por llamada

#### Scenario: Endpoint listo sin compatibilidad comprobada
- **WHEN** el endpoint aparece READY pero no se ha comprobado JSON Schema para esa instalación
- **THEN** no se declara soporte verificado y la activación conserva el contrato textual y sus validaciones o queda bloqueada si no cumple los requisitos de instalación

#### Scenario: Permiso o capacidad insuficiente
- **WHEN** la identidad de la App carece de CAN_QUERY o el endpoint no acepta el presupuesto requerido
- **THEN** la migración no se declara verificada ni admite HUs con la instalación incompleta

#### Scenario: Intento anterior a la migración
- **WHEN** se consulta un intento realizado con Sonnet 5
- **THEN** se conserva el modelo original de sus llamadas y no se atribuye a Sonnet 5.5 ejecución o aprobación histórica
