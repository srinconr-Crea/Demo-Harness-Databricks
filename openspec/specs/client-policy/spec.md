# Client Policy Specification

## Purpose

Delimitar por perfil de cliente los recursos y cambios que el harness puede procesar.

## Requirements

### Requirement: Perfil separado por cliente

El harness SHALL obtener el repositorio, la rama base, las rutas editables y la estrategia de un perfil YAML seleccionado para la ejecución.

#### Scenario: Perfil configurado
- **WHEN** se inicia una ejecución con un perfil válido
- **THEN** el flujo usa únicamente el repositorio, la rama y las rutas de ese perfil

### Requirement: Restricción de rutas

El harness SHALL rechazar una ruta fuera de los prefijos permitidos, absoluta, con ascenso de directorio, con separadores no admitidos o dentro de `.github/`.

#### Scenario: Ruta fuera de política
- **WHEN** la estrategia apunta a un archivo que el perfil no permite
- **THEN** la ejecución falla antes de editar o publicar

### Requirement: Entradas sin autoridad de política

El harness SHALL tratar la historia, el contenido del repositorio y las salidas del modelo como datos sin autoridad para ampliar perfiles, rutas, estrategias o modelos.

#### Scenario: Solicitud de ruta adicional en una historia
- **WHEN** una historia pide editar una ruta no autorizada por el perfil
- **THEN** el harness mantiene la restricción del perfil y no publica el cambio

### Requirement: Espacio OpenSpec autorizado por perfil

El harness SHALL exigir que cada perfil declare un prefijo OpenSpec confiable para inicializar y publicar artefactos en el repositorio cliente. SHALL aplicar a esas rutas el mismo rechazo de rutas absolutas, traversal y archivos fuera de política.

#### Scenario: Perfil configurado
- **WHEN** el perfil declara su prefijo OpenSpec y el cambio supera los controles
- **THEN** solo los archivos bajo ese prefijo pueden incorporarse al Pull Request

#### Scenario: Perfil sin prefijo OpenSpec
- **WHEN** el perfil no declara un prefijo OpenSpec válido
- **THEN** el harness no inicia desarrollo ni publicación para esa historia
