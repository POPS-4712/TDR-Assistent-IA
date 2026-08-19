# Phase 2.16 — Validación post-publicación de la release v1.0.0

**Fecha de validación:** 20 de agosto de 2026  
**Alcance:** comprobación material de la release publicada `v1.0.0`, con instalación aislada en Windows x64, sin modificar el tag, los activos publicados, credenciales reales ni datos de producción.  
**Estado final:** **NOT READY — BLOCKED por dos defectos funcionales reproducidos.**

> La release existe, contiene los diez distribuibles comprometidos y sus hashes fueron verificados. Sin embargo, no se puede declarar lista para producción porque el healthcheck interno del frontend falla y la importación de automatizaciones en n8n devuelve HTTP 401 aun cuando el preflight sea `ready`.

## 1. Alcance y reglas de evidencia

La validación utilizó exclusivamente los activos descargados desde la release `v1.0.0`. Las pruebas de instalación se ejecutaron en directorios temporales bajo `%TEMP%`, con una instancia Docker aislada por sufijo aleatorio. La limpieza se realizó con `down --remove-orphans`, sin `--volumes`; ningún volumen, perfil, secreto o automatización de producción fue eliminado.

| Área | Método aplicado | Resultado |
|---|---|---|
| Integridad de release | Descarga real de 12 activos; recomputación de SHA-256 y contraste cruzado con `SHA256SUMS.txt`, `release-manifest.json` y digest del servicio de releases. | **PASS: 10/10 artefactos** |
| Artefactos Windows | Integridad de ZIP, launcher PE extraído y escaneo de secretos. El wrapper Inno Setup es PE32 x86, mientras que los launchers ZIP son x64 y ARM64 respectivamente. | **PASS** |
| Artefactos Linux | Arquitectura DEB, contenido, payload ELF de DEB/TAR y escaneo de seguridad. | **PASS: x64 y ARM64** |
| Artefactos macOS | Existencia, firma de archivo y escaneo bruto. La arquitectura del payload no se montó ni ejecutó porque no había host macOS ni herramienta DMG disponible. | **PARTIAL PASS; payload NOT TESTED** |
| Seguridad de distribución | Escáner del proyecto sobre diez activos, extracciones de Windows/Linux y metadatos publicados. | **PASS; sin coincidencias de alta confianza** |
| Instalador publicado Windows x64 | Instalación silenciosa aislada, arranque, endpoints, perfil, backup de metadatos, reinstalación y desinstalación normal. | **PASS** |
| Regresión `test-automation` | Descubrimiento y preflight real sin cuentas externas; importación n8n y ejecución posterior. | **FAIL: importación HTTP 401** |

## 2. Integridad, procedencia y contratos de distribución

Los diez artefactos comprometidos fueron descargados desde la release publicada y cada hash SHA-256 local coincidió con tres fuentes: la suma publicada, el manifiesto de release y el digest de GitHub. El manifiesto declara diez registros con estado `BUILT` y validación positiva. No se utilizaron ejecutables de un build local como sustituto de la release.

| Plataforma | Activos comprobados | Verificación material |
|---|---:|---|
| Windows x64 | `.exe`, `.zip` | Hashes correctos; launcher ZIP PE x64; escaneo PASS. |
| Windows ARM64 | `.exe`, `.zip` | Hashes correctos; launcher ZIP PE ARM64; escaneo PASS. |
| Linux x64 | `.deb`, `.tar.gz` | Hashes correctos; DEB `amd64`; payload ELF x64; escaneo PASS. |
| Linux ARM64 | `.deb`, `.tar.gz` | Hashes correctos; DEB `arm64`; payload ELF ARM64; escaneo PASS. |
| macOS x64 | `.dmg` | Hash correcto y escaneo bruto PASS; arquitectura del payload **NOT TESTED**. |
| macOS ARM64 | `.dmg` | Hash correcto y escaneo bruto PASS; arquitectura del payload **NOT TESTED**. |

