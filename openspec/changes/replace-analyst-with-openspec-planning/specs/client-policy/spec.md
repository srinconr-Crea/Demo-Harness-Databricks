# Spec Delta

## ADDED Requirements

### Requirement: Espacio OpenSpec autorizado por perfil

El harness SHALL exigir que cada perfil declare un prefijo OpenSpec confiable para inicializar y publicar artefactos en el repositorio cliente. SHALL aplicar a esas rutas el mismo rechazo de rutas absolutas, traversal y archivos fuera de política.

#### Scenario: Perfil configurado
- **WHEN** el perfil declara su prefijo OpenSpec y el cambio supera los controles
- **THEN** solo los archivos bajo ese prefijo pueden incorporarse al Pull Request

#### Scenario: Perfil sin prefijo OpenSpec
- **WHEN** el perfil no declara un prefijo OpenSpec válido
- **THEN** el harness no inicia desarrollo ni publicación para esa historia
