# Spec Delta

## Purpose

Permitir instalaciones del mismo producto dedicadas a un cliente mediante configuración de despliegue reproducible, sin incorporar su identidad al código del harness.

## ADDED Requirements

### Requirement: Una instalación por cliente
Cada instalación SHALL activar exactamente un perfil cliente durante su proceso de vida. La HU y los endpoints de la App no SHALL seleccionar otro perfil. La distribución del producto SHALL permitir instalaciones para dos clientes distintos sin cambios en Python, HTML ni los valores genéricos del bundle.

#### Scenario: Dos instalaciones del mismo producto
- **WHEN** se preparan dos instalaciones con perfiles y parámetros diferentes a partir de la misma revisión del producto
- **THEN** cada instalación usa únicamente su repositorio, políticas y nombre visible configurados

#### Scenario: Selección de cliente desde una HU
- **WHEN** una HU o solicitud intenta cambiar el cliente de la instalación
- **THEN** el harness no cambia el perfil ni redirige el checkout o la publicación

### Requirement: Entrega explícita de configuración de despliegue
El despliegue SHALL entregar una copia concreta del perfil aprobado y su SHA-256 esperado y configurar `HARNESS_CLIENT_PROFILE_PATH` a un archivo accesible por la App. SHALL admitir parámetros externos para App, workspace y recursos del harness sin modificar el código común. SHALL separar las configuraciones de cliente y entorno de los defaults genéricos y evitar secretos inline. El arranque no SHALL descargar ni activar automáticamente `.harness/client.yaml` del repositorio cliente.

#### Scenario: Paquete de instalación válido
- **WHEN** el operador prepara un paquete con un perfil aprobado, hash y parámetros del entorno
- **THEN** el paquete contiene el archivo seleccionado, la App puede resolverlo al arrancar y no se necesita editar código del producto

#### Scenario: Ruta solo disponible en el equipo del operador
- **WHEN** el despliegue referencia un archivo que no fue entregado al runtime de la App
- **THEN** la App rechaza el arranque sin seleccionar un cliente alternativo

### Requirement: Recursos y registros separados por instalación
Cada instalación SHALL utilizar un espacio de registros y coordinación exclusivo y un sandbox con identidad distinta de su App, sin credenciales GitHub ni acceso a recursos del cliente. Los parámetros SHALL identificar recursos del harness y no SHALL habilitar ejecución o despliegue del cliente. La guía SHALL exigir verificar ACL y aislamiento antes de habilitar HUs; una validación de bundle no SHALL presentarse como prueba de permisos operativos.

#### Scenario: Configuración de otra instalación
- **WHEN** el operador prepara una segunda instalación
- **THEN** asigna sus registros, coordinación y sandbox propios y comprueba sus accesos antes de aceptar HUs

#### Scenario: Piloto existente
- **WHEN** se migra la instalación piloto de NaturaPet al perfil externo
- **THEN** conserva sus recursos demo_harness y el warehouse sintético autorizado sin cambiar recursos NaturaPet

### Requirement: Inicio e identidad visual parametrizados
El lanzador SHALL recibir nombre de App y perfil Databricks sin valores de cliente implícitos, y SHALL obtener la URL de esa App tras iniciarla. La interfaz SHALL presentar la identidad común del producto y el nombre del cliente desde el perfil, conservando la entrada HU y descripción. La documentación genérica SHALL remitir los valores concretos del piloto a ejemplos o guía específica y conservar evidencia histórica accesible.

#### Scenario: Inicio de una App configurada
- **WHEN** el operador invoca el lanzador con App y perfil válidos
- **THEN** inicia esa App y abre la URL devuelta para ella

#### Scenario: Parámetros ausentes o inicio fallido
- **WHEN** faltan parámetros requeridos o falla la consulta o el inicio de la App
- **THEN** el lanzador muestra un diagnóstico y no abre una URL fija del piloto

#### Scenario: Presentación de otro cliente
- **WHEN** otra instalación responde con un nombre visible distinto
- **THEN** la UI muestra ese nombre con el mismo HTML y conserva la identidad del producto
