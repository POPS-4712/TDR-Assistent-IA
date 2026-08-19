# Email Assistant

AI-powered email management with Gmail integration and Google Calendar.

## Overview

This automation processes incoming emails using AI (Gemini) to classify and take appropriate actions:
- Create calendar events
- Update existing events
- Cancel events
- Create tasks
- Send notifications
- Process security/account emails

## Workflow

The workflow consists of:
1. **Gmail Trigger** - Listens for new emails
2. **Gmail - List Messages** - Fetches unread inbox messages
3. **Webhook - Email Intake** - Alternative entry point
4. **Preparar correo** - Normalizes email data
5. **Excluir spam, promociones y social** - Filters out unwanted categories
6. **Evitar duplicados** - Deduplication using PostgreSQL
7. **Verificar duplicado** - Checks deduplication result
8. **Gemini - Secretary Analysis** - AI classification
9. **Validar JSON Secretary** - Validates AI response
10. **¿Requiere acción?** - Routes to appropriate action
11. **Action handlers** - Create/update/cancel events, tasks, notifications

## Requirements

- Google OAuth2 credentials with Gmail and Calendar scopes
- OpenRouter API key for AI processing
- PostgreSQL connection for deduplication

## Credentials Mapping

| n8n Credential | Provider |
|----------------|----------|
| gmailOAuth2 | google |
| googleCalendarOAuth2Api | google |
| postgres | postgresql |
| openRouterApi | openrouter |

## Source

Based on workflow: `01-email-manager.json`