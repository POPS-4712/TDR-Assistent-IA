# PHASE 2.17 — Corrección de defectos post-release y nueva validación E2E

> **STATUS: NOT READY**
>
> La corrección del healthcheck del frontend fue validada en una composición Docker aislada. La integración n8n ahora falla de forma segura antes de importar workflows, pero no se obtuvo una Public API key válida creada en n8n mediante un mecanismo soportado; por ello no se ejecutó el ciclo E2E completo de `test-automation` y no se creó la candidata `v1.0.1`.

```text
PHASE 2.17
STATUS: NOT READY

BACKEND: PASS
FRONTEND: PASS
DOCKER: PASS
FRONTEND HEALTH: PASS
N8N API AUTH: FAIL (NOT CONFIGURED IN THE ISOLATED INSTANCE)
E2E TEST AUTOMATION: FAIL (SAFELY BLOCKED BEFORE IMPORT)
SECURITY: PASS
BACKUP: PASS
DOCUMENTATION: PASS

WINDOWS X64: NOT TESTED
WINDOWS ARM64: NOT TESTED
LINUX X64: NOT TESTED
LINUX ARM64: NOT TESTED
MACOS INTEL: NOT TESTED
MACOS ARM64: NOT TESTED

RELEASE: NOT CREATED
```

## 1. Resumen ejecutivo

La validación de Phase 2.16 había identificado dos defectos: el frontend quedaba `unhealthy` cuando su healthcheck usaba `localhost`, y una clave aleatoria escrita en `runtime.env` no era una Public API key válida de n8n. En Phase 2.17 se corrigió el primer defecto y se sustituyó el segundo comportamiento inseguro por una detección explícita que bloquea la instalación antes de mutar n8n.

La documentación oficial de n8n indica que una Public API key debe crearse desde **Settings > n8n API** y enviarse mediante `X-N8N-API-KEY`; no documenta un mecanismo de bootstrap por variable de entorno ni un endpoint público para crear automáticamente esa clave.[1] La evidencia de la instancia aislada confirmó de nuevo que, sin una clave creada y configurada de esa forma, el preflight debe permanecer bloqueado. No se usaron APIs internas no documentadas, claves hardcodeadas ni desactivación de autenticación.

## 2. Cambios realizados

| Área | Cambio aplicado | Objetivo |
|---|---|---|
| Healthcheck de producción | El healthcheck de `frontend` en `docker-compose.prod.yml` pasó de `localhost` a `127.0.0.1`. | Resolver el estado `unhealthy` reproducido en Phase 2.16. |
| Composición de desarrollo | Se añadió el mismo healthcheck IPv4 al frontend de `docker-compose.yml`. | Evitar divergencia entre desarrollo y producción. |
| Validación estática | `validate_definitions.py` exige el healthcheck IPv4 y rechaza `localhost/health`. | Prevenir regresiones de packaging. |
| Clave n8n | `write_runtime_env()` ya no genera una clave aleatoria tratada como Public API key. | Eliminar una autenticación ficticia. |
| Configuración privada | Se añadió `AutomationCenter configure-n8n-api-key`, con entrada mediante prompt sin eco y persistencia solo en `runtime.env` privado. | Permitir configurar una clave creada oficialmente sin exponerla en argumentos, logs o Git. |
| Cliente n8n | Se añadió una llamada autenticada y read-only a `GET /api/v1/workflows?limit=1`. | Clasificar `not_configured`, `rejected`, `unavailable` o `valid` sin revelar valores ni cuerpos de respuesta. |
| Preflight | Se incorporó el check `n8n_public_api_auth`; una clave ausente o rechazada bloquea antes de cualquier importación. | Evitar el antiguo HTTP 400 encapsulando un HTTP 401 de n8n. |
| Requisitos Python | `requirements-dev.txt` ahora delega en `requirements.txt`. | Eliminar la contradicción `pytest-asyncio==1.3.0` frente a `1.4.0`. |
| Documentación | Se crearon cuatro guías operativas en la raíz. | Cubrir instalación, upgrade, troubleshooting y packaging. |

## 3. Defectos corregidos y límites restantes

### 3.1 Frontend `unhealthy`: **corregido y verificado**

La composición temporal levantó `frontend`, `backend`, `postgres`, `n8n` y `playwright` con estado `healthy`. `AutomationCenter health` devolvió `healthy: true`, y `http://127.0.0.1:43017/health` respondió HTTP 200. Esta evidencia verifica tanto el healthcheck interno como el endpoint local expuesto.

### 3.2 Public API n8n: **corrección de seguridad aplicada; E2E funcional pendiente**

La generación de `N8N_API_KEY` por el runtime fue retirada, porque un valor aleatorio no registra una key de Public API dentro de n8n. La configuración debe partir de una clave real creada por el mecanismo soportado de n8n.[1]

En la instancia aislada no se configuró una clave válida. El preflight de `test-automation` devolvió `status=blocked`, `n8n_public_api_auth=blocked`, `details=not_configured` y `mutations_applied=False`. Un intento de instalación devolvió HTTP 400, de forma esperada, sin invocar importación ni crear workflows. La UI presentó el mensaje seguro **“n8n Public API authentication not configured”**.

