# Spec Delta

## ADDED Requirements

### Requirement: Inicialización y artefactos OpenSpec en el PR

El harness SHALL incluir la inicialización y los artefactos OpenSpec validados entre los archivos del mismo Pull Request que contiene el cambio de código. La revisión humana seguirá siendo necesaria para integrar el PR.

#### Scenario: Publicación conjunta
- **WHEN** todos los controles pasan y el repositorio cliente no tenía OpenSpec
- **THEN** el PR contiene la configuración inicial, el cambio OpenSpec validado y el código cambiado

#### Scenario: Cliente ya inicializado
- **WHEN** el repositorio cliente ya tenía OpenSpec y todos los controles pasan
- **THEN** el PR conserva el contexto existente e incluye el nuevo cambio y el código

#### Scenario: Rama reutilizada con documentos divergentes
- **WHEN** una rama existente contiene artefactos OpenSpec distintos a los validados o archivos adicionales
- **THEN** el harness rechaza la reutilización de esa rama
