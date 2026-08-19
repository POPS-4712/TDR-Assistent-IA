# Informe de implementación y verificación — Phase 2.11

**Proyecto:** Automation Center / TDR-Assistent-IA  
**Fecha de verificación:** 19 de agosto de 2026  
**Ámbito:** resolución de cuentas, mapeo de credenciales n8n, instalación segura, ejecución explícita, interfaz automática y validación Docker local.

> **Resultado global:** Phase 2.11 está implementada, publicada y verificada en el entorno local. El sistema distingue entre automatizaciones **Ready**, bloqueos de cuentas reales y errores operativos, sin importar workflows ni exponer secretos durante el preflight.

## 1. Capacidades implementadas

La capa de automatizaciones incorpora un resolver determinista de cuentas. Para cada requisito del manifest, comprueba estado, scopes declarados, compatibilidad con el tipo exacto de credencial n8n y disponibilidad de los prerrequisitos locales. La respuesta pública contiene únicamente identificadores funcionales de proveedor y cuenta, estado, scopes requeridos/concedidos, compatibilidad y requisitos faltantes. No incluye IDs internos de n8n ni valores de secretos.

| Área | Implementación validada | Garantía operativa |
|---|---|---|
| Resolución de cuentas | `AccountResolver` y endpoint `GET /api/v1/automations/{id}/accounts`. | Muestra compatibilidad y bloqueos sin revelar referencias internas ni valores sensibles. |
| Preflight | `POST /api/v1/automations/preflight` y `POST /api/v1/automations/{id}/preflight`. | Es de solo lectura respecto de workflows; informa `mutations_applied: false`. |
| Instalación | Preflight obligatorio antes de importación; mapeo exacto en la copia importada; rollback tras fallo. | No se importan workflows fuente. Un fallo posterior a importación elimina la copia n8n creada. |
| Reintentos | Estado transitorio `installing` y protección de reintento. | Reinstalar una copia ya instalada no la degrada a `error`. |
| Ejecución explícita | `POST /api/v1/automations/{id}/run` y actualización `GET /api/v1/automations/executions/{id}`. | Solo permite ejecutar una copia habilitada y prevalidada. |
| Perfil | Perfil activo o `profile_id` opcional; contexto derivado por capacidad. | Se transmite solo configuración derivada de automatización, nunca credenciales. |
| Seguimiento | Registros con estado, IDs, `profile_id`, tiempo y error seguro. | La interfaz omite payloads de runtime y resultados potencialmente sensibles. |
| Revalidación | Cambios en cuentas o perfiles solicitan silenciosamente el preflight global. | El paso de `blocked` a `ready` se refleja automáticamente al recargar la vista. |

## 2. Flujo seguro de instalación y ejecución

La instalación ya no puede saltarse el preflight formal. Primero se valida el manifest, el JSON del workflow, dependencias, runtime local, cuentas, scopes y mapeos de tipos n8n. Solo cuando todos los controles están en estado `ready`, se valida otra vez la copia del workflow, se importa en n8n y se inyectan los mapeos exclusivamente sobre la copia importada. Ante cualquier fallo tras la importación, el sistema intenta eliminar la copia creada y conserva un estado seguro y explicable.

La ejecución requiere que la automatización esté habilitada y que el preflight final siga en estado `ready`. Si existe un perfil activo o se indica un `profile_id`, se incorpora únicamente su bloque de defaults derivado para la capacidad adecuada: correo, noticias, empleo o marca personal. El seguimiento registra `queued`, `running`, `completed`, `failed` o `cancelled`, sin almacenar ni mostrar datos de ejecución ni secretos.

## 3. Interfaz y comportamiento automático

La página `http://localhost:3001/automations` ejecuta el preflight global antes de leer el listado persistido. De esta manera, no existe una carrera en la primera carga y no se necesita pulsar **Discover**. El control disponible es **Refresh checks**, que repite la comprobación de solo lectura.

| Estado visual | Comportamiento de tarjeta |
|---|---|
| **Ready to install** | Se habilita únicamente `Install`. |
| **Installing** | Se muestran pasos de progreso sin habilitar acciones incompatibles. |
| **Blocked** | Se presentan cuentas, tipos n8n, requisitos de entorno o scopes pendientes; la instalación queda deshabilitada y se muestra `Connect accounts`. |
| **Installed / Disabled** | Se ofrecen acciones permitidas de enable, disable o uninstall. |
| **Enabled** | Se ofrece `Run` explícito y `Disable`. |

La interfaz de ejecuciones muestra estado, perfil, duración, IDs de seguimiento y errores seguros. Por diseño, el panel aclara que no expone payloads de runtime. Las tarjetas también representan los requisitos de runtime sin tratarlos como credenciales.

## 4. Correcciones complementarias realizadas

