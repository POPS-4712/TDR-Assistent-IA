# Phase 2.9 — Providers de credenciales y preparación segura de automatizaciones

**Estado:** **PASS con límites explícitos**  
**Fecha de verificación:** 18 de agosto de 2026  
**Autor:** Manus AI

## Resultado

Phase 2.9 incorpora una capa de cuentas preparada para proveedores reales, sin persistir secretos en PostgreSQL ni enviarlos de vuelta a la interfaz. Se añadieron los providers **WhatsApp Cloud API** y **Header Auth**, se mantuvo el provider OAuth de Google y se reforzó el lifecycle para bloquear una instalación antes de importar un workflow si faltan cuentas, scopes, mapeos n8n compatibles o variables de entorno declaradas.

> **Principio aplicado:** los valores secretos se almacenan exclusivamente en `SecureStore` o en n8n cuando n8n es el propietario de la credencial. La API de Accounts devuelve solamente metadata pública, estado, scopes y marcas de validación.

| Área | Resultado verificado |
|---|---|
| Provider `whatsapp_cloud` | Disponible en el catálogo; exige token, Phone Number ID y versión Graph API; valida contra Meta sin mostrar el token. |
| Provider `header_auth` | Disponible en el catálogo; guarda el valor del header en el almacén seguro; solo permite una URL de validación HTTPS pública y opcional. |
| Google OAuth | Se conserva como provider único; los manifests declaran scopes. El resolver bloquea tipos n8n incompatibles en vez de inventar un payload. |
| API pública de Accounts | No devuelve `n8n_credential_id`, claves, tokens, passwords ni valores de header. |
| Instalación de automatizaciones | El preflight devuelve `INSTALLATION BLOCKED: Missing credential: …` antes de importar a n8n. |
| Copia importada de n8n | El mapping actualiza exclusivamente la copia importada y filtra campos de solo lectura. |
| Perfiles | Se mantuvieron independientes: no contienen, copian ni seleccionan secretos. |

## Cambios implementados

