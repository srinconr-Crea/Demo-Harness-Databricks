# Spec Delta

## Purpose

Definir la planificación OpenSpec que convierte cada historia autorizada en artefactos verificables antes de editar código cliente.

## ADDED Requirements

### Requirement: Cambio de planificación por intento

El harness SHALL generar un cambio OpenSpec separado por intento, con propuesta, especificaciones delta, diseño y tareas, a partir de la historia y del contexto autorizado del perfil.

#### Scenario: Historia admitida
- **WHEN** una historia supera el análisis determinista de su estrategia
- **THEN** el planner produce los cuatro tipos de artefacto para ese intento

#### Scenario: Reintento
- **WHEN** una historia fallida se reintenta
- **THEN** el nuevo cambio tiene identidad propia y conserva trazabilidad hacia el intento anterior

### Requirement: Validación previa a la edición

El harness SHALL exigir validación estructural estricta de OpenSpec y comprobación determinista de que los artefactos no exceden la estrategia, los archivos ni los modelos autorizados por el perfil.

#### Scenario: Artefactos válidos y acotados
- **WHEN** OpenSpec valida los artefactos y la política los admite
- **THEN** el harness habilita la fase de desarrollo

#### Scenario: Documento que solicita un archivo adicional
- **WHEN** un artefacto generado pide editar o publicar una ruta no autorizada
- **THEN** el harness rechaza el cambio antes de invocar al desarrollador

#### Scenario: Validación estructural fallida
- **WHEN** falta un artefacto requerido o OpenSpec reporta un error
- **THEN** el intento falla sin editar ni publicar archivos cliente

### Requirement: Artefactos disponibles para revisión

El harness SHALL conservar los artefactos validados y exponer su identidad y resultado de validación junto con el intento para revisión humana.

#### Scenario: Intento planificado
- **WHEN** el planner termina correctamente
- **THEN** el registro del intento permite recuperar los artefactos y sus hashes
