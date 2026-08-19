# Arquitectura de empaquetado de Automation Center

**Versión de producto:** `1.0.0`  
**Estado:** diseño implementable para distribución local con Docker Desktop o Docker Engine como runtime.

> Automation Center se distribuye como una aplicación local. El instalador prepara un lanzador nativo y una configuración de usuario; los servicios de aplicación siguen ejecutándose en contenedores locales. No se requieren comandos Docker durante el uso ordinario.

## Decisión de arquitectura

El producto preserva la arquitectura existente —React, FastAPI, PostgreSQL, n8n y Playwright— y añade una capa de distribución fuera de los contenedores. Esta capa contiene el lanzador, el gestor de servicios, el asistente de primera ejecución y los scripts de actualización. Los secretos se crean en el primer arranque y se guardan solamente en el directorio privado de usuario; no se copian al paquete de aplicación ni a las imágenes.

| Capa | Responsabilidad | Contenido que nunca transporta |
|---|---|---|
| Paquete de aplicación | Lanzador, compose de producción, imágenes o referencias de imágenes, frontend y documentación. | Credenciales, `.env`, volúmenes, copias de datos de usuario. |
| Directorio de usuario | Configuración privada, estado de runtime, logs, backups de metadata, manifest de primera ejecución. | Binaries de instalación y código fuente distribuido. |
| Volúmenes Docker con nombre de producto | Datos persistentes de PostgreSQL y n8n. | Archivos de instalación, logs de secretos y artefactos de build. |
| Credential Vault existente | Secretos de proveedores autorizados por el usuario. | Exportación hacia ZIP, instaladores, bundles web o backups de metadata. |

## Directorios estables de datos

Los scripts y el gestor de runtime determinan la raíz con prioridades explícitas: `AUTOMATION_CENTER_DATA_DIR`, modo portable y finalmente la ruta estándar del sistema operativo. La raíz se crea con permisos de usuario y contiene archivos de configuración no versionados por Git.

| Plataforma | Directorio normal | Directorio portable |
|---|---|---|
| Windows | `%LOCALAPPDATA%\AutomationCenter` | `<carpeta-portable>\data` |
| Linux | `~/.local/share/automation-center` | `<carpeta-portable>/data` |
| macOS | `~/Library/Application Support/AutomationCenter` | `<Application Support>/AutomationCenterPortable` |

Cada raíz contiene `config/`, `runtime/`, `logs/`, `backups/`, `vault-metadata/` y `state/`. El archivo de variables generado en primera ejecución queda en `config/runtime.env`, con permisos restringidos cuando la plataforma lo permite. Los volúmenes se nombran con un prefijo dedicado para evitar interferir con desarrollo.

## Compose de producción

La composición de producción es independiente de `docker-compose.yml`. Expone únicamente la interfaz en loopback y mantiene backend, PostgreSQL, n8n y Playwright en una red interna. El frontend usa un proxy `/api/` hacia FastAPI, para no publicar el puerto del backend en una instalación normal. Los servicios tienen health checks y políticas de reinicio seguras.

| Servicio | Exposición normal | Persistencia | Comprobación |
|---|---|---|---|
| Frontend | `127.0.0.1:<puerto-ui>` | No requerida | HTTP `/` |
| Backend | Interna; proxy por frontend | Logs y configuración de usuario | HTTP `/health` |
| PostgreSQL | Interna | Volumen de producción | `pg_isready` |
| n8n | Interna | Volumen de producción | HTTP `/healthz` |
| Playwright | Interna | No requerida | HTTP `/health` |

Los puertos preferidos se verifican antes del arranque. Un conflicto se informa con proceso y puerto cuando el sistema permite determinarlo; el gestor nunca finaliza procesos ajenos. El usuario puede elegir un puerto local alternativo para la interfaz.

## Selección de tecnología de instalador

El proyecto mantiene definiciones de paquete por plataforma y solo genera binarios nativos en una máquina compatible. Las definiciones nunca hacen pasar un binario x64 por ARM64.

| Plataforma | Formato previsto | Tecnología de construcción | Validación de arquitectura |
|---|---|---|---|
| Windows x64 | `.exe` y ZIP portable | Inno Setup + lanzador Python empaquetado en la arquitectura destino | `x64compatible` y `build-windows.ps1 -Architecture x64` |
| Windows ARM64 | `.exe` y ZIP portable | Inno Setup ARM64 + lanzador construido en Windows ARM64 | `arm64` y `build-windows.ps1 -Architecture arm64` |
| Linux x64 | `.deb` y `tar.gz` portable | `dpkg-deb` en Linux x64 | `amd64` |
| Linux ARM64 | `.deb` y `tar.gz` portable | `dpkg-deb` en Linux ARM64 | `arm64` |
| macOS Intel | `.dmg` | `pkgbuild` y `hdiutil` en macOS Intel | `x86_64` |
| macOS Apple Silicon | `.dmg` | `pkgbuild` y `hdiutil` en Apple Silicon | `arm64` |

Los scripts marcan una compilación en otro sistema como `PLATFORM UNAVAILABLE`; no crean archivos sustitutos vacíos ni artefactos con una extensión falsa.

## Primera ejecución y actualización

El lanzador comprueba arquitectura, Docker/runtime, espacio disponible, puertos y salud de servicios. Si el directorio de usuario no tiene el marcador `state/first-run-complete.json`, inicia el asistente de primera ejecución en la interfaz. El asistente permite crear o seleccionar un perfil y omitir las cuentas externas. Las cuentas externas nunca bloquean el inicio de la aplicación.

Antes de una actualización, el lanzador solicita al backend un backup de metadata y valida el checksum del resultado. La actualización conserva la raíz de usuario y los volúmenes de producción. Una desinstalación estándar retira el paquete y los accesos directos, pero conserva los datos. La eliminación de datos requiere una opción explícita y una confirmación separada.

## Límites honestos de build

El repositorio contiene las definiciones, controles de arquitectura y scripts para las seis distribuciones. La generación real de instaladores y paquetes exige el sistema operativo y las herramientas nativas correspondientes. Las pruebas en un sistema Windows x64 no constituyen pruebas de runtime en Windows ARM64, Linux ni macOS.
