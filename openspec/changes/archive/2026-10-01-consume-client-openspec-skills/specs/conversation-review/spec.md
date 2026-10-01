## ADDED Requirements

### Requirement: Continuidad de la conversación al importar skills
El harness SHALL conservar estados, acciones y contratos públicos de la conversación de HU al consumir skills. SHALL mostrar resumen y preguntas necesarias, propuesta revisable y aprobación vigente del plan; SHALL continuar automáticamente hasta el PR tras verificar, sincronizar y archivar para intentos de publicación por plan aprobado. Las instrucciones internas no SHALL introducir aprobaciones adicionales, comandos o JSON en el hilo principal. Los históricos SHALL conservar su modalidad y seguir consultables sin inventar evidencia. El texto generado puede variar sin alterar el recorrido.

#### Scenario: HU clara
- **WHEN** explore no identifica preguntas necesarias
- **THEN** continúa a propuesta sin agregar una confirmación para cargar skills

#### Scenario: Aclaración y revisión
- **WHEN** la persona responde preguntas o solicita cambios al plan
- **THEN** se conservan mensajes y borradores, se usan las mismas acciones y una revisión nueva invalida la aprobación anterior

#### Scenario: Plan aprobado
- **WHEN** el candidato corresponde al plan aprobado y supera controles vigentes
- **THEN** se crea el PR automáticamente sin pedir aprobación humana adicional del diff

#### Scenario: Preparación incompleta
- **WHEN** faltan configuración o skills compatibles en la base
- **THEN** se muestra un error comprensible que identifica la preparación manual pendiente, sin abrir un onboarding dentro del chat

#### Scenario: Histórico
- **WHEN** se consulta una ejecución anterior al consumo de skills
- **THEN** permanece legible con su modalidad y evidencia original sin atribuirle instrucciones nuevas
