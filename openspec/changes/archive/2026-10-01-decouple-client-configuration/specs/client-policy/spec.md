# Spec Delta

## ADDED Requirements

### Requirement: Perfil externo activado por el operador
El harness SHALL cargar el perfil externo exclusivamente desde la ruta configurada por el operador, verificar sus bytes contra `HARNESS_CLIENT_PROFILE_SHA256` y validar el contrato YAML antes de aceptar HUs. SHALL rechazar archivo ausente, ilegible, enlace, YAML inválido, tamaño mayor de 128 KiB o hash faltante, inválido o divergente. La copia activada SHALL permanecer fuera del checkout editable y del paquete sandbox. No SHALL copiar claves privadas o tokens al perfil, prompts o diagnósticos.

#### Scenario: Perfil externo íntegro
- **WHEN** el archivo regular configurado cumple tamaño, contrato y hash esperado
- **THEN** el proceso activa ese único perfil sin depender de perfiles cliente incluidos en el código del producto

#### Scenario: Perfil alterado o inválido
- **WHEN** falla cualquiera de las comprobaciones del perfil externo
- **THEN** el proceso no acepta HUs y emite un diagnóstico sin el contenido del archivo ni secretos

### Requirement: Selección compatible y sin fallback implícito
El harness SHALL aceptar temporalmente la selección por nombre `HARNESS_CLIENT_PROFILE` solo cuando no esté configurado el modo externo. SHALL conservar la validación del nombre y contrato del modo legado y registrar su procedencia. SHALL rechazar configuración simultánea de ambos modos, ausencia de selección y hash externo sin ruta. Un error en el modo externo no SHALL activar el modo legado ni un perfil predeterminado.

#### Scenario: Instalación legada explícita
- **WHEN** solo se configura el selector legado y su YAML existe en el directorio de perfiles de esa instalación
- **THEN** se carga ese perfil y se registra el modo legado sin ampliar autorizaciones

#### Scenario: Selección ambigua
- **WHEN** están configurados ambos selectores o el hash externo sin su ruta
- **THEN** la App rechaza el arranque y explica la configuración incompatible

### Requirement: Configuración cliente protegida en el repositorio
El harness SHALL tratar `.harness/` como solo lectura para el desarrollador independientemente del alcance y extensiones del perfil. SHALL rechazar su creación, modificación o eliminación en edición, validación del candidato y publicación. Un perfil versionado allí SHALL aportar contexto sin sustituir la copia activada por el operador.

#### Scenario: Intento de ampliar permisos
- **WHEN** una HU modifica `.harness/client.yaml` para habilitar otras rutas o pruebas
- **THEN** el harness rechaza la operación y conserva la política activada

#### Scenario: Archivo protegido añadido al candidato
- **WHEN** un candidato contiene una creación, modificación o eliminación bajo `.harness/` por cualquier vía
- **THEN** su validación o publicación queda bloqueada aunque el manifiesto lo incluya
