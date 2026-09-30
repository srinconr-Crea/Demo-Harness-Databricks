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
El harness SHALL rechazar rutas fuera de los prefijos permitidos, absolutas, con ascenso de directorio, con separadores no admitidos, enlaces que escapen del checkout o dentro de `.github/`. SHALL aplicar esta comprobación al parche, al estado final del checkout y al conjunto que se publicará.

#### Scenario: Ruta fuera de política
- **WHEN** el desarrollador propone o produce un archivo fuera de política
- **THEN** la ejecución bloquea la edición o publicación de ese archivo

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