La base de datos incorpora `credential_metadata` y `last_validation` mediante migraciones `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. La metadata contiene únicamente datos no sensibles; los indicadores privados de compatibilidad con n8n se filtran antes de construir respuestas HTTP y nunca contienen un secreto.

El endpoint `POST /api/v1/credentials/structured` recibe una estructura separada entre `secrets` y `metadata`. El endpoint `POST /api/v1/credentials/{id}/validate` devuelve uno de los resultados `VALID`, `INVALID`, `EXPIRED` o `REAUTH_REQUIRED`. La interfaz Accounts ofrece formularios específicos para WhatsApp Cloud API y Header Auth, muestra la última validación, y permite validar, actualizar o desconectar una cuenta sin visualizar el secreto.

| Archivo o componente | Función final |
|---|---|
| `backend/app/services/credentials/structured_providers.py` | Providers WhatsApp Cloud API y Header Auth. |
| `backend/app/services/credentials/manager.py` | Metadata pública, validación, persistencia estructurada y catálogo consistente. |
| `backend/app/services/automations/manager.py` | Preflight de scopes, variables de entorno y compatibilidad n8n; mapping sobre la copia importada. |
| `backend/app/services/n8n/client.py` | Importación y actualización filtradas; errores sin cuerpo de respuesta en logs. |
| `frontend/src/pages/Accounts.tsx` y componentes asociados | Interfaz de conexión, estado y validación de providers estructurados. |
| `automations/news/manifest.yaml` | Requisito migrado de `whatsapp` a `whatsapp_cloud`. |
| `automations/personal-brand/manifest.yaml` | Header Auth y Google Docs declarados con scopes Docs/Drive explícitos. |

## Evidencia de validación

| Comprobación | Resultado |
|---|---:|
| Salud del backend | **PASS** — `healthy` |
| Providers estructurados expuestos por API | **PASS** — `whatsapp_cloud`, `header_auth` |
| Pruebas específicas de providers estructurados y preflight | **PASS** — 6 pruebas |
| Regresión completa del backend | **PASS** — **84 passed**, 8 advertencias de deprecación no bloqueantes |
| Pruebas del frontend | **PASS** — **8 passed** |
| Compilación de producción del frontend | **PASS** |
| Workflow aislado `test-automation` | **PASS** — estado final `discovered` |
| API de cuentas sin campos prohibidos | **PASS** — ninguna cuenta persistida durante la comprobación; contrato cubierto por pruebas unitarias |

Las advertencias de backend proceden de APIs deprecadas de SQLAlchemy y Pydantic, y no corresponden a fallos de esta fase. La compilación frontend emitió una advertencia preexistente de Tailwind sobre `content`; el build finalizó correctamente.

## Preparación de automatizaciones reales

Ninguna automatización real fue instalada, activada, editada o ejecutada durante esta fase. La ausencia deliberada de cuentas reales hace que el estado operativo de las automatizaciones sea **BLOCKED, no FAIL**: el preflight evita la importación hasta que se conecten las cuentas requeridas y exista un mapping compatible en n8n.

| Automatización | Requisitos que el preflight evaluará | Estado de preparación actual |
|---|---|---|
| Email Assistant | Google (Gmail/Calendar scopes), Gemini, PostgreSQL/n8n y variables declaradas. | **BLOCKED** hasta configurar cuentas y runtime. |
| Laboral | PostgreSQL/n8n, Gemini, Telegram, Playwright y variables declaradas. | **BLOCKED** hasta configurar cuentas y runtime. |
| News | PostgreSQL/n8n, Gemini, WhatsApp Cloud API y variables heredadas. | **BLOCKED** hasta conectar y migrar/confirmar runtime. |
| Personal Brand | PostgreSQL/n8n, Header Auth, Google Docs/Drive scopes y `GEMINI_MODEL`. | **BLOCKED** hasta configurar cuentas y runtime. |
| Playwright Jobs | PostgreSQL/n8n y Playwright. | **BLOCKED** hasta configurar runtime interno. |
| Test Automation | No requiere cuenta. | **DISCOVERED** y reservado para regresión aislada. |

## Guía operativa segura

Para conectar WhatsApp Cloud API, se debe usar el formulario de Accounts con una etiqueta de cuenta local, el token de sistema, el Phone Number ID y la versión de Graph API. Meta indica que las integraciones automatizadas usan tokens de sistema y que la cuenta necesita permisos apropiados; el token debe tratarse como una cadena opaca.[1] [2]

Para Header Auth, se debe indicar la cuenta, el nombre del header y su valor. La URL de validación es opcional y, si se utiliza, debe ser HTTPS pública; esto evita que el backend realice solicitudes a servicios locales o redes privadas desde este flujo.

Para Google, se reutiliza una conexión OAuth existente y se solicitan scopes declarados por el manifest. Google recomienda declarar scopes en la configuración de consentimiento y solicitarlos explícitamente para cada sesión, con el alcance mínimo que satisfaga la operación.[3] [4]

Antes de instalar una automatización real, se debe confirmar que las variables de entorno heredadas requeridas por su manifest existen en el runtime n8n. Este requisito se mantiene intencionalmente: Phase 2.9 no reescribe workflows fuente ni migra valores desde variables de entorno a credenciales sin una acción explícita y reversible.

## Límites y decisiones pendientes

El sistema no autoimporta ni duplica credenciales PostgreSQL existentes de n8n, porque eso supondría copiar una contraseña que n8n ya almacena cifrada. La vinculación requiere una referencia compatible y no expone dicha referencia a la interfaz.

El workflow fuente de News todavía usa variables de entorno para la llamada HTTP a WhatsApp. La nueva cuenta WhatsApp Cloud valida y conserva sus datos de manera segura, pero el workflow heredado solo debe migrarse a `httpHeaderAuth` dentro de una **copia importada y revisada**, nunca editando su JSON fuente. Por ello, el preflight mantiene bloqueada la instalación si faltan variables de entorno declaradas.

Durante la auditoría final se detectó un diff local de contenido en `workflows/02-laboral.json`. No fue revertido ni modificado para preservar cambios locales de autoría indeterminada. Debe revisarse por el propietario antes de realizar cualquier commit o despliegue.

## Referencias

[1]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta for Developers — WhatsApp Cloud API Get Started"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/ "Meta for Developers — WhatsApp Access Tokens Guide"
[3]: https://developers.google.com/workspace/drive/api/guides/api-specific-auth "Google Developers — Choose Google Drive API scopes"
[4]: https://developers.google.com/workspace/calendar/api/auth "Google Developers — Choose Google Calendar API scopes"
