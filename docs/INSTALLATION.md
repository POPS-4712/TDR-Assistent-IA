# Instalación de Automation Center

**Versión de producto:** `1.0.0`  
**Estado de los paquetes nativos en este repositorio:** las definiciones de instalación están validadas; los instaladores `.exe`, `.deb`, `.dmg` y archivos portables deben construirse en sus plataformas nativas antes de distribuirse.

> Automation Center se ejecuta localmente. Sus servicios permanecen en el equipo del usuario y la interfaz se abre en el navegador predeterminado. Las cuentas externas son opcionales durante la primera ejecución.

## Compatibilidad y requisitos

La distribución se planifica para Windows x64, Windows ARM64, Linux x64, Linux ARM64, macOS Intel y macOS Apple Silicon. El instalador correspondiente comprueba su propia arquitectura antes de continuar. Nunca se debe instalar un paquete x64 en ARM64, ni a la inversa.

| Plataforma | Formato de distribución previsto | Runtime local requerido | Estado de definición |
|---|---|---|---|
| Windows x64 | Instalador `.exe` y ZIP portable | Docker Desktop o Docker Engine en funcionamiento | Validada estáticamente |
| Windows ARM64 | Instalador `.exe` y ZIP portable | Docker Desktop o Docker Engine compatible con ARM64 | Validada estáticamente |
| Ubuntu/Debian x64 | `.deb` y archivo portable | Docker Engine compatible con x64 | Validada estáticamente |
| Ubuntu/Debian ARM64 | `.deb` y archivo portable | Docker Engine compatible con ARM64 | Validada estáticamente |
| macOS Intel | `.dmg` | Docker Desktop para Intel | Validada estáticamente |
| macOS Apple Silicon | `.dmg` | Docker Desktop para Apple Silicon | Validada estáticamente |

El instalador no incorpora Docker ni fuerza una instalación silenciosa de un runtime incompatible. Si Docker no está disponible, la comprobación de compatibilidad explica el problema y la aplicación no intenta finalizar procesos ajenos ni ocupar puertos existentes por la fuerza.

## Instalación normal

Cuando esté disponible el artefacto nativo de la plataforma, se ejecuta el instalador correspondiente. En Windows, este crea accesos directos en el menú Inicio y, si se selecciona, en el escritorio. En Linux se instala un lanzador y una entrada de escritorio. En macOS, la aplicación se copia desde el DMG a Aplicaciones.

El instalador prepara el lanzador local, la composición de producción y la configuración privada. En un uso normal, el usuario abre **Automation Center** desde su acceso directo. No necesita ejecutar comandos de Docker ni importar manualmente workflows.

| Paso de primera ejecución | Comportamiento |
|---|---|
| Bienvenida | Explica que el runtime y los datos permanecen locales. |
| Compatibilidad | Comprueba sistema operativo, arquitectura, espacio disponible, runtime y puertos preferidos. |
| Servicios locales | Comprueba backend, PostgreSQL, n8n y Playwright automáticamente. |
| Almacenamiento seguro | Crea los directorios privados y los secretos de runtime local sin mostrarlos en pantalla. |
| Primer perfil | Solicita crear o seleccionar un perfil editable; no presupone profesión. |
| Cuentas | Permite omitir Google, Gemini, Telegram, WhatsApp u otras cuentas para conectarlas más tarde. |
| Finalización | Descubre automatizaciones y ejecuta preflight; no instala workflows reales automáticamente. |

## Directorio de datos de usuario

Los binarios de la aplicación y los datos personales están separados. Las actualizaciones del paquete no sustituyen el directorio de datos de usuario ni los volúmenes de PostgreSQL y n8n.

| Plataforma | Ruta estándar |
|---|---|
| Windows | `%LOCALAPPDATA%\AutomationCenter` |
| Linux | `~/.local/share/automation-center` |
| macOS | `~/Library/Application Support/AutomationCenter` |

La ruta contiene `config`, `runtime`, `logs`, `backups`, `vault-metadata` y `state`. Las bases de datos de PostgreSQL y n8n usan volúmenes dedicados con el prefijo `automation-center`; sobreviven a una actualización normal.

## Cuentas y automatizaciones

La primera ejecución no exige cuentas externas. Desde **Accounts** se pueden conectar posteriormente las cuentas reales necesarias. Cada cambio ejecuta el preflight automático: una automatización pasa a `Ready to install` únicamente cuando sus cuentas, scopes, credenciales n8n, runtime y configuración requeridos están disponibles.

El estado `Blocked` no es un error de instalación. Indica una dependencia real pendiente y muestra el motivo sin exponer tokens, claves ni referencias internas. Los workflows solo se importan después de pulsar explícitamente **Install**.

## Modo portable

El modo portable mantiene su carpeta `data` junto al paquete portable y sigue separando los binarios de los datos. Debe utilizarse solamente con el archivo correspondiente a la arquitectura del equipo. El archivo portable no contiene credenciales, perfiles, backups ni volúmenes preexistentes.

## Modo avanzado

La página **System** muestra la salud de los servicios locales. La gestión de inicio, parada y reinicio está reservada para **Advanced mode** y permanece deshabilitada a menos que la instalación local autorice expresamente el control limitado de sus propios contenedores. El modo normal no expone detalles internos de Docker.