Esto resuelve el defecto de comportamiento inseguro y proporciona una ruta de recuperación local, pero no satisface el criterio funcional de autenticación válida ni autoriza una release. El E2E completo requiere configurar en la instancia aislada una key creada en la pantalla oficial de n8n y volver a ejecutar: discover, preflight, install, comprobación de existencia en n8n, enable, execute, comprobación de ejecución, disable, uninstall y comprobación de eliminación.

## 4. Pruebas ejecutadas

| Prueba | Resultado | Evidencia |
|---|---|---|
| Sintaxis de módulos y tests modificados | **PASS** | `compileall` terminó correctamente. |
| Validación de definiciones y CI | **PASS** | `validate_definitions.py` y `validate_release_ci.py` finalizaron correctamente. |
| Backend pytest | **PASS: 105 pruebas, 0 fallos** | Se ejecutó en imagen temporal Python 3.11, la versión usada por `backend/Dockerfile`. |
| Frontend Vitest | **PASS: 11 pruebas** | `npm test -- --run`. |
| Build frontend | **PASS** | `tsc && vite build`. |
| Health Docker aislado | **PASS** | Cinco servicios en `healthy`; launcher `healthy: true`. |
| Health frontend IPv4 | **PASS** | HTTP 200 en `127.0.0.1:43017/health`. |
| Preflight sin clave n8n | **PASS como control de seguridad** | `blocked`, sin mutaciones. |
| Instalación E2E con clave válida | **FAIL / NOT EXECUTED** | No se configuró una key real de Public API. |
| Backup, validate y restore dry-run repetido | **PASS** | Exportación y validación correctas; dos restores `dry_run=true`. |
| Escaneo de seguridad | **PASS** | Fuente controlada, runtime temporal, logs e imagen backend temporal. |

## 5. Resultado de Docker, n8n y E2E

La composición se creó con un directorio de datos temporal y un puerto de UI aislado. Tras la prueba, se ejecutó `down --remove-orphans` sin `--volumes`, se eliminaron solo los datos temporales de la instancia y se retiró la imagen backend temporal. No se eliminaron volúmenes, perfiles, credenciales ni automatizaciones reales.

La instancia n8n fue saludable, pero Public API auth permaneció no configurada. El estado `healthy` de n8n no equivale a una autorización válida para la Public API; esta separación queda ahora reflejada por el preflight. En consecuencia, el flujo E2E obligatorio no se declaró parcialmente exitoso: install, enable, execute, disable y uninstall siguen sin evidencia y se clasifican como **FAIL / NOT EXECUTED**.

## 6. Seguridad, backup y documentación

Los escaneos de fuente controlada, configuración runtime temporal, logs y export de imagen backend no detectaron nombres privados prohibidos ni patrones de secreto de alta confianza. Los resultados no imprimieron ningún valor de configuración.

El backup exportado no expuso campos de nombre `secret`, `token`, `password` o `api_key` de nivel superior. Su validación y dos restores dry-run finalizaron correctamente. No se ejecutó una restauración con escritura porque el requisito de esta fase era no alterar datos reales y el objetivo era comprobar seguridad e idempotencia del modo dry-run.

| Documento creado | Contenido cubierto |
|---|---|
| `INSTALLATION.md` | Plataformas, instalación, checksums, primer arranque, health y configuración segura de n8n. |
| `UPGRADING.md` | Backup previo, actualización, preservación, rollback, credenciales y volúmenes. |
| `TROUBLESHOOTING_INSTALLATION.md` | Frontend, PostgreSQL, n8n, Playwright, puertos, Docker, logs seguros y recuperación. |
| `PACKAGING.md` | Targets, artefactos, runners, validación, SHA-256, pipeline y limitaciones de firma. |

## 7. Matriz de plataformas y artefactos

No se creó ni publicó `v1.0.1`. El archivo `VERSION` sigue en `1.0.0`, no existe tag ni release `v1.0.1` en el repositorio remoto, y los seis builds nativos de una candidata no se ejecutaron. Por ello todos los estados de plataforma y los SHA-256 de candidata son **NOT TESTED**, no PASS.

La release `v1.0.0` no se modificó ni sobrescribió.[2]

## 8. Incidencias y siguiente paso obligatorio

La única incidencia funcional que bloquea el cierre READY es la ausencia de una Public API key real en la instancia n8n aislada. La investigación documentó que automatizar su creación mediante una variable de entorno no está soportado por la documentación oficial. El paso manual seguro es crear la key en la UI n8n y registrarla localmente mediante `AutomationCenter configure-n8n-api-key`; una vez hecho, la validación restante puede ejecutarse de forma automática sin cuentas externas sobre `test-automation`.

No debe crearse ni publicarse `v1.0.1` hasta obtener evidencia real de autenticación válida, del E2E completo y de la matriz nativa de seis targets. `BLOCKED`, `NOT TESTED` y la seguridad fail-closed no se reinterpretan como PASS.

## Referencias

[1] [n8n — Authentication for the Public API](https://docs.n8n.io/connect/n8n-api/authentication/)
[2] [Automation Center v1.0.0 release](https://github.com/POPS-4712/TDR-Assistent-IA/releases/tag/v1.0.0)
