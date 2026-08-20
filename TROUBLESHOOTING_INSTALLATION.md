# Diagnóstico de instalación de Automation Center

Esta guía usa únicamente comprobaciones locales y evita mostrar secretos. Antes de cambiar configuración, ejecute:

```text
AutomationCenter diagnose --json
AutomationCenter health --json
```

Los resultados JSON contienen estados y nombres de configuración, no valores secretos.

## 1. Frontend `unhealthy`

El healthcheck interno del frontend debe consultar `http://127.0.0.1/health`. La UI también debe responder en `http://127.0.0.1:<puerto>/health` con HTTP 200.

| Síntoma | Comprobación | Acción segura |
|---|---|---|
| UI no responde | Visite el endpoint local `/health`. | Compruebe Docker y ejecute `AutomationCenter restart --service frontend --json`. |
| `frontend=unhealthy` | Revise la definición local de Compose y el diagnóstico. | Confirme que el healthcheck usa `127.0.0.1`, no `localhost`; reconstruya solo la instancia aislada afectada. |
| Puerto ocupado | El diagnóstico informa el puerto local. | No finalice procesos ajenos; elija un puerto de instancia distinto. |

## 2. PostgreSQL

PostgreSQL debe estar `healthy` antes de iniciar n8n y backend. Si no arranca, revise primero espacio libre, Docker disponible y el estado del contenedor.

No elimine el volumen de PostgreSQL para resolver un error de inicio. Realice un backup de metadata y use una instancia de prueba aislada si necesita reproducir un problema.

## 3. n8n y Public API

n8n puede estar saludable por `/healthz` y, aun así, tener una Public API key ausente o inválida. El preflight muestra un bloqueo seguro en estos casos y no importa workflows.

1. Inicie sesión en la instancia local de n8n.
2. Abra **Settings > n8n API**.
3. Cree o sustituya una Public API key según la documentación oficial.
4. Ejecute `AutomationCenter configure-n8n-api-key` y escriba la clave cuando se solicite; la entrada no se muestra.
5. Reinicie la instancia local y ejecute el preflight de `test-automation`.

| Estado de preflight | Significado | Acción |
|---|---|---|
| `not_configured` | No hay Public API key privada configurada. | Cree la key en n8n y use el comando local de configuración. |
| `rejected` | La key fue rechazada, revocada o caducó. | Cree una key nueva en n8n, sustitúyala localmente y reinicie. |
| `unavailable` | La Public API no responde de forma utilizable. | Confirme que n8n está healthy y revise la conectividad local. |
| `valid` | La llamada read-only autenticada funcionó. | Puede continuar con preflight e instalación. |

Nunca pegue la key en argumentos de comandos, `.env` versionados, capturas o logs. La Public API utiliza la cabecera `X-N8N-API-KEY`.[1]

## 4. Playwright

Playwright debe responder internamente en su endpoint `/health`. Si no está disponible, las automatizaciones que lo declaran como dependencia quedan bloqueadas por preflight.

Reinicie únicamente el servicio de Playwright y vuelva a ejecutar el preflight. No cambie los flujos productivos para probar el diagnóstico; use `test-automation` para validar el ciclo de importación y ejecución.

## 5. Puertos y Docker

| Problema | Acción segura |
|---|---|
| Docker no está disponible | Arranque Docker Desktop o Docker Engine y espere a que el diagnóstico lo informe como disponible. |
| Puerto de interfaz ocupado | Use un puerto aislado; no termine procesos de otras aplicaciones. |
| Imagen o contenedor no inicia | Revise estados y logs locales sin copiar valores de `runtime.env`. |
| Red de instancia aislada residual | Detenga la instancia con el launcher y use `down --remove-orphans` sin `--volumes`. |

## 6. Logs seguros y recuperación

No publique archivos `runtime.env`, directorios `.n8n`, logs que puedan contener valores de entorno, ni backups privados. Para compartir una incidencia, use solo códigos HTTP, estados de servicio, nombres de checks y tipos de error.

Antes de cualquier recuperación, cree un backup de metadata. La desinstalación normal preserva datos privados; la eliminación total requiere confirmación explícita y no debe usarse para solucionar problemas ordinarios.

## Referencias

[1] [Autenticación de la Public API de n8n](https://docs.n8n.io/connect/n8n-api/authentication/)