Los validadores locales de definiciones de packaging y de la pipeline CI completaron correctamente. La evidencia de CI nativa continúa siendo el run de publicación `32284849538`, que generó y publicó el contrato completo antes de crear el tag de release.[1] [2]

## 3. Resultado del instalador y preservación de datos en Windows x64

El instalador descargado de la release fue comprobado en el host Windows contra el SHA-256 publicado antes de ejecutarse. La prueba aislada existente finalizó con `INSTALL_TEST=PASS`, `UPGRADE_TEST=PASS`, `UNINSTALL_TEST=PASS`, `FIRST_RUN_RUNTIME=PASS`, `PROFILE_PERSISTENCE=PASS` y `METADATA_BACKUP_SECURITY=PASS`.

La instalación generó una configuración privada con identificador de instancia aislado. La reinstalación conservó el perfil de prueba y el directorio de backups. La desinstalación silenciosa normal conservó los datos privados aislados, conforme a la política del instalador; posteriormente, el directorio temporal de prueba fue eliminado. No se invocó `remove-data --confirm-remove-data` y no se borraron volúmenes reales.

## 4. Defectos funcionales reproducidos

### 4.1 Healthcheck interno del frontend: **FAIL**

La UI respondió por HTTP en el puerto aislado y el endpoint externo `http://127.0.0.1:<puerto>/health` respondió correctamente. Sin embargo, el estado Docker del servicio `frontend` permaneció `unhealthy`. La comprobación dentro del contenedor confirmó esta diferencia:

| Verificación dentro de `frontend` | Resultado |
|---|---|
| `wget --spider http://127.0.0.1/health` | **Exit 0** |
| `wget --spider http://localhost/health` | **Exit 1; conexión rechazada** |
| Estado Docker del contenedor | **unhealthy** |

La causa reproducida es que el healthcheck de Compose usa `http://localhost/health`, mientras Nginx escucha de forma efectiva por IPv4; en este contenedor `localhost` resuelve a una ruta que rechaza la conexión. Como el gestor local exige que todos los servicios estén `healthy` o `running`, `AutomationCenter health` no puede declarar el runtime sano aunque la UI sea accesible.

**Corrección requerida para una nueva release:** cambiar el healthcheck del servicio frontend a `http://127.0.0.1/health` o configurar explícitamente un listener IPv6 compatible. La corrección debe probarse en un nuevo build; no se altera el activo `v1.0.0` ya publicado.

### 4.2 Importación n8n de `test-automation`: **FAIL**

El workflow `test-automation` fue el único workflow seleccionado para la regresión. No tiene requisitos ni mappings de credenciales, y su preflight aislado devolvió `ready` sin mutaciones. Sin embargo, `POST /api/v1/automations/test-automation/install` devolvió HTTP 400 porque el backend encapsuló un fallo de importación n8n. La clasificación no sensible de logs confirmó que n8n rechazó el contexto de autenticación.

La comprobación directa, usando el mismo filtrado de campos que el cliente de la aplicación, devolvió **HTTP 401** al llamar a `POST /api/v1/workflows`. El test no mostró la respuesta ni ninguna clave. La evidencia indica una incompatibilidad entre la clave generada como `N8N_API_KEY` para el runtime y la autenticación real de la API pública n8n: la generación local de un valor no aprovisiona por sí misma una API key pública válida en n8n.

**Impacto:** la aplicación puede descubrir y preflight el workflow, pero no importarlo, habilitarlo ni ejecutarlo. Por tanto, la automatización local no cumple el flujo de instalación de extremo a extremo.

**Corrección requerida para una nueva release:** implementar un mecanismo compatible y verificable de aprovisionamiento/recuperación de la API key pública n8n, o sustituir la integración por un mecanismo de autenticación soportado que se configure en la instancia local. El contrato debe incluir una prueba de importación real, seguida de eliminación del workflow de prueba, antes de publicar una nueva release.

