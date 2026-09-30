# Spec Delta

## MODIFIED Requirements

### Requirement: Restricción de rutas
El harness SHALL admitir alcance por prefijos o repositorio, según perfil confiable, y distinguir rutas editables, solo lectura y sin acceso. SHALL rechazar rutas absolutas, traversal, separadores inválidos, enlaces y rutas externas. `.github/`, el prefijo OpenSpec y los archivos de instrucciones declarados SHALL ser solo lectura para el desarrollador; `.git/` y secretos SHALL quedar sin acceso del modelo. Las prohibiciones prevalecen sobre permisos y extensiones. SHALL comprobar edición, estado final y publicación; solo el flujo OpenSpec puede escribir su prefijo.

#### Scenario: Ruta fuera de política
- **WHEN** el desarrollador propone o produce un archivo fuera de política
- **THEN** se bloquea su edición o publicación

#### Scenario: Archivo raíz autorizado
- **WHEN** un perfil de alcance repositorio admite un archivo raíz y su extensión
- **THEN** se permite la operación si satisface los demás controles

#### Scenario: Ruta solo lectura
- **WHEN** el desarrollador intenta crear, modificar o borrar una ruta solo lectura
- **THEN** se rechaza la operación aunque su extensión esté admitida

## ADDED Requirements

### Requirement: Extensiones y operaciones explícitas
Cada perfil general SHALL declarar operaciones, extensiones, límites de archivos y bytes, adaptadores y objetivos de pruebas. La lista soportada SHALL incluir `.py`, `.sql`, `.ipynb`, `.yml`, `.yaml`, `.json`, `.toml`, `.md`, `.txt`; cada cliente habilita únicamente tipos con validación pertinente. Los perfiles existentes por prefijos y silver_safe_ratio SHALL conservar su alcance sin ampliación implícita.

#### Scenario: Extensión no autorizada
- **WHEN** se propone un archivo de extensión no habilitada
- **THEN** el harness rechaza el parche

#### Scenario: Perfil piloto existente
- **WHEN** se carga un perfil silver_safe_ratio sin política de repositorio
- **THEN** continúa su editor y prueba SQL acotados
