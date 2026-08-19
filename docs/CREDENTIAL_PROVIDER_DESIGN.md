# Diseño de providers y readiness de credenciales

## Principios

La ampliación conserva el `CredentialManager`, el almacén seguro y los workflows fuente. Las credenciales mantienen esta separación: **secretos** exclusivamente en `SecureStore` o en el almacén cifrado propio de n8n; **metadata no sensible** en PostgreSQL; y **respuestas públicas** sin tokens, claves, passwords, valores de header ni referencias internas de n8n.

| Capa | Puede conservar | No puede conservar |
|---|---|---|
| SecureStore | Tokens, API keys y valores de header. | Metadata funcional que deba mostrarse en la UI. |
| PostgreSQL | Provider, cuenta, scopes, IDs públicos, versión API, estado y última validación. | Token, API key, password, refresh token o valor de header. |
| Frontend | Provider, estado, cuenta, scopes, campos de configuración no sensibles y última validación. | Secretos y `n8n_credential_id`. |
| Backup | Metadata filtrada con `requires_reauth`. | Todo secreto y referencia remota que no sea portable. |

## Providers a incorporar

| Provider | Tipo | Secreto en secure store | Metadata pública | Validación |
|---|---|---|---|---|
| `whatsapp_cloud` | Token estructurado | `access_token`. | `phone_number_id`, `waba_id` opcional, `api_version`, cuenta y última validación. | `GET /{PHONE_NUMBER_ID}?fields=id,status` contra Graph API con Bearer token. |
| `header_auth` | Secreto estructurado | `header_value`. | `header_name`, `validation_url` opcional, cuenta y última validación. | Solicitud HTTPS únicamente cuando existe `validation_url` permitida; en otro caso, comprobación local de presencia. |
| `n8n_internal` | Referencia externa | Ninguno. | Tipo n8n, ID interno no expuesto y nombre de cuenta. | Comprobación backend contra la Public API de n8n; n8n conserva el secreto cifrado. |
| `google` | OAuth reutilizado | Access y refresh token existentes. | Scopes, cuenta, vencimiento y última validación. | Llamada OAuth existente y comprobación de scopes requeridos. |

Meta requiere para la automatización WhatsApp Cloud un token Bearer de sistema, un Phone Number ID, versión de Graph API y, cuando se necesita administrar los números de una cuenta, un WABA ID. El provider no interpreta el token ni lo presenta a la interfaz.[1] [2]

## Estados y contratos

El endpoint `POST /api/v1/credentials/{id}/validate` devolverá una respuesta no sensible con estado de resultado: `VALID`, `INVALID`, `EXPIRED` o `REAUTH_REQUIRED`. La metadata persistente queda normalizada a los estados internos existentes (`active`, `error`, `expired`, `reauth_required`, `revoked`) y añade la marca temporal de última validación.

La creación de secret providers usa un endpoint estructurado distinto de los endpoints heredados de API key y token. Su payload admite campos de configuración no secretos por separado, de forma que solamente los valores marcados como secreto llegan a `SecureStore` y nunca se reemiten en una respuesta.

## Resolución antes de importar

El lifecycle de instalación se refuerza con esta secuencia:

```text
manifest → requisitos y scopes → resolver de credenciales → validación de estado
→ comprobación de tipo n8n → importación → inyección de referencias n8n → activación explícita
```

El resolver devuelve un diagnóstico por requisito. Si faltan una cuenta, scopes, un tipo de credencial n8n compatible o una credencial interna existente, la instalación se detiene antes de la importación con `INSTALLATION BLOCKED: Missing credential: <provider>`. Nunca intenta generar tokens, migrar variables de entorno ni modificar un workflow fuente.

La inyección se limita a la **copia recién importada** en n8n: actualiza los objetos `node.credentials` para los tipos declarados por el manifest. La importación no toca los JSON bajo `workflows/` ni `automations/*/workflow.json`.

## Google y Google Docs

Google Docs reutiliza el único provider OAuth de Google. El manifest expresará sus scopes por automatización y el resolver exigirá su presencia antes de instalar. Los scopes de Docs, Drive, Gmail y Calendar se solicitan de manera explícita y con el menor alcance que el workflow permita. Google recomienda declarar los scopes tanto en la pantalla de consentimiento como en la solicitud de autorización y elegir el alcance más restringido posible.[3] [4]

La creación automática de diferentes credenciales n8n Google se limita a tipos de payload confirmados. Cuando el tipo existente de n8n no sea compatible con el tipo que demanda un nodo (`gmailOAuth2`, `googleCalendarOAuth2Api` o `googleDocsOAuth2Api`), el resolver reportará `REQUIRES_USER_CREDENTIAL` en vez de inventar un payload n8n.

## PostgreSQL y perfiles

PostgreSQL se trata como dependencia interna de n8n. La aplicación puede registrar una referencia de credencial n8n sin copiar su password, pero no construirá una contraseña nueva. Los perfiles siguen siendo independientes: solo contienen parámetros de personalización y configuraciones por automatización; no seleccionan, copian ni poseen secretos.

## Referencias

[1]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta for Developers — WhatsApp Cloud API Get Started"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/ "Meta for Developers — WhatsApp Access Tokens Guide"
[3]: https://developers.google.com/workspace/drive/api/guides/api-specific-auth "Google Developers — Choose Google Drive API scopes"
[4]: https://developers.google.com/workspace/calendar/api/auth "Google Developers — Choose Google Calendar API scopes"
