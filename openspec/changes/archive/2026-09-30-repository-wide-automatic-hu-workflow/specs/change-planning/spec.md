# Spec Delta

## ADDED Requirements

### Requirement: Propuesta comprensible y manifiesto aprobado
La propuesta SHALL mostrar objetivo, comportamiento esperado, archivos y operaciones previstos, pruebas requeridas y que su aprobación autoriza crear automáticamente el PR. SHALL distinguir cambios previstos del diff real posterior. El manifiesto SHALL limitar el desarrollo dentro de la política; los comentarios generan nueva revisión y aprobación. Ninguna descripción narrativa SHALL ampliar permisos ni sustituir pruebas del perfil.

#### Scenario: Aprobación informada
- **WHEN** la persona revisa una propuesta válida
- **THEN** ve alcance, pruebas y autorización de publicación antes de aprobar su hash

#### Scenario: Cambio de propuesta
- **WHEN** la persona solicita ajustes
- **THEN** se actualizan artefactos y manifiesto, invalidando aprobación anterior

#### Scenario: Código mostrado antes de apply
- **WHEN** la propuesta incluye ejemplos o cambios de código previstos
- **THEN** se identifican como previstos sin afirmar que son el diff ejecutado
