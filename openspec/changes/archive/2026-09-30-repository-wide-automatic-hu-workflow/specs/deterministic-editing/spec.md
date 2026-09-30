# Spec Delta

## MODIFIED Requirements

### Requirement: Validación del resultado
El harness SHALL validar el resultado con controles de su estrategia y comparar el diff real con archivos y operaciones del manifiesto aprobado, además de la política. Las operaciones generales SHALL ser tipadas, de texto, limitadas y con hash previo para modificación o borrado; SHALL rechazarse conjuntos inválidos antes de aplicar archivos. El candidato SHALL quedar vinculado a la versión del plan y evidencia de verificación.

#### Scenario: Edición divergente
- **WHEN** la expresión o resultado silver_safe_ratio difiere de la razón validada
- **THEN** se detiene el flujo sin publicar

#### Scenario: Código general inválido
- **WHEN** el parche viola formato, sintaxis, estructura o límites
- **THEN** se bloquean verify y publicación hasta corregir

#### Scenario: Archivo adicional
- **WHEN** el parche admite una ruta por política pero no por el manifiesto aprobado
- **THEN** se solicita revisión del plan antes de editar esa ruta

#### Scenario: Hash previo divergente
- **WHEN** una modificación o eliminación no coincide con los bytes esperados
- **THEN** se rechaza el conjunto sin aplicar parcialmente operaciones
