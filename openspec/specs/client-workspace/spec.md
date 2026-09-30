# client-workspace Specification

## Purpose

Garantizar que cada HU trabaje sobre un checkout completo y autorizado del repositorio cliente, con OpenSpec preparado una sola vez y borradores recuperables entre etapas.

## Requirements

### Requirement: Preparación única de OpenSpec por cliente
El harness SHALL ofrecer una preparación separada que inicialice OpenSpec en el repositorio cliente mediante una rama permitida y un PR; SHALL admitir HUs solamente cuando la rama base contenga una configuración OpenSpec válida. No SHALL volver a ejecutar `openspec init` para cada HU.

#### Scenario: Cliente pendiente de preparación
- **WHEN** la rama base del cliente carece de `openspec/config.yaml`
- **THEN** el harness informa que se requiere el PR de preparación y no inicia `explore`, `propose` ni desarrollo de una HU

#### Scenario: Cliente preparado
- **WHEN** el PR de preparación ya se integró y la rama base contiene OpenSpec válido
- **THEN** la HU usa esa configuración sin reinicializarla

### Requirement: Checkout aislado y fijado a la base
El harness SHALL obtener un checkout completo del repositorio y commit base autorizados por el perfil para cada intento; los cambios OpenSpec y de código SHALL realizarse en ese checkout. El contenido del repositorio no SHALL poder cambiar el repositorio, rama o commit elegidos por política.

#### Scenario: Inicio de intento
- **WHEN** se acepta una HU de un cliente preparado
- **THEN** el intento registra el SHA base y dispone de los archivos del repositorio cliente en un checkout aislado

#### Scenario: Checkout no disponible
- **WHEN** la obtención o verificación del checkout falla
- **THEN** el intento queda detenido sin invocar al desarrollador ni publicar una rama

### Requirement: Borrador exacto y recuperable
El harness SHALL guardar un punto de control íntegro de los archivos modificados, su base, versión y huellas en almacenamiento persistente antes de esperar una respuesta humana. SHALL restaurar y verificar ese punto de control al continuar tras un reinicio; las vistas redactadas y los logs no SHALL reemplazar al borrador canónico.

#### Scenario: Reinicio durante revisión
- **WHEN** la App se reinicia mientras una HU espera aprobación del plan o del diff
- **THEN** la misma versión de artefactos y código sigue disponible para revisión y continuación

#### Scenario: Punto de control alterado
- **WHEN** la huella del borrador restaurado no coincide con la registrada
- **THEN** el harness bloquea la continuación y la publicación
