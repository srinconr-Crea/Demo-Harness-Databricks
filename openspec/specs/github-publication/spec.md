# GitHub Publication Specification

## Purpose

Controlar la publicación revisable de cambios en el repositorio configurado para un cliente.

## Requirements

### Requirement: Rama y Pull Request acotados

El harness SHALL publicar cambios aprobados en una rama `feature/*` del repositorio del perfil y abrir un Pull Request hacia la rama base configurada, sin hacer merge ni despliegue automático.

#### Scenario: Publicación aprobada
- **WHEN** todos los controles pasan y el cambio produce un diff nuevo
- **THEN** se crea o actualiza la rama permitida y se registra la URL del Pull Request

#### Scenario: Ausencia de cambio
- **WHEN** el archivo editado no difiere de la base
- **THEN** el harness no crea un Pull Request nuevo

### Requirement: Archivos publicados verificados

El harness SHALL comprobar que los archivos de una rama o Pull Request reutilizados coinciden con el conjunto completo de archivos validados para el intento.

#### Scenario: Archivos adicionales en una rama existente
- **WHEN** una rama reutilizable incluye un archivo no validado
- **THEN** el harness rechaza la publicación

### Requirement: Estado de checks honesto

El harness SHALL reportar los checks del Pull Request como `passed`, `pending`, `failed` o `unavailable` según la evidencia disponible.

#### Scenario: Checks no consultables
- **WHEN** los permisos o la API no permiten consultar checks
- **THEN** el estado se informa como `unavailable`, sin presentarlo como aprobado

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
