# Guía operativa de providers de credenciales

Automation Center centraliza la conexión de cuentas desde **Accounts** y muestra únicamente el proveedor, la etiqueta de cuenta, los scopes, el estado, la última validación y metadata no sensible. Las claves, tokens, passwords y valores de header se escriben una sola vez en el almacenamiento seguro local y no se devuelven a la interfaz.

## Catálogo y uso

| Provider | Tipo | Datos de conexión | Validación | Uso actual |
|---|---|---|---|---|
| Google | OAuth | Autorización web y scopes del manifest. | Identidad OAuth. | Gmail, Calendar y Google Docs según scopes. |
| Gemini | API key | Etiqueta de cuenta y API key. | Endpoint del provider. | Workflows heredados que usan configuración de entorno. |
| Telegram | Token | Etiqueta de bot y token. | `getMe`. | Workflow Laboral heredado. |
| WhatsApp Cloud API | Estructurado | Etiqueta, token de sistema, Phone Number ID, WABA ID opcional y versión Graph API. | Consulta del Phone Number ID y estado `CONNECTED`. | News; el JSON fuente mantiene variables de entorno hasta una migración explícita. |
| Header Auth | Estructurado | Etiqueta, nombre de header, valor secreto y URL HTTPS pública opcional. | Comprobación local o solicitud HTTPS opcional. | Personal Brand para Gemini mediante `httpHeaderAuth`. |
| PostgreSQL/n8n | Dependencia interna | No se copia ni solicita password en Accounts. | Referencia n8n compatible en backend. | Dedupe e historial en workflows. |

## Conectar WhatsApp Cloud API

En **Accounts**, seleccionar **WhatsApp Cloud API** e introducir una etiqueta local de cuenta, el token de sistema, el Phone Number ID y la versión de Graph API. El WABA ID puede añadirse si el caso operativo lo requiere. La validación consulta el Phone Number ID y exige estado `CONNECTED`; el token se envía como Bearer y nunca se interpreta ni se muestra.

Meta recomienda tokens de sistema para automatizaciones directas y documenta los permisos `business_management`, `whatsapp_business_management` y `whatsapp_business_messaging` para el flujo de token de sistema.[1] [2]

## Conectar Header Auth

Seleccionar **Header Auth**, asignar una etiqueta de cuenta y establecer el nombre y el valor del header. La URL de validación es opcional; si se declara, debe ser HTTPS pública. No se aceptan direcciones locales o privadas para evitar que el backend sea usado como puente hacia servicios internos.

El valor del header se guarda como secreto. La interfaz solo conserva el nombre del header y la URL de validación como metadata visible.

## Conectar Google

Seleccionar **Google** y autorizar los scopes requeridos por el manifest. La página de consentimiento debe declarar los scopes y la solicitud de autorización debe pedir exactamente los necesarios para la automatización. Google recomienda utilizar el alcance más limitado compatible con la operación.[3] [4]

| Automatización | Scopes Google declarados |
|---|---|
| Email Assistant | Gmail modify, Gmail readonly y Calendar. |
| Personal Brand | Google Docs y `drive.file`. |

Cuando el tipo de credencial n8n no sea compatible con el nodo del workflow, Automation Center bloqueará la instalación antes de importarla. La aplicación no intenta transformar automáticamente una credencial Gmail, Calendar o Docs en otra clase n8n.

## Validar, reconectar y desconectar

La acción **Validar** comprueba una cuenta guardada y devuelve `VALID`, `INVALID`, `EXPIRED` o `REAUTH_REQUIRED`. Una cuenta expirada o que requiera reautorización debe reconectarse mediante el flujo OAuth correspondiente. **Desconectar** elimina el secreto local y solicita la eliminación de la credencial n8n administrada por Automation Center; no elimina automatizaciones ni credenciales globales ajenas.

## Instalar una automatización

Antes de importar un workflow, Automation Center evalúa las cuentas activas, scopes, tipos de credencial n8n y variables de entorno declaradas. Si un requisito no se satisface, la instalación se detiene con un mensaje `INSTALLATION BLOCKED: Missing credential: …` y no crea ningún workflow n8n.

Los workflows fuente se mantienen inmutables. Cuando todos los requisitos se cumplen, los mappings se aplican únicamente a la copia recién importada en n8n. Este diseño impide que una conexión de cuenta modifique las automatizaciones existentes del usuario.

## Referencias

[1]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta for Developers — WhatsApp Cloud API Get Started"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/ "Meta for Developers — WhatsApp Access Tokens Guide"
[3]: https://developers.google.com/workspace/drive/api/guides/api-specific-auth "Google Developers — Choose Google Drive API scopes"
[4]: https://developers.google.com/workspace/calendar/api/auth "Google Developers — Choose Google Calendar API scopes"
