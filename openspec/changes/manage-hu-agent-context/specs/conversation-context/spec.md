# Spec Delta

## Purpose

Gestionar el contexto de cada HU mediante recuperación, cache, memoria y compactación verificables, conservando decisiones, aislamiento y autorizaciones exactas durante todo el flujo.

## ADDED Requirements

### Requirement: Selección de contexto trazable
Antes de cada llamada el harness SHALL evaluar identidad y procedencia, hechos necesarios para rol/fase, validez de fuentes derivadas y presupuesto. SHALL decidir determinísticamente entre uso directo, memoria verificada, cache válida, recuperación, compactación o bloqueo; estas acciones pueden combinarse. SHALL conservar la razón de la elección y nunca consultar contenido fuera del perfil.

#### Scenario: Información suficiente
- **WHEN** el contexto obligatorio y la evidencia vigente caben en el presupuesto
- **THEN** se invoca el rol sin recuperación ni compactación innecesarias y se registra esa decisión

#### Scenario: Información faltante
- **WHEN** falta evidencia requerida para una conclusión
- **THEN** se recupera de fuentes autorizadas o se declara la carencia sin sustituirla por una inferencia del resumen

### Requirement: Cache derivada aislada e invalidable
La cache SHALL conservar únicamente contenido derivado autorizado, vinculado a cliente, repositorio, perfil, SHA base, revisión del checkout y hashes de fuentes. SHALL comprobar identidad, integridad y acceso vigente en cada hit, aplicar límites y retención, y permitir reconstrucción tras ausencia o corrupción. No SHALL usar como válidas lecturas del SHA base para archivos cambiados durante apply.

#### Scenario: Lectura repetida válida
- **WHEN** se solicita una fuente con identidad, hash y política idénticos
- **THEN** puede reutilizarse su contenido y se registra el hit sin atribuir ahorro de tokens no medido

#### Scenario: Archivo modificado en el candidato
- **WHEN** cambia un archivo leído aunque el SHA base permanezca igual
- **THEN** la entrada previa se invalida y verificación recibe la versión vigente

#### Scenario: Acceso revocado o cliente distinto
- **WHEN** la entrada pertenece a otro cliente o el perfil actual no permite leer su fuente
- **THEN** se rechaza su reutilización sin exponer contenido

### Requirement: Memoria confirmada por HU
La memoria SHALL conservar decisiones con identidad de HU/intento, revisión, origen, evidencia y estado vigente o sustituido. SHALL promover únicamente respuestas humanas autorizadas o hechos verificados en fuentes; una interpretación del modelo SHALL permanecer propuesta. SHALL conservar contradicciones sin resolver y no compartir automáticamente memoria entre HUs o clientes.

#### Scenario: Aclaración confirmada
- **WHEN** la persona autorizada indica que cero está permitido y la regla aplica a compras
- **THEN** todos los roles posteriores recuperan ambas decisiones con referencias a la aclaración original

#### Scenario: Decisiones contradictorias
- **WHEN** dos decisiones vigentes se contradicen sin una sustitución explícita
- **THEN** se bloquea el paso dependiente y se solicita aclaración mediante el flujo existente

### Requirement: Compactación condicional y conservadora
La compactación SHALL evaluarse ante el umbral configurado o redundancia medible y actuar solo sobre historial y resultados derivados. SHALL preservar decisiones vigentes, preguntas, restricciones y referencias comprobables a evidencia. Las skills e instrucciones obligatorias no SHALL truncarse. Aprobaciones, identidades, hashes y manifiestos SHALL recuperarse de registros originales y nunca inferirse del resumen. El registro original SHALL conservarse según retención y ACL.

#### Scenario: Historial extenso
- **WHEN** el contexto excede el umbral de compactación
- **THEN** se valida un resumen estructurado contra las fuentes y se usa solo si conserva información requerida y reduce el tamaño

#### Scenario: Aprobación alterada en resumen
- **WHEN** un resumen omite o modifica una referencia de aprobación necesaria
- **THEN** se rechaza el resumen y la autorización se comprueba desde los registros originales

#### Scenario: Mínimo obligatorio excedido
- **WHEN** las instrucciones y hechos obligatorios no caben aun tras retirar derivaciones prescindibles
- **THEN** la llamada se bloquea con diagnóstico sin truncamiento silencioso ni aumento automático del presupuesto

### Requirement: Recuperación y compatibilidad
El harness SHALL persistir memoria y compactaciones aceptadas de forma íntegra y vinculada al checkpoint/revisión. SHALL reconstruir contexto tras reinicio desde registros originales y derivaciones validadas; cache corrupta SHALL poder descartarse. Los históricos SHALL seguir consultables sin memoria o compactaciones ficticias. La versión de política y prompts SHALL permanecer fijada por intento.

#### Scenario: Reinicio esperando aprobación
- **WHEN** se restaura una HU con preguntas y un plan pendiente
- **THEN** se conservan esas preguntas y la espera original sin convertirla en aprobación

#### Scenario: Derivación alterada
- **WHEN** la memoria o compactación persistida no supera la validación de integridad
- **THEN** se reconstruye desde fuentes originales o se bloquea el avance si no es posible, sin perder la consulta autorizada
