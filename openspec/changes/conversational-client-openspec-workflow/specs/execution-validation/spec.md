# Spec Delta

## MODIFIED Requirements

### Requirement: Secuencia de controles
El harness SHALL exigir checkout autorizado, OpenSpec preexistente, plan validado y aprobado por una persona, desarrollo bajo una estrategia registrada, pruebas pertinentes, verificación contra los specs y aprobación humana del diff final antes de publicar. El desarrollador y el verificador SHALL recibir artefactos de la misma versión aprobada del plan; `apply` SHALL invocar al desarrollador para ejecutar tareas aprobadas.

#### Scenario: Todos los controles aprobados
- **WHEN** cada control y las dos revisiones humanas producen resultados vigentes y aprobatorios
- **THEN** el flujo puede iniciar la publicación

#### Scenario: Control rechazado
- **WHEN** cualquier control falla o entrega una salida inválida
- **THEN** el flujo queda pendiente de corrección o falla sin iniciar la publicación

#### Scenario: Planificación rechazada
- **WHEN** el cambio OpenSpec no valida, contradice la política o no tiene aprobación humana vigente
- **THEN** el desarrollador no se invoca y no se publica código cliente

#### Scenario: Inicialización rechazada
- **WHEN** la rama base carece de una preparación OpenSpec válida
- **THEN** el desarrollador no se invoca y no se publica código cliente

#### Scenario: Verificación contra la especificación
- **WHEN** el código editado supera los controles de su estrategia
- **THEN** `verify` compara el diff y la evidencia de pruebas con los specs validados antes de habilitar la revisión final

## ADDED Requirements

### Requirement: Verificación específica y ciclo de corrección
Cada tipo de cambio SHALL disponer de comprobaciones deterministas pertinentes y una revisión del verificador. Un descuadre SHALL mostrarse en la conversación y permitir `update`/`apply`/`verify` sobre una versión nueva, sin aprobar automáticamente resultados inconclusos ni ejecutar comandos arbitrarios solicitados por la HU.

#### Scenario: Descuadre corregible
- **WHEN** `verify` encuentra una diferencia entre el código, los specs y las pruebas
- **THEN** el intento conserva el hallazgo, bloquea la revisión final y permite una corrección trazable

#### Scenario: Prueba no disponible
- **WHEN** una comprobación obligatoria no puede ejecutarse
- **THEN** el resultado se informa como no verificado y no se trata como aprobado
