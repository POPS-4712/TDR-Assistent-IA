# Instalación de Automation Center

Automation Center es una aplicación **local-first**. La interfaz, el backend, PostgreSQL, n8n y Playwright se ejecutan localmente mediante Docker. Los instaladores no requieren que se envíen credenciales al repositorio ni a un servicio externo.

## 1. Plataforma y artefacto correcto

| Plataforma | Arquitectura | Artefacto distribuido |
|---|---|---|
| Windows | x64 | `AutomationCenter-<versión>-win-x64.exe` o `.zip` |
| Windows | ARM64 | `AutomationCenter-<versión>-win-arm64.exe` o `.zip` |
| Linux | x64 | `AutomationCenter-<versión>-linux-x64.deb` o `.tar.gz` |
| Linux | ARM64 | `AutomationCenter-<versión>-linux-arm64.deb` o `.tar.gz` |
| macOS Intel | x64 | `AutomationCenter-<versión>-macos-x64.dmg` |
| macOS Apple Silicon | ARM64 | `AutomationCenter-<versión>-macos-arm64.dmg` |

Descargue siempre el artefacto que corresponda a la arquitectura real del equipo. La release incluye `SHA256SUMS.txt` y `release-manifest.json`; ambos deben acompañar al artefacto descargado.

## 2. Verificación de integridad

Antes de ejecutar un instalador, calcule su SHA-256 y compárelo con `SHA256SUMS.txt` publicado con la release.

| Sistema | Comando de verificación |
|---|---|
| Windows PowerShell | `Get-FileHash .\AutomationCenter-<versión>-win-x64.exe -Algorithm SHA256` |
| Linux | `sha256sum AutomationCenter-<versión>-linux-x64.deb` |
| macOS | `shasum -a 256 AutomationCenter-<versión>-macos-arm64.dmg` |

> Un checksum distinto implica que el archivo no debe instalarse. Descárguelo de nuevo desde la release autorizada y vuelva a comprobarlo.

## 3. Requisitos locales

En Windows, instale y arranque Docker Desktop antes de iniciar Automation Center. En Linux o macOS, Docker Engine o Docker Desktop debe estar disponible para el usuario que ejecuta la aplicación. Se necesita espacio local para las imágenes y los volúmenes de PostgreSQL y n8n.

No copie archivos `.env`, `runtime.env`, directorios `.n8n` ni datos de PostgreSQL entre instalaciones. El instalador crea una configuración privada e independiente por usuario.

## 4. Instalación y primer arranque

Ejecute el instalador de la arquitectura correcta. En Windows puede usar el instalador gráfico o una ejecución silenciosa controlada mediante los parámetros compatibles de Inno Setup. Para una instalación normal, no use opciones de eliminación de datos.

Al primer inicio, el launcher crea una configuración privada en el perfil local y levanta una composición Docker aislada. Abra la URL local mostrada por la aplicación. La comprobación de estado se ejecuta con:

```text
AutomationCenter health --json
```

El resultado correcto informa los servicios `frontend`, `backend`, `postgres`, `n8n` y `playwright` como saludables o en ejecución según su contrato. La UI debe responder en `http://127.0.0.1:<puerto>/health` con HTTP 200.

## 5. Configuración de n8n y cuentas

Las automatizaciones requieren una **Public API key real de n8n**. Automation Center no genera ni finge esa clave. En la instancia local de n8n, cree la clave mediante **Settings > n8n API > Create an API key** y configure su caducidad según la política local.[1]

Guarde la clave únicamente a través del comando local, que la solicita sin eco:

```text
AutomationCenter configure-n8n-api-key
```

Después, reinicie los servicios locales. El preflight de una automatización confirma la autenticación mediante una llamada read-only; si la clave falta, ha sido revocada o no es válida, la instalación queda bloqueada sin importar workflows. Nunca incluya la clave en argumentos de línea de comandos, archivos versionados, capturas, chats o tickets.

Conecte las cuentas externas desde la aplicación local únicamente cuando la automatización las requiera. El workflow `test-automation` se reserva para pruebas y no necesita credenciales externas.

## 6. Diagnóstico básico

| Síntoma | Primera acción segura |
|---|---|
| La aplicación no inicia | Confirme que Docker está en ejecución y use `AutomationCenter diagnose --json`. |
| La UI no responde | Compruebe `http://127.0.0.1:<puerto>/health` y el estado `frontend`. |
| El preflight bloquea n8n | Cree o sustituya la Public API key en n8n y ejecute `AutomationCenter configure-n8n-api-key`; reinicie. |
| Un puerto está ocupado | No finalice procesos ajenos. Cambie el puerto de la instancia aislada y reinicie. |

Consulte [TROUBLESHOOTING_INSTALLATION.md](./TROUBLESHOOTING_INSTALLATION.md) para recuperación y diagnóstico detallado.

## Referencias

[1] [Autenticación de la Public API de n8n](https://docs.n8n.io/connect/n8n-api/authentication/)
