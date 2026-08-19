# Auditoría de compatibilidad de credenciales y flujos

**Fecha:** 18 de agosto de 2026  
**Propósito:** Consolidar los requisitos reales observados en los workflows locales antes de conectar cuentas o realizar importaciones de automatizaciones reales.

## Principio operativo

El `CredentialManager` debe gestionar la **metadata y los secretos de proveedor** que sean necesarios para instalar una automatización. Cada manifest declara los requisitos y el `credential_mapping` debe apuntar solo a una clave de proveedor compatible. La instalación se detiene antes de importar a n8n si un requisito no está disponible; no debe inventar credenciales ni sobrescribir el workflow fuente.

| Automatización | Integraciones observadas | Estado de mapping | Acción de bajo riesgo |
|---|---|---|---|
| Email Assistant | Google, Gemini, PostgreSQL | Declarado por manifest; depende de conexiones existentes. | Conectar solo cuentas de prueba o autorizar explícitamente las productivas. |
| Laboral | PostgreSQL, Gemini, Telegram, Playwright | Requisitos declarados; Playwright es infraestructura, no una credencial n8n. | Validar health de Playwright y crear mappings únicamente si existen las conexiones. |
| News | PostgreSQL, Gemini, **WhatsApp Cloud API de Meta** | PostgreSQL mapeado; Gemini y WhatsApp se consumen por variables de entorno. | Añadir un proveedor WhatsApp aditivo antes de pretender gestionar ese token desde la aplicación. |
| Personal Brand | PostgreSQL, Gemini, Google/Google Docs, header auth | Requiere revisar el mapping formal de Google Docs y autenticación de cabecera. | Añadir metadatos de requisitos sin modificar el JSON fuente. |
| Playwright Jobs | PostgreSQL, Playwright | PostgreSQL como conexión; Playwright como dependencia de servicio. | No crear proveedor Playwright si solo se requiere comprobar la salud del servicio. |
| Test Automation | Ninguno | No requiere mapping. | Se usa únicamente para validación del lifecycle E2E. |

## Hallazgo específico: News

La auditoría del workflow `automations/news/workflow.json` identificó dos nodos HTTP. El primero llama a Gemini mediante `generativelanguage.googleapis.com`; el segundo llama a `graph.facebook.com/.../messages`. Por su endpoint, la salida de mensajería corresponde a **WhatsApp Cloud API de Meta**. El manifest ya declara `provider: whatsapp` y conserva las variables de entorno necesarias hasta que exista un adaptador gestionado.

| Requisito News | Fuente de configuración actual | Tratamiento recomendado |
|---|---|---|
| PostgreSQL | Credencial y mapping n8n. | Mantener como conexión gestionada. |
| Gemini | Variable de entorno para el nodo HTTP. | Mantener como requisito `gemini`; no incluir su clave en backups. |
| WhatsApp Cloud API | Variables de entorno: token de acceso, teléfono, destinatario y versión API. | Modelar como proveedor `whatsapp` que guarde secreto fuera de PostgreSQL y exponga solo metadata. |

## Integración recomendada para WhatsApp

La incorporación debe ser **aditiva**: un proveedor `whatsapp` en el gestor de credenciales, almacenamiento de secreto en el almacén seguro existente, metadata no sensible en PostgreSQL y una asociación explícita de automatización a credencial. La migración no debe copiar tokens existentes de variables de entorno ni cambiar el workflow News automáticamente. Una futura interfaz puede permitir registrar una conexión WhatsApp nueva, probarla de manera opt-in y, solo entonces, ofrecer al usuario una migración controlada.

> No se deben guardar tokens de WhatsApp, claves de Gemini ni material OAuth en manifests, perfiles, backups o logs. Las copias de seguridad de metadata los rechazan por diseño.

## Estado de validación

| Control | Resultado |
|---|---:|
| Workflows fuente preservados | **PASS** |
| Manifests de inventario disponibles | **PASS** |
| News identificado como WhatsApp Cloud API | **PASS** |
| Importación de automatizaciones reales | **NOT TESTED** por diseño |
| Conexión de cuentas reales | **NOT CONNECTED** por diseño |
| Lifecycle con workflow sin credenciales | **PASS** mediante `test-automation` |
