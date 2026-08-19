# Phase 2.10 — Matriz de auditoría de workflows

> Generada desde copias en `automations/*/workflow.json`; los campos secretos no se leen ni se muestran.

## email-assistant

| Nodo | Tipo n8n | Tipos de credencial | Provider detectado | Variables de entorno | Dependencia interna | Host externo |
|---|---|---|---|---|---|---|
| Gmail Trigger | n8n-nodes-base.gmailTrigger | gmailOAuth2 | google |  |  | — |
| Gmail - Listar mensajes | n8n-nodes-base.gmail | gmailOAuth2 | google |  |  | — |
| Evitar duplicados | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Secretary Analysis | n8n-nodes-base.httpRequest |  | gemini | GEMINI_API_KEY, GEMINI_MODEL, TZ |  | generativelanguage.googleapis.com |
| Validar evento nuevo | n8n-nodes-base.code |  |  | TZ | playwright | — |
| Google Calendar - Crear evento | n8n-nodes-base.googleCalendar | googleCalendarOAuth2Api | google |  |  | — |
| Google Calendar - Buscar eventos | n8n-nodes-base.googleCalendar | googleCalendarOAuth2Api | google |  |  | — |
| Procesar actualizar evento | n8n-nodes-base.code |  |  | TZ | playwright | — |
| Google Calendar - Actualizar evento | n8n-nodes-base.googleCalendar | googleCalendarOAuth2Api | google |  |  | — |
| Google Calendar - Buscar para cancelar | n8n-nodes-base.googleCalendar | googleCalendarOAuth2Api | google |  |  | — |
| Google Calendar - Cancelar evento | n8n-nodes-base.googleCalendar | googleCalendarOAuth2Api | google |  |  | — |

## laboral

| Nodo | Tipo n8n | Tipos de credencial | Provider detectado | Variables de entorno | Dependencia interna | Host externo |
|---|---|---|---|---|---|---|
| Cada maÃ±ana - Playwright | n8n-nodes-base.cron |  |  |  | playwright | — |
| Webhook - Playwright Jobs | n8n-nodes-base.webhook |  |  |  | playwright | — |
| Preparar solicitudes Playwright | n8n-nodes-base.code |  |  | PLAYWRIGHT_BASE_URL | playwright | — |
| HTTP - Ejecutar scraper Playwright | n8n-nodes-base.httpRequest |  |  |  | playwright | — |
| Evitar duplicados PostgreSQL | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Resumir oferta | n8n-nodes-base.httpRequest |  | gemini | GEMINI_API_KEY, GEMINI_MODEL |  | generativelanguage.googleapis.com |
| Telegram - Enviar oferta | n8n-nodes-base.httpRequest |  | telegram | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |  | api.telegram.org |
| Telegram - Sin ofertas | n8n-nodes-base.httpRequest |  | telegram | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |  | api.telegram.org |
| Responder webhook Playwright | n8n-nodes-base.respondToWebhook |  |  |  | playwright | — |

## news

| Nodo | Tipo n8n | Tipos de credencial | Provider detectado | Variables de entorno | Dependencia interna | Host externo |
|---|---|---|---|---|---|---|
| Eliminar duplicados | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Resumir noticia | n8n-nodes-base.httpRequest |  | gemini | GEMINI_API_KEY, GEMINI_MODEL |  | generativelanguage.googleapis.com |
| WhatsApp - Noticias | n8n-nodes-base.httpRequest |  | whatsapp_cloud | WHATSAPP_ACCESS_TOKEN, WHATSAPP_API_VERSION, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_RECIPIENT |  | graph.facebook.com |

## personal-brand

| Nodo | Tipo n8n | Tipos de credencial | Provider detectado | Variables de entorno | Dependencia interna | Host externo |
|---|---|---|---|---|---|---|
| Evitar duplicados | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Borrador LinkedIn | n8n-nodes-base.httpRequest | httpHeaderAuth | gemini, header_auth |  |  | generativelanguage.googleapis.com |
| Google Docs - Crear borrador | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Google Docs - Escribir borrador | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Evitar duplicados1 | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Borrador LinkedIn1 | n8n-nodes-base.httpRequest | httpHeaderAuth | gemini, header_auth |  |  | generativelanguage.googleapis.com |
| Google Docs - Crear borrador1 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Google Docs - Escribir borrador1 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Evitar duplicados2 | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Borrador LinkedIn2 | n8n-nodes-base.httpRequest | httpHeaderAuth | gemini, header_auth |  |  | generativelanguage.googleapis.com |
| Google Docs - Crear borrador2 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Google Docs - Escribir borrador2 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Evitar duplicados3 | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Borrador LinkedIn3 | n8n-nodes-base.httpRequest | httpHeaderAuth | gemini, header_auth |  |  | generativelanguage.googleapis.com |
| Google Docs - Crear borrador3 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Google Docs - Escribir borrador3 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Evitar duplicados4 | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |
| Gemini - Borrador LinkedIn4 | n8n-nodes-base.httpRequest | httpHeaderAuth | gemini, header_auth |  |  | generativelanguage.googleapis.com |
| Google Docs - Crear borrador4 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |
| Google Docs - Escribir borrador4 | n8n-nodes-base.googleDocs | googleDocsOAuth2Api | google |  |  | — |

## playwright-jobs

| Nodo | Tipo n8n | Tipos de credencial | Provider detectado | Variables de entorno | Dependencia interna | Host externo |
|---|---|---|---|---|---|---|
| Cada maÃ±ana - Playwright | n8n-nodes-base.cron |  |  |  | playwright | — |
| Webhook - Playwright Jobs | n8n-nodes-base.webhook |  |  |  | playwright | — |
| Preparar solicitudes Playwright | n8n-nodes-base.code |  |  | PLAYWRIGHT_BASE_URL | playwright | — |
| HTTP - Ejecutar scraper Playwright | n8n-nodes-base.httpRequest |  |  |  | playwright | — |
| HistÃ³rico PostgreSQL - SÃ³lo nuevos | n8n-nodes-base.postgres | postgres | postgresql |  | postgresql | — |

## Integridad de copias

| Automatización | Copia y fuente con mismo hash |
|---|---|
| email-assistant | False |
| laboral | True |
| news | True |
| personal-brand | True |
| playwright-jobs | True |