La validación de Playwright usaba antes una variable que solo estaba disponible para n8n. Se corrigió el backend para usar `PLAYWRIGHT_BASE_URL` cuando exista y, en su ausencia, `PLAYWRIGHT_API_URL`. La comprobación consulta exclusivamente el endpoint local `/health` de Playwright. Docker ahora suministra una URL interna no sensible para el backend, por lo que las automatizaciones que usan Playwright ya no se bloquean falsamente por el runtime.

También se eliminó la referencia a **InfoJobs** del manifest y de la interfaz de la automatización laboral. La descripción actual declara únicamente LinkedIn. Las etiquetas no operativas se leen dinámicamente desde el manifest al listar automatizaciones; esta sincronización evita cambiar estados, mappings o workflows durante el preflight.

## 5. Verificaciones ejecutadas

| Comprobación | Resultado verificable |
|---|---:|
| Regresión backend completa | **94 passed, 0 failed** |
| Compilación de frontend | **PASS** |
| Suite frontend | **11 passed, 0 failed** |
| Ciclo E2E aislado | **PASS**: install → enable → webhook → disable → uninstall; todas las respuestas 200 |
| Backend | `healthy` |
| Frontend `/automations` | HTTP 200, con `Cache-Control: no-store` |
| Playwright local | `/health` → `ok` |
| Preflight global | 6 automatizaciones, `mutations_applied: false` |
| Automatización de prueba | Preflight `ready`; estado persistido final `discovered` |
| Automatizaciones reales | 5 en `blocked` por requisitos de cuentas reales |
| Verificación visual | Tarjetas `Ready`/`Blocked`, requisitos visibles, sin valores de secretos y sin referencia a InfoJobs |

El ciclo E2E se ejecutó exclusivamente sobre `test-automation`. En un primer intento se detectó una copia de prueba residual; su limpieza mostró que una reinstalación repetida podía marcar indebidamente una copia existente como `error`. Se corrigió ese comportamiento, se añadió una prueba de regresión y se repitió el ciclo completo con resultado PASS. El estado final se restauró a `discovered` mediante el preflight automático.

## 6. Estado real de dependencias

Los siguientes bloqueos son **reales** y no se han eludido. No se importó ni ejecutó ninguna automatización de producción.

| Automatización | Estado | Bloqueos actuales verificados |
|---|---|---|
| `test-automation` | `ready` / `discovered` | Ninguno; preparada únicamente para validación aislada. |
| `playwright-jobs` | `blocked` | Cuenta PostgreSQL y mapping n8n `postgres`. El servicio Playwright local está disponible. |
| `laboral` | `blocked` | PostgreSQL, Gemini y Telegram; sus mappings y variables de cuenta correspondientes. |
| `news` | `blocked` | PostgreSQL, Gemini y WhatsApp Cloud API; variables de cuenta requeridas. |
| `personal-brand` | `blocked` | PostgreSQL, Header Auth/Gemini y Google OAuth con mapping n8n compatible. |
| `email-assistant` | `blocked` | Google OAuth para Gmail/Calendar, Gemini y PostgreSQL con mappings compatibles. |

Los nombres de variables de entorno que aparecen como requisito son **etiquetas de configuración**; no se devuelven ni registran sus valores. La configuración de cuentas reales continúa siendo el único paso inevitable para desbloquear esas automatizaciones.

## 7. Archivos principales modificados

| Área | Archivos representativos |
|---|---|
| Backend | `backend/app/services/automations/account_resolver.py`, `manager.py`, `api/routes/automations.py` |
| Backend: pruebas | `backend/tests/test_account_resolver.py`, `backend/tests/test_automation_manager.py`, `backend/requirements.txt` |
| Frontend | `frontend/src/hooks/useAutomations.ts`, `useCredentials.ts`, `contexts/ProfileContext.tsx` |
| Frontend: UI | `components/automations/AutomationCard.tsx`, `pages/Automations.tsx`, `pages/Executions.tsx` |
| Frontend: contratos y pruebas | `frontend/src/types/index.ts`, `api/automations.ts`, `api/automations.test.ts` |
| Runtime local | `docker-compose.yml`, `automations/laboral/manifest.yaml` |

## 8. Límites y siguiente operación necesaria

La plataforma está lista para desbloquear automatizaciones automáticamente, pero no puede crear ni autorizar cuentas externas sin datos reales del propietario. Para pasar de `blocked` a `ready`, se deben registrar las cuentas en `/accounts` con sus credenciales y scopes reales. Cada operación de conexión, validación, renovación o revocación dispara el preflight global desde la interfaz. Los cambios de perfil siguen el mismo patrón.

No se hizo ninguna afirmación de prueba sobre credenciales externas, OAuth real, WhatsApp, Gemini, Telegram o Google, porque esas cuentas no están configuradas. Su estado es **BLOCKED**, no PASS ni NOT TESTED.

---

**Autor:** Manus AI  
**Entorno verificado:** Docker local en Windows, proyecto `TDR-Assistent-IA`.
