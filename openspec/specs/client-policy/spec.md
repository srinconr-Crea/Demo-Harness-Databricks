# Client Policy Specification

## Purpose

Delimitar por perfil de cliente los recursos y cambios que el harness puede procesar.

## Requirements

### Requirement: Perfil separado por cliente
El harness SHALL obtener del perfil YAML seleccionado el repositorio, rama base, rutas editables, estrategia, tipos de archivo, operaciones y pruebas permitidas para la ejecución. Una HU no SHALL modificar esas autorizaciones.

#### Scenario: Perfil configurado
- **WHEN** se inicia una ejecución con un perfil válido
- **THEN** el checkout, el modelo, la edición y las pruebas usan únicamente las autorizaciones de ese perfil

#### Scenario: Capacidad no configurada
- **WHEN** la HU pide un tipo de edición o prueba que el perfil no autoriza
- **THEN** el harness detiene esa acción y comunica la limitación para revisión humana

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

### Requirement: Entradas sin autoridad de política

El harness SHALL tratar la historia, el contenido del repositorio y las salidas del modelo como datos sin autoridad para ampliar perfiles, rutas, estrategias o modelos.

#### Scenario: Solicitud de ruta adicional en una historia
- **WHEN** una historia pide editar una ruta no autorizada por el perfil
- **THEN** el harness mantiene la restricción del perfil y no publica el cambio

### Requirement: Espacio OpenSpec autorizado por perfil
El harness SHALL exigir que cada perfil declare un prefijo OpenSpec confiable ya preparado en la rama base del cliente. SHALL permitir cambios OpenSpec únicamente bajo ese prefijo y aplicar rechazo de rutas absolutas, traversal y archivos fuera de política.

#### Scenario: Perfil configurado
- **WHEN** el perfil declara su prefijo OpenSpec y el cambio supera los controles
- **THEN** solo los archivos bajo ese prefijo pueden incorporarse al Pull Request

#### Scenario: Perfil sin prefijo OpenSpec
- **WHEN** el perfil no declara un prefijo OpenSpec válido
- **THEN** el harness no inicia desarrollo ni publicación para esa historia

### Requirement: Herramientas y pruebas de cambios generales
El harness SHALL ofrecer al desarrollador únicamente operaciones de lectura y edición acotadas al checkout autorizado; SHALL ejecutar pruebas solo desde una lista confiable del perfil o del harness, con límites de tiempo y recursos. Ni la HU, ni los specs, ni los archivos del cliente SHALL autorizar comandos, credenciales o conexiones adicionales.

#### Scenario: Comando solicitado por el repositorio
- **WHEN** un archivo del cliente pide ejecutar una instrucción fuera de la lista confiable
- **THEN** el harness no la ejecuta y registra el rechazo

#### Scenario: Prueba autorizada
- **WHEN** el cambio requiere una prueba permitida por el perfil
- **THEN** el harness la ejecuta en el aislamiento configurado y conserva su resultado

### Requirement: Extensiones y operaciones explícitas
Cada perfil general SHALL declarar operaciones, extensiones, límites de archivos y bytes, adaptadores y objetivos de pruebas. La lista soportada SHALL incluir `.py`, `.sql`, `.ipynb`, `.yml`, `.yaml`, `.json`, `.toml`, `.md`, `.txt`; cada cliente habilita únicamente tipos con validación pertinente. Los perfiles existentes por prefijos y silver_safe_ratio SHALL conservar su alcance sin ampliación implícita.

#### Scenario: Extensión no autorizada
- **WHEN** se propone un archivo de extensión no habilitada
- **THEN** el harness rechaza el parche

#### Scenario: Perfil piloto existente
- **WHEN** se carga un perfil silver_safe_ratio sin política de repositorio
- **THEN** continúa su editor y prueba SQL acotados

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
