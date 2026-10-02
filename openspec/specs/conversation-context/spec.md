# conversation-context Specification

## Purpose

Gestionar contexto por HU con selección y reducción deterministas, cache y decisiones verificables, preservando fuentes vigentes, aislamiento y autorizaciones exactas.

## Requirements

### Requirement: Selección de contexto trazable por rol
Antes de cada llamada y tras cada solicitud de contexto el harness SHALL evaluar identidad, procedencia, mínimos por rol/fase, decisiones aplicables, vigencia de fuentes y presupuesto. SHALL registrar razones de inclusión/exclusión y recuperar evidencia faltante autorizada o declarar su ausencia. SHALL priorizar aplicabilidad y vigencia comprobable sobre recencia de fecha; ninguna nota reciente SHALL sustituir por sí sola una regla vigente.

#### Scenario: Contexto suficiente
- **WHEN** mínimos y evidencia vigente caben en el presupuesto
- **THEN** se invoca el rol sin recuperación innecesaria y se registra selección reproducible

#### Scenario: Nota reciente incompatible
- **WHEN** una nota reciente contradice una regla vigente sin sustitución autorizada clara
- **THEN** se conserva la discrepancia y se solicita aclaración antes del paso dependiente, sin elegir solo por fecha

#### Scenario: Evidencia faltante
- **WHEN** falta una fuente requerida para el rol
- **THEN** se recupera bajo política o se declara la carencia sin inferirla desde una referencia o derivación

### Requirement: Cache aislada e invalidable
La cache SHALL conservar solo derivaciones autorizadas vinculadas a cliente/repo/perfil, base, revisión del candidato y hashes de fuentes/inventario. SHALL revalidar identidad, integridad y acceso por hit y aplicar límites/TTL. No SHALL considerar completas respuestas truncadas ni reutilizar como vigente una lectura anterior de archivo modificado.

#### Scenario: Lectura repetida
- **WHEN** identidad, contenido y permisos coinciden
- **THEN** se reutiliza la lectura con hit registrado sin atribuir ahorro de tokens no medido

#### Scenario: Candidato o inventario cambiado
- **WHEN** cambia un archivo durante apply o se crea/elimina una ruta del alcance de búsqueda
- **THEN** se invalida el resultado anterior y se recupera evidencia vigente

#### Scenario: Otro cliente o acceso revocado
- **WHEN** la entrada pertenece a otro cliente o ya no está autorizada
- **THEN** se rechaza sin exponer contenido

### Requirement: Memoria verificable con ciclo de vigencia
La memoria SHALL conservar identidad HU/intento, revisión, origen/hash, actor aplicable, estado y sustitución de decisiones. SHALL confirmar solo aclaraciones humanas autorizadas inequívocas o hechos verificados; interpretaciones del modelo SHALL permanecer propuestas. Decisiones humanas no SHALL caducar solo por tiempo. Hechos cuya fuente cambió SHALL revalidarse antes de uso. SHALL separar vigencia funcional, TTL de cache y retención de originales, sin memoria automática entre HUs/clientes.

#### Scenario: Aclaración aplicable
- **WHEN** una respuesta autorizada confirma cero permitido en compras y negativos rechazados
- **THEN** los roles pertinentes reciben ambas decisiones con referencias originales comprobables

#### Scenario: Sustitución inequívoca
- **WHEN** una corrección autorizada indica inequívocamente que cero ahora se rechaza
- **THEN** la nueva decisión sustituye la anterior conservando ambas y sus orígenes

#### Scenario: Conflicto o extracción ambigua
- **WHEN** decisiones aplicables se contradicen sin sustitución clara o una extracción no permite preservar significado
- **THEN** se conserva texto original íntegro y se solicita aclaración si afecta el paso dependiente, sin confirmar inferencias

#### Scenario: Hecho obsoleto y decisión antigua
- **WHEN** cambia el hash de un hecho recuperado mientras una decisión humana permanece sin sustitución
- **THEN** el hecho se revalida y la decisión humana no expira por su antigüedad

### Requirement: Reducción determinista conservadora
El harness SHALL reducir únicamente derivaciones duplicadas exactas, obsoletas o demostrablemente no pertinentes y ensamblar decisiones/preguntas desde originales con referencias verificadas. SHALL conservar evidencia requerida suficiente y validar cobertura de IDs/refs/hashes. No SHALL resumir semánticamente mediante LLM, invocar compactor, truncar skills/instrucciones obligatorias ni reconstruir aprobaciones desde vistas reducidas. SHALL medir entrada completa incluido system y reservar salida; si mínimo excede presupuesto SHALL bloquear con diagnóstico sin ampliación automática.

#### Scenario: Resultado repetido
- **WHEN** dos rondas contienen la misma evidencia vigente
- **THEN** se conserva una copia íntegra requerida y se registra exclusión del duplicado sin pérdida de decisiones

#### Scenario: Decisión omitida o referencia fabricada
- **WHEN** la vista propuesta pierde un ID requerido o contiene referencia/hash no verificable
- **THEN** se rechaza y se reconstruye desde originales o se bloquea sin usarla como autoridad

#### Scenario: Mínimo demasiado grande
- **WHEN** system, instrucciones, decisiones/evidencia obligatorias y reserva no caben después de reducción
- **THEN** se bloquea conservando consulta/cancelación, sin compactor ni truncamiento silencioso

### Requirement: Recuperación y compatibilidad
El harness SHALL persistir decisiones y vistas aceptadas protegidas por hash y vinculadas al checkpoint/revisión. SHALL reconstruir desde originales tras reinicio; cache SHALL ser descartable. Históricos SHALL seguir consultables sin metadatos ficticios y política/prompts SHALL permanecer fijados por intento. Retry SHALL revalidar decisiones permitidas sin heredar autorizaciones.

#### Scenario: Reinicio en espera
- **WHEN** se restaura HU esperando aclaración o revisión de plan
- **THEN** se conservan preguntas, decisiones y espera sin transformarlas en aprobación

#### Scenario: Derivación alterada
- **WHEN** memoria o vista persistida falla integridad
- **THEN** se reconstruye desde originales o se bloquea sin perder consulta autorizada

#### Scenario: Retry bajo política actual
- **WHEN** una persona solicita nuevo intento del mismo run
- **THEN** hechos se revalidan y aprobación previa no se hereda
