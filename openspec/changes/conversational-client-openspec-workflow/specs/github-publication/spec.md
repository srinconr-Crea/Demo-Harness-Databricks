# Spec Delta

## MODIFIED Requirements

### Requirement: Rama y Pull Request acotados
El harness SHALL publicar únicamente el candidato validado y aprobado en la App en una rama `feature/*` del repositorio del perfil, y abrir un Pull Request hacia la rama base configurada, sin hacer merge ni despliegue automático.

#### Scenario: Publicación aprobada
- **WHEN** todos los controles pasan, existe un diff nuevo y la persona aprueba la versión exacta del candidato
- **THEN** se crea o actualiza la rama permitida y se registra la URL del Pull Request

#### Scenario: Ausencia de cambio
- **WHEN** el candidato no difiere de la base
- **THEN** el harness no crea un Pull Request nuevo

#### Scenario: Publicación sin aprobación
- **WHEN** no existe aprobación humana vigente del diff final
- **THEN** el harness no crea ni actualiza rama o Pull Request

### Requirement: Inicialización y artefactos OpenSpec en el PR
El harness SHALL incluir en el mismo Pull Request el código y los artefactos OpenSpec de la HU validados, sincronizados y archivados dentro del repositorio cliente. La inicialización de OpenSpec SHALL pertenecer al PR separado de preparación del cliente. La revisión humana seguirá siendo necesaria para integrar el PR.

#### Scenario: Publicación conjunta
- **WHEN** una HU de un cliente preparado supera todos los controles
- **THEN** el PR contiene el código y los specs e historial OpenSpec aprobados, sin volver a inicializar OpenSpec

#### Scenario: Cliente ya inicializado
- **WHEN** la rama base del cliente contiene OpenSpec y el candidato aprobado supera todos los controles
- **THEN** el PR conserva el contexto existente e incluye el cambio OpenSpec nuevo y el código aprobado

#### Scenario: Cliente no inicializado
- **WHEN** la rama base aún carece de la preparación OpenSpec
- **THEN** no se publica un PR de HU que mezcle configuración inicial y cambio de código

#### Scenario: Rama reutilizada con documentos divergentes
- **WHEN** una rama existente contiene artefactos OpenSpec distintos a los aprobados o archivos adicionales
- **THEN** el harness rechaza la reutilización de esa rama

## ADDED Requirements

### Requirement: Identidad del candidato publicado
El harness SHALL preparar `sync` y `archive` antes de presentar el diff final, y SHALL comparar el conjunto completo de archivos y sus hashes aprobados con el candidato que se va a publicar. Si la base remota cambió o el candidato difiere, SHALL detener la publicación y requerir nueva validación y aprobación.

#### Scenario: Base avanzada durante revisión
- **WHEN** la rama base cambia después de fijar el checkout
- **THEN** el harness no publica el candidato antiguo y solicita actualizarlo y revisarlo de nuevo

#### Scenario: Candidato sin cambios posteriores
- **WHEN** los hashes de todos los archivos y la base coinciden con la aprobación
- **THEN** el harness puede publicar exactamente ese candidato
