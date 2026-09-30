# Spec Delta

## MODIFIED Requirements

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

### Requirement: Identidad del candidato publicado
El harness SHALL completar sync y archive y conservar un candidato exacto ligado al SHA base, revisión, plan aprobado, política y evidencia. SHALL comparar bytes y hashes al publicar y el diff remoto completo al reutilizar rama o PR. Si cambia la base SHALL reiniciar planificación y exigir aprobación vigente sobre la nueva base. Si cambia el candidato SHALL detener publicación y revalidarlo.

#### Scenario: Base avanzada durante revisión
- **WHEN** la base remota cambió después de fijar checkout
- **THEN** no publica el candidato antiguo y requiere planificación y aprobación sobre nueva base

#### Scenario: Candidato sin cambios posteriores
- **WHEN** base y hashes coinciden con el candidato verificado y autorizado
- **THEN** publica exactamente ese candidato sin aprobación humana adicional del diff

