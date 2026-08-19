# Arquitectura de integración end-to-end

## Visión del sistema

Automation Center se compone de una interfaz React, una API FastAPI, PostgreSQL como almacenamiento de metadatos, n8n como motor interno de workflows y un servicio Playwright para scraping. El usuario opera el producto desde Automation Center; n8n no es una interfaz requerida para el flujo normal.

```text
React
  ↓ API HTTP local
FastAPI
  ├─ CredentialManager → almacén seguro → metadatos de credenciales → credenciales n8n
  ├─ AutomationManager → manifests → workflows JSON → API n8n
  ├─ PostgreSQL → automatizaciones, relaciones de credencial y ejecuciones
  ├─ ProfileManager → contexto de personalización no sensible
  └─ BackupManager → snapshots de metadata filtrados y restore idempotente
       ↓
n8n
  ├─ PostgreSQL / RSS / servicios IA / Google / Telegram / WhatsApp
  └─ Playwright para búsquedas de empleo cuando corresponda
```

## Flujo de credenciales

El flujo previsto es `manifest → resolver de requisitos y scopes → CredentialManager → metadata de Credential → mapping n8n → importación → actualización de la copia importada`. Los secretos se mantienen en el almacén seguro y no deben viajar al frontend ni persistirse en los modelos de perfiles. La metadata de credenciales en PostgreSQL conserva estado, proveedor, configuración pública y referencias internas filtradas; la API de Accounts no devuelve la referencia n8n ni secreto material.

Las automatizaciones reales tienen requisitos distintos; no se exige que los seis proveedores disponibles estén conectados en todas ellas. La matriz auditada identifica Google, Gemini, PostgreSQL, Telegram, WhatsApp, Google Docs y Playwright solo cuando los workflows los referencian.

| Capa | Responsabilidad | Garantía de seguridad |
|---|---|---|
| Frontend | Solicita operaciones contra Automation Center. | No almacena ni recibe secretos. |
| CredentialManager | Mantiene secretos y metadata de conexión. | La suite usa keyring en memoria y vault temporal solo bajo pytest. |
| AutomationManager | Valida manifests, requisitos y mapeos. | No crea credenciales reales durante las validaciones controladas. |
| n8n | Importa, activa y ejecuta workflows. | Debe requerir una clave API local de prueba válida para su Public API. |
| PostgreSQL | Mantiene metadata, relaciones y ejecución. | No debe recibir resultados con secretos. |

## Flujo de instalación y rollback

La instalación usa este orden: localizar manifest, validar workflow, comprobar dependencias, resolver cuentas, scopes, tipo n8n y variables de entorno, importar en n8n, asignar referencias únicamente a la copia importada, crear metadata y marcar `installed`. Si falla después de la importación, `AutomationManager` intenta borrar el workflow n8n creado y marca la automatización como `error`. Si falta un requisito, devuelve `INSTALLATION BLOCKED: Missing credential: …` antes de importar.

Durante la validación de esta fase se separaron las dependencias de infraestructura (`postgresql`, `playwright`, `google-oauth2`) de las dependencias entre automatizaciones. Las primeras no se buscan como filas de automatización: PostgreSQL se necesita para el propio servicio, Playwright se valida por su salud y Google OAuth se valida como requisito de credencial. Las dependencias entre automatizaciones siguen validándose contra metadata instalada.

## Ejecución y tracking

El cliente n8n dispone de importación, activación, desactivación, lectura de ejecución y ejecución manual. El contrato de ejecución de Automation Center contempla `automation_id`, `workflow_id`, `n8n_execution_id`, estado, marcas temporales, error y resultado saneado. El 18 de agosto de 2026, el workflow aislado `test-automation` se importó, activó y ejecutó de forma real mediante su webhook local; después se desactivó y eliminó. Esta validación confirma el lifecycle de n8n, pero no sustituye una prueba funcional de las automatizaciones reales ni una validación específica de sincronización de todos los resultados de ejecución.

## Fallos controlados

