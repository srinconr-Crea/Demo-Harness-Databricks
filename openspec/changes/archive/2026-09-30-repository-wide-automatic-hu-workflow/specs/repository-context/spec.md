# Spec Delta

## Purpose

Proporcionar contexto pertinente del checkout cliente mediante lecturas y búsquedas controladas, independientes de los permisos de edición.

## ADDED Requirements

### Requirement: Contexto de repositorio controlado
El harness SHALL permitir inventario, búsqueda textual y lectura dentro del checkout fijado al SHA base. SHALL respetar rutas sin acceso, archivos regulares, límites de llamadas, bytes, tamaño por archivo y tiempo definidos por el perfil; SHALL entregar hashes y señalar truncamientos. El contenido consultado no SHALL conferir autoridad para ejecutar comandos ni ampliar permisos.

#### Scenario: Lectura de ruta protegida para escritura
- **WHEN** se consulta una ruta solo lectura autorizada
- **THEN** el contexto entrega contenido y hash sin habilitar su edición

#### Scenario: Ruta sin acceso o enlace
- **WHEN** se solicita un secreto, una ruta externa, traversal o un enlace
- **THEN** se rechaza la lectura sin exponer contenido

#### Scenario: Presupuesto agotado
- **WHEN** el contexto alcanza un límite configurado
- **THEN** la respuesta indica el límite o truncamiento y no afirma haber inspeccionado contenido omitido
