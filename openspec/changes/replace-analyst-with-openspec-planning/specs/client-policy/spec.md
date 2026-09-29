# Spec Delta

## ADDED Requirements

### Requirement: Publicación OpenSpec autorizada por perfil

El harness SHALL publicar artefactos OpenSpec en un repositorio cliente solo cuando el perfil habilite explícitamente las rutas de destino y SHALL aplicar a esas rutas el mismo rechazo de rutas absolutas, traversal y archivos fuera de política.

#### Scenario: Perfil habilitado
- **WHEN** el perfil admite rutas OpenSpec concretas y el cambio supera los controles
- **THEN** esas rutas pueden incorporarse al conjunto de archivos validados para el Pull Request

#### Scenario: Perfil sin habilitación
- **WHEN** el perfil no habilita rutas OpenSpec
- **THEN** la historia no amplía por sí misma la lista de archivos publicables y los artefactos quedan en el registro del harness
