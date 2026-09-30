# GitHub Publication Specification

## Purpose

Controlar la publicación revisable de cambios en el repositorio configurado para un cliente.

## Requirements

### Requirement: Rama y Pull Request acotados
El harness SHALL publicar únicamente un candidato verificado y autorizado por la aprobación vigente del plan en una rama feature/* del repositorio configurado hacia su base. SHALL crear el PR automáticamente después de sync y archive, sin merge ni despliegue automático.

#### Scenario: Publicación aprobada
- **WHEN** pasan controles, existe diff nuevo y autorización vigente del plan
- **THEN** se crea o reutiliza rama permitida y se registra URL automáticamente

#### Scenario: Ausencia de cambio
- **WHEN** el candidato no difiere de la base
- **THEN** no se crea un PR nuevo

#### Scenario: Publicación sin aprobación
- **WHEN** no existe aprobación humana vigente del plan y autorización correspondiente
- **THEN** no se crea ni actualiza rama o PR

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
El harness SHALL incluir en el mismo Pull Request el código y los artefactos OpenSpec de la HU validados, sincronizados y archivados dentro del repositorio cliente. La inicialización de OpenSpec SHALL pertenecer al PR separado de preparación del cliente. La revisión humana seguirá siendo necesaria para integrar el PR.

#### Scenario: Publicación conjunta
- **WHEN** una HU de un cliente preparado supera todos los controles
- **THEN** el PR contiene el código y los specs e historial OpenSpec aprobados, sin volver a inicializar OpenSpec

#### Scenario: Cliente ya inicializado
- **WHEN** la rama base del cliente contiene OpenSpec y el candidato aprobado supera todos los controles
- **THEN** el PR conserva el contexto existente e incluye el cambio OpenSpec nuevo y el código aprobado

#### Scenario: Rama reutilizada con documentos divergentes
- **WHEN** una rama existente contiene artefactos OpenSpec distintos a los aprobados o archivos adicionales
- **THEN** el harness rechaza la reutilización de esa rama

#### Scenario: Cliente no inicializado
- **WHEN** la rama base aún carece de la preparación OpenSpec
- **THEN** no se publica un PR de HU que mezcle configuración inicial y cambio de código

### Requirement: Identidad del candidato publicado
El harness SHALL completar sync y archive y conservar un candidato exacto ligado al SHA base, revisión, plan aprobado, política y evidencia. SHALL comparar bytes y hashes al publicar y el diff remoto completo al reutilizar rama o PR. Si cambia la base SHALL reiniciar planificación y exigir aprobación vigente sobre la nueva base. Si cambia el candidato SHALL detener publicación y revalidarlo.

#### Scenario: Base avanzada durante revisión
- **WHEN** la base remota cambió después de fijar checkout
- **THEN** no publica el candidato antiguo y requiere planificación y aprobación sobre nueva base

#### Scenario: Candidato sin cambios posteriores
- **WHEN** base y hashes coinciden con el candidato verificado y autorizado
- **THEN** publica exactamente ese candidato sin aprobación humana adicional del diff
