# Spec Delta

## ADDED Requirements

### Requirement: Artefactos OpenSpec en publicación habilitada

Cuando el perfil lo autorice, el harness SHALL incluir los artefactos OpenSpec validados entre los archivos del mismo Pull Request que contiene el cambio de código. La revisión humana seguirá siendo necesaria para integrar el PR.

#### Scenario: Publicación conjunta
- **WHEN** el perfil permite las rutas de artefactos y todos los controles pasan
- **THEN** el PR contiene el código cambiado y los documentos OpenSpec aprobados

#### Scenario: Publicación no habilitada
- **WHEN** el perfil no permite rutas OpenSpec
- **THEN** el harness no escribe esos archivos en el repositorio cliente

#### Scenario: Rama reutilizada con documentos divergentes
- **WHEN** una rama existente contiene artefactos OpenSpec distintos a los validados o archivos adicionales
- **THEN** el harness rechaza la reutilización de esa rama