## 5. Suites, validadores y documentación

| Comprobación | Resultado | Observación |
|---|---|---|
| Validadores de definiciones de packaging y CI | **PASS** | Se validaron los seis targets nativos, gates, checksums y contrato completo. |
| Frontend Vitest | **PASS: 3 archivos, 11 pruebas** | Ejecutado en el host Windows. |
| Frontend producción (`tsc && vite build`) | **PASS** | Build generado correctamente. |
| Backend pytest en host Windows | **NOT TESTED (host-blocked)** | Python 3.14 no dispone de wheel compatible para `asyncpg==0.29.0` y no hay compilador C++ disponible; adicionalmente `requirements-dev.txt` contradice la versión de `pytest-asyncio` declarada en `requirements.txt`. El CI nativo ya había ejecutado la suite en un entorno compatible, pero esto no sustituye una ejecución local de Phase 2.16. |
| `INSTALLATION.md` | **MISSING** | No existe en la raíz. |
| `UPGRADING.md` | **MISSING** | No existe en la raíz. |
| `TROUBLESHOOTING_INSTALLATION.md` | **MISSING** | No existe en la raíz. |
| `PACKAGING.md` | **MISSING** | No existe en la raíz. |

La ausencia de los cuatro documentos solicitados es un incumplimiento documental independiente. Antes de volver a clasificar una release como lista, deben describir instalación, upgrade, desinstalación no destructiva, restauración, diagnóstico de Docker/n8n, verificación de checksums y arquitectura soportada.

## 6. Matriz de salida Phase 2.16

| Criterio de aceptación | Estado | Evidencia |
|---|---|---|
| Release y diez artefactos verificables | **PASS** | Descarga real; 10/10 hashes y tamaños concordantes. |
| No secretos en activos revisados | **PASS** | Escáner del proyecto sobre archivos y extracciones. |
| Instalación y desinstalación aisladas Windows x64 | **PASS** | Instalador publicado, perfil, backup, upgrade y uninstall normal. |
| Backend, PostgreSQL, n8n y Playwright observables | **PASS (observación aislada)** | Estado `healthy` en el runtime temporal durante diagnóstico. |
| Frontend accesible por HTTP | **PASS** | Endpoint HTTP de la UI respondió. |
| Healthcheck agregado del runtime | **FAIL** | `frontend=unhealthy` por `localhost` frente a `127.0.0.1`. |
| Descubrimiento/preflight del workflow de prueba | **PASS** | `test-automation` listo y sin mutación. |
| Importación/ejecución del workflow de prueba | **FAIL** | Importación API n8n HTTP 401; no se declaró ejecución exitosa. |
| Documentación operativa requerida | **FAIL** | Cuatro documentos ausentes. |
| Backend pytest local en host disponible | **NOT TESTED** | Bloqueo de compatibilidad Python 3.14/`asyncpg`. |
| Resultado global | **NOT READY** | Los defectos de healthcheck e importación n8n requieren corrección y nueva validación. |

## 7. Próximo ciclo recomendado

No se debe sustituir ni etiquetar de nuevo `v1.0.0`. El siguiente ciclo debe crear un candidato de corrección independiente, introducir pruebas de regresión para los dos defectos identificados, completar la documentación faltante y ejecutar de nuevo el pipeline nativo completo. La nueva validación post-publicación debe incluir explícitamente una importación, habilitación, ejecución, deshabilitación y eliminación de `test-automation`, además del comando `AutomationCenter health` con los cinco servicios en estado saludable.

## Referencias

[1] [Release v1.0.0 de Automation Center](https://github.com/POPS-4712/TDR-Assistent-IA/releases/tag/v1.0.0)  
[2] [Run de publicación nativa 32284849538](https://github.com/POPS-4712/TDR-Assistent-IA/actions/runs/32284849538)  
[3] [Informe de Phase 2.15](./PHASE_2_15_CICD_RELEASE_REPORT.md)
