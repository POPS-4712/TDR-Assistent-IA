# Matriz de auditoría de credenciales

**Fecha:** 18 de agosto de 2026  
**Fuente:** Análisis automático de 10 copias de workflow bajo `workflows/*.json` y `automations/*/workflow.json`. El inventario detallado sin valores sensibles está disponible en `docs/WORKFLOW_CREDENTIAL_INVENTORY.json`.

> La auditoría registra exclusivamente tipos, nodos, nombres de campos y hosts. No exporta nombres reales de credencial, tokens, claves API ni valores de parámetros.

## Matriz por automatización

| Automatización | Provider | Tipo de credencial o mecanismo observado | Obligatorio | Soportado hoy | Gestionado hoy | Externo | Estado |
|---|---|---|---:|---:|---:|---:|---|
| Email Assistant | Google | `gmailOAuth2` y `googleCalendarOAuth2Api` en Gmail y Calendar. | Sí | Sí, parcialmente | Sí, mediante OAuth único | No | Requiere scopes de Gmail y Calendar explícitos. |
| Email Assistant | Gemini | HTTP Request a `generativelanguage.googleapis.com`; sin ref. n8n. | Sí | Sí | Parcialmente | Sí | El workflow consume una variable de entorno; requiere resolver controlado antes de instalar. |
| Email Assistant | PostgreSQL | `postgres` n8n en nodo de deduplicación. | Sí | No como provider AC | No | Sí, n8n interno | Debe reutilizar credencial cifrada existente de n8n; no almacenar password en AC. |
| Laboral | PostgreSQL | `postgres` n8n en deduplicación. | Sí | No como provider AC | No | Sí, n8n interno | Requiere mapping a credencial n8n existente. |
| Laboral | Gemini | HTTP Request a Gemini; sin ref. n8n. | Sí | Sí | Parcialmente | Sí | Requiere resolver seguro de la configuración actual. |
| Laboral | Telegram | HTTP Request a `api.telegram.org`; sin ref. n8n. | Sí | Sí | Parcialmente | Sí | El provider existe, pero el workflow actual usa su propia configuración HTTP. |
| News | PostgreSQL | `postgres` n8n en deduplicación. | Sí | No como provider AC | No | Sí, n8n interno | Reutilizar credencial n8n cifrada; no duplicar password. |
| News | Gemini | HTTP Request a Gemini; sin ref. n8n. | Sí | Sí | Parcialmente | Sí | Requiere resolución antes de importar. |
| News | WhatsApp Cloud API | HTTP Request a `graph.facebook.com/.../messages`. | Sí | No | No | Sí | **Nuevo provider requerido**; token, Phone Number ID, WABA ID y versión API. |
| Personal Brand | PostgreSQL | `postgres` n8n en deduplicación. | Sí | No como provider AC | No | Sí, n8n interno | Reutilizar credencial n8n cifrada existente. |
| Personal Brand | Header Auth | `httpHeaderAuth` en solicitudes HTTP de Gemini. | Sí | No | No | Sí | **Nuevo provider requerido**; nombre de header como metadata y valor solo en secure store. |
| Personal Brand | Google Docs | `googleDocsOAuth2Api` en creación y escritura de borradores. | Sí | Sí, parcialmente | Sí, mediante OAuth único | No | Reutilizar Google OAuth, solicitando scopes Docs/Drive según el manifest. |
| Playwright Jobs | PostgreSQL | `postgres` n8n para historial. | Sí | No como provider AC | No | Sí, n8n interno | Candidato de instalación inicial si la credencial PostgreSQL n8n ya existe. |
| Test Automation | Ninguno | Webhook y Set. | No | N/A | N/A | No | Validado E2E y reservado para regresión aislada. |

## Hallazgos verificables

Los workflows fuente y sus copias importables son pares auditados, por lo que la matriz se expresa por automatización y no duplica el requisito por archivo. El inventario detectó 74 nodos que usan una referencia de credencial o un endpoint de proveedor relevante. El resultado no clasifica feeds RSS públicos como una credencial Google.

El nodo **News → WhatsApp - Noticias** apunta a `graph.facebook.com`, por lo que corresponde a la **WhatsApp Cloud API de Meta**. Meta documenta que una integración automatizada debe usar un token de sistema, un Phone Number ID y, cuando procede, un WhatsApp Business Account ID; los tokens se transmiten como Bearer y deben tratarse como cadenas opacas.[1] [2]

Los nodos Google Docs de Personal Brand usan `googleDocsOAuth2Api`; no justifican un sistema OAuth distinto. La solución correcta es conservar un solo provider Google y resolver la compatibilidad con los scopes y el tipo de credencial n8n requeridos por cada nodo.

## Decisiones de diseño que condicionan Phase 2.9

La metadata pública de una cuenta no debe exponer `n8n_credential_id`; esa referencia queda en la capa interna de backend. Las credenciales PostgreSQL existentes siguen bajo el almacenamiento cifrado de n8n. La comprobación de readiness debe distinguir claramente una cuenta administrada por Automation Center, una dependencia externa n8n y un requisito de entorno aún no migrado, bloqueando la instalación con un mensaje de requisito faltante y sin modificar workflows fuente.

## Referencias

[1]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta for Developers — WhatsApp Cloud API Get Started"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/ "Meta for Developers — WhatsApp Access Tokens Guide"