Se ejecutaron pruebas de credenciales ausentes para las automatizaciones reales. Todas detuvieron el proceso antes de la importación a n8n y devolvieron un error claro de requisitos faltantes. No se invocaron APIs externas, Playwright remoto, correo, Telegram, WhatsApp ni Google.

La automatización de prueba, que no exige credenciales ni llamadas externas, completó la importación, activación, webhook real, desactivación y eliminación mediante la Public API de n8n. Su estado final se redescubrió como `discovered`; no quedó un workflow de prueba instalado o activo.

## Restart y persistencia

Se reconstruyeron las imágenes backend y frontend, se recreó el backend y se verificó su salud junto con PostgreSQL y n8n. La API mantuvo seis metadatos de automatización y el catálogo de perfiles existente. El lifecycle posterior de `test-automation` confirmó además una importación, activación y eliminación válidas contra la Public API de n8n; al terminar se redescubrió como `discovered`.

## Backup y restore de metadata

`BackupManager` expone exportación, validación y restore mediante `/api/v1/backup/export`, `/api/v1/backup/validate` y `/api/v1/backup/restore`. El bundle contiene metadata de automatizaciones, credenciales sin secretos, settings filtrados, templates, perfiles y manifests sanitizados. Excluye ID de workflow y activación de n8n, referencias n8n de credenciales, historiales de ejecución y campos cuyo nombre indique material sensible.

La restauración es `dry_run=true` por defecto. En modo persistente inserta únicamente registros que no existen y deja las automatizaciones como `discovered` y las credenciales como `requires_reauth`. Se verificaron exportación, validación, escaneo de campos sensibles, restore en seco e idempotencia usando un perfil temporal que fue eliminado al terminar.

## Phase 2.9: providers estructurados y Accounts

Phase 2.9 añade `whatsapp_cloud` y `header_auth` como providers estructurados. Los valores `access_token` y `header_value` se guardan únicamente en `SecureStore`; PostgreSQL conserva Phone Number ID, WABA ID opcional, versión API, nombre de header, URL de validación opcional y marcas temporales. El endpoint de validación devuelve estados `VALID`, `INVALID`, `EXPIRED` o `REAUTH_REQUIRED` sin revelar el valor validado.

Las cuentas Google conservan un único flujo OAuth. Los manifests declaran scopes y el preflight bloquea un tipo n8n incompatible en vez de intentar transformar una credencial de Gmail, Calendar o Docs sin un contrato confirmado. PostgreSQL continúa como dependencia interna de n8n y no se copia su contraseña a Automation Center.

## Modelo de seguridad

El análisis estático de rutas backend, frontend, tests, automatizaciones, documentación y configuración no encontró patrones de claves de proveedor literales. Las coincidencias saneadas quedaron limitadas a fixtures de prueba y cabeceras simuladas. La revisión no imprime valores potenciales.

La clave temporal creada por pytest existe solo en el directorio temporal de la sesión; el contenedor de producción se verificó sin `/etc/automation-center/system.key` ni vault generados por las pruebas. Las pruebas no modificaron `N8N_ENCRYPTION_KEY`, `N8N_API_KEY`, credenciales reales, `assistant_processed_items` ni tablas internas de n8n.

## Límites actuales

La Public API de n8n está validada para el workflow de prueba con una clave local de API creada en n8n y cargada desde el entorno Docker. La clave tiene ciclo de vida propio y debe renovarse localmente antes de expirar, sin copiar su valor al repositorio o a documentación.

Las automatizaciones reales permanecen sin ejecutar por diseño: sus cuentas y permisos no se introdujeron en la validación E2E. News utiliza la WhatsApp Cloud API de Meta mediante variables de entorno heredadas, pero el provider gestionado `whatsapp_cloud` ya permite conectar, validar y mantener de forma segura el token, Phone Number ID y versión Graph API. La migración del workflow legado a `httpHeaderAuth` sigue pendiente y debe aplicarse solo sobre una copia importada y revisada, nunca sobre el JSON fuente.
