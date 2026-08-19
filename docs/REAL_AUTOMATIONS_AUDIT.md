# Real Automations Audit

Generated: 2026-08-18
Phase: 2.8 - End-to-End Integration & Real Automations

---

## Summary

| Workflow ID | Name | Status | Credentials Required | PostgreSQL | Playwright | AI Provider |
|-------------|------|--------|---------------------|------------|------------|-------------|
| 01-email-manager | AI Email Secretary | Active | Google OAuth2 (Gmail, Calendar), Gemini API | ✅ | ❌ | Gemini |
| 02-laboral | AI Personal Assistant - Laboral | Active | PostgreSQL, Gemini API, Telegram Bot | ✅ | ✅ | Gemini |
| 03-news | AI Personal Assistant - News | Active | PostgreSQL, Gemini API, WhatsApp API | ✅ | ❌ | Gemini |
| 04-personal-brand | AI Personal Assistant - Personal Brand | Active | PostgreSQL, Gemini API, Google Docs OAuth2 | ✅ | ❌ | Gemini |
| 05-playwright-jobs | AI Personal Assistant - Playwright Jobs | Active | PostgreSQL | ✅ | ✅ | ❌ |

---

## 01-email-manager.json — AI Email Secretary

### Basic Information
- **ID**: 01-email-manager
- **Name**: AI Email Secretary
- **Source File**: workflows/01-email-manager.json
- **Manifest**: automations/email-assistant/manifest.yaml

### Required Credentials
| Credential | Type | Scopes/Details |
|------------|------|----------------|
| Google OAuth2 (Gmail) | OAuth2 | `https://www.googleapis.com/auth/gmail.modify`, `https://www.googleapis.com/auth/gmail.readonly` |
| Google OAuth2 (Calendar) | OAuth2 | `https://www.googleapis.com/auth/calendar` |
| Gemini API Key | API Key | `GEMINI_API_KEY` environment variable |
| PostgreSQL | Connection | `Postgres assistant` credential in n8n |

### Required APIs
- **Gmail API**: List messages, get message details
- **Google Calendar API**: Create, update, delete events
- **Gemini API**: Email classification and action determination
- **PostgreSQL**: Deduplication via `assistant_processed_items` table

### Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `GEMINI_MODEL` | Model name (e.g., `gemini-2.5-flash`) | ✅ |
| `TZ` | Timezone (e.g., `Europe/Madrid`) | ✅ |
| `N8N_ENCRYPTION_KEY` | n8n encryption key | ✅ |

### Required n8n Nodes
- `n8n-nodes-base.gmailTrigger` (v1)
- `n8n-nodes-base.gmail` (v1.2)
- `n8n-nodes-base.webhook` (v2)
- `n8n-nodes-base.code` (v2) × 4
- `n8n-nodes-base.if` (v2.2) × 7
- `n8n-nodes-base.postgres` (v2.5)
- `n8n-nodes-base.httpRequest` (v4.2) × 2
- `n8n-nodes-base.googleCalendar` (v1.3) × 4

### PostgreSQL Dependencies
- **Table**: `assistant_processed_items`
- **Operations**: INSERT with ON CONFLICT DO NOTHING, SELECT for deduplication
- **Columns used**: `item_key`, `source`, `title`, `payload`

### Playwright Dependencies
- **None** - This workflow does not use Playwright

### Trigger
- **Primary**: Gmail Trigger (push notification on new email)
- **Secondary**: Webhook at `/assistant/email` (manual intake)

### Outputs
- Google Calendar events (create/update/delete)
- Console logs for notifications (task, important, process)
- Deduplication records in PostgreSQL

### Known Risks
1. **Gemini API key in workflow**: The workflow uses `{{$env.GEMINI_API_KEY}}` directly in HTTP request URL - this exposes the key in n8n execution logs
2. **No Telegram/Slack notifications**: Only console logging for actionable emails
3. **Calendar operations require high confidence (≥0.85)**: May miss valid events
4. **Gmail trigger vs polling**: Uses both trigger and list - potential duplicate processing
5. **Hardcoded credential names**: "Google OAuth2", "Postgres assistant" must match n8n exactly

### Compatibility Status
- **Manifest Match**: ⚠️ PARTIAL - Manifest lists `openrouter` but workflow uses `Gemini` directly via HTTP
- **Credential Mapping**: ⚠️ MISMATCH - Manifest maps `openRouterApi: openrouter` but workflow uses Gemini API key via env var
- **PostgreSQL Credential**: ✅ Matches (`postgres: postgresql`)
- **Google Credentials**: ✅ Matches (`gmailOAuth2: google`, `googleCalendarOAuth2Api: google`)

---

## 02-laboral.json — AI Personal Assistant - Laboral

### Basic Information
- **ID**: 02-laboral
- **Name**: AI Personal Assistant - Laboral
- **Source File**: workflows/02-laboral.json
- **Manifest**: automations/laboral/manifest.yaml

### Required Credentials
| Credential | Type | Scopes/Details |
|------------|------|----------------|
| PostgreSQL | Connection | `Postgres assistant` credential in n8n |
| Gemini API Key | API Key | `GEMINI_API_KEY` environment variable |
| Telegram Bot Token | Token | `TELEGRAM_BOT_TOKEN` environment variable |
| Telegram Chat ID | Config | `TELEGRAM_CHAT_ID` environment variable |

### Required APIs
- **Playwright Scraper Service**: HTTP GET to `http://playwright:3000/linkedin` (internal service)
- **Gemini API**: Job offer summarization and fit analysis
- **Telegram Bot API**: Send job notifications
- **PostgreSQL**: Deduplication and job storage via `assistant_processed_items`

### Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `GEMINI_MODEL` | Model name (e.g., `gemini-2.5-flash`) | ✅ |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | ✅ |
| `TELEGRAM_CHAT_ID` | Target chat ID for notifications | ✅ |
| `PLAYWRIGHT_BASE_URL` | Playwright service URL (default: `http://playwright:3000`) | ✅ |
| `TZ` | Timezone (e.g., `Europe/Madrid`) | ✅ |

### Required n8n Nodes
- `n8n-nodes-base.cron` (v1.2)
- `n8n-nodes-base.manualTrigger` (v1)
- `n8n-nodes-base.webhook` (v2)
- `n8n-nodes-base.code` (v2) × 5
- `n8n-nodes-base.httpRequest` (v4.2) × 3
- `n8n-nodes-base.postgres` (v2.5)
- `n8n-nodes-base.respondToWebhook` (v1.1)

### PostgreSQL Dependencies
- **Table**: `assistant_processed_items`
- **Operations**: Complex INSERT with CTE for deduplication, SELECT for verification
- **Columns used**: `item_key`, `source`, `title`, `payload`
- **Source values**: `linkedin`, `playwright_linkedin`

### Playwright Dependencies
- **Service**: Playwright scraper at `http://playwright:3000`
- **Endpoint**: `/linkedin` with query parameters
- **Parameters**: `location`, `keywords`, `termsPerQuery`, `maxJobsPerSearch`, `maxScrollSteps`, `gotoTimeout`, `selectorTimeout`
- **Output**: Normalized job objects with `item_key` format `job:linkedin:{identity}`

### Trigger
- **Primary**: Cron daily at 08:30
- **Secondary**: Manual trigger
- **Tertiary**: Webhook at `/assistant/playwright-jobs-laboral`

### Outputs
- Telegram messages (HTML format) with top 3 job offers
- PostgreSQL deduplication records
- Webhook response with execution summary

### Known Risks
1. **Gemini API key in workflow**: Direct use of `{{$env.GEMINI_API_KEY}}` in HTTP request URL
2. **Telegram credentials in workflow**: Direct use of `{{$env.TELEGRAM_BOT_TOKEN}}` and `{{$env.TELEGRAM_CHAT_ID}}`
3. **Playwright service dependency**: Requires separate Playwright container running
4. **Hardcoded filtering logic**: Large INCLUDE/EXCLUDE arrays in code node - difficult to maintain
5. **Scoring algorithm in workflow**: Complex deterministic scoring in code node - not configurable
6. **No error notifications for scraper failures**: Only logs errors, doesn't alert
7. **Credential names**: "Postgres assistant" must match n8n exactly

### Compatibility Status
- **Manifest Match**: ⚠️ PARTIAL - Manifest lists `openrouter` but workflow uses `Gemini` directly
- **Credential Mapping**: ⚠️ MISMATCH - Manifest maps `openRouterApi: openrouter` and `telegramApi: telegram` but workflow uses env vars directly
- **PostgreSQL Credential**: ✅ Matches (`postgres: postgresql`)
- **Playwright Dependency**: ✅ Listed in manifest dependencies

---

## 03-news.json — AI Personal Assistant - News

### Basic Information
- **ID**: 03-news
- **Name**: AI Personal Assistant - News
- **Source File**: workflows/03-news.json
- **Manifest**: automations/news/manifest.yaml

### Required Credentials
| Credential | Type | Scopes/Details |
|------------|------|----------------|
| PostgreSQL | Connection | `Postgres assistant` credential in n8n |
| Gemini API Key | API Key | `GEMINI_API_KEY` environment variable |
| WhatsApp Business API | Token | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_RECIPIENT`, `WHATSAPP_API_VERSION` |

### Required APIs
- **Google News RSS**: `https://news.google.com/rss/search?q=...`
- **Gemini API**: News summarization with structured JSON output
- **WhatsApp Business API**: Send message to recipient
- **PostgreSQL**: Deduplication via `assistant_processed_items`

### Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `GEMINI_MODEL` | Model name | ✅ |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Business API token | ✅ |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | ✅ |
| `WHATSAPP_RECIPIENT` | Target phone number | ✅ |
| `WHATSAPP_API_VERSION` | API version (e.g., `v18.0`) | ✅ |

### Required n8n Nodes
- `n8n-nodes-base.cron` (v1.2)
- `n8n-nodes-base.rssFeedRead` (v1)
- `n8n-nodes-base.code` (v2) × 2
- `n8n-nodes-base.postgres` (v2.5)
- `n8n-nodes-base.httpRequest` (v4.2) × 2

### PostgreSQL Dependencies
- **Table**: `assistant_processed_items`
- **Operations**: INSERT with ON CONFLICT DO NOTHING
- **Columns used**: `item_key`, `source`, `title`, `payload`
- **Source value**: `news`

### Playwright Dependencies
- **None** - Uses RSS feeds directly

### Trigger
- **Primary**: Cron daily at 13:00

### Outputs
- WhatsApp messages with news summaries
- PostgreSQL deduplication records

### Known Risks
1. **Gemini API key in workflow**: Direct use in HTTP request URL
2. **WhatsApp credentials in workflow**: Multiple env vars used directly in HTTP request
3. **Single RSS source**: Only Google News with fixed query
4. **No fallback for WhatsApp failures**: Only `onError: continueRegularOutput`
5. **Hardcoded RSS query**: Spanish economy/tech/aerospace/space - not configurable
6. **Credential name**: "Postgres assistant" must match n8n exactly

### Compatibility Status
- **Manifest Match**: ⚠️ PARTIAL - Manifest lists `openrouter` and `telegram` but workflow uses `Gemini` and `WhatsApp`
- **Credential Mapping**: ❌ MAJOR MISMATCH - Manifest maps `openRouterApi: openrouter`, `telegramApi: telegram` but workflow uses neither
- **PostgreSQL Credential**: ✅ Matches (`postgres: postgresql`)

---

## 04-personal-brand.json — AI Personal Assistant - Personal Brand

### Basic Information
- **ID**: 04-personal-brand
- **Name**: AI Personal Assistant - Personal Brand
- **Source File**: workflows/04-personal-brand.json
- **Manifest**: automations/personal-brand/manifest.yaml

### Required Credentials
| Credential | Type | Scopes/Details |
|------------|------|----------------|
| PostgreSQL | Connection | `Postgres account` credential in n8n (different from others!) |
| Gemini API Key | API Key | Via HTTP Header Auth credential `Header Auth account` in n8n |
| Google Docs OAuth2 | OAuth2 | `Google Docs account` credential in n8n |

### Required APIs
- **Google News RSS**: 5 separate feeds (OpenAI, Google AI, Microsoft AI, NVIDIA, Space)
- **Gemini API**: LinkedIn post generation (via HTTP Header Auth)
- **Google Docs API**: Create and update documents
- **PostgreSQL**: Deduplication via `assistant_processed_items`

### Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Used via HTTP Header Auth in n8n | ✅ |

### Required n8n Nodes
- `n8n-nodes-base.cron` (v1.2)
- `n8n-nodes-base.rssFeedRead` (v1) × 5
- `n8n-nodes-base.code` (v2) × 5
- `n8n-nodes-base.postgres` (v2.5) × 5
- `n8n-nodes-base.httpRequest` (v4.2) × 5 (with HTTP Header Auth)
- `n8n-nodes-base.googleDocs` (v2) × 10 (5 create + 5 update)

### PostgreSQL Dependencies
- **Table**: `assistant_processed_items`
- **Operations**: INSERT with ON CONFLICT DO NOTHING × 5 (one per RSS source)
- **Columns used**: `item_key`, `source`, `title`, `payload`
- **Source value**: `personal_brand`
- **Credential**: Uses `Postgres account` (different from `Postgres assistant`)

### Playwright Dependencies
- **None** - Uses RSS feeds directly

### Trigger
- **Primary**: Cron daily at 18:00

### Outputs
- Google Docs documents (one per news item, organized in folders)
- PostgreSQL deduplication records

### Known Risks
1. **Duplicate workflow structure**: 5 nearly identical parallel branches - maintenance nightmare
2. **Hardcoded Google Docs folder IDs**: 5 different folder IDs hardcoded in workflow
3. **Credential inconsistency**: Uses `Postgres account` vs `Postgres assistant` used by other workflows
4. **Gemini via HTTP Header Auth**: Unusual pattern - API key passed via header auth credential
5. **No notifications**: Only creates Google Docs, no Telegram/email/Slack alerts
6. **Hardcoded RSS queries**: 5 fixed topics - not configurable
7. **Large workflow**: 1141 lines, 70+ nodes - performance impact on n8n
8. **Credential names**: Must match exactly: `Postgres account`, `Header Auth account`, `Google Docs account`

### Compatibility Status
- **Manifest Match**: ⚠️ PARTIAL - Manifest lists `openrouter` and `telegram` but workflow uses `Gemini` (via header auth) and `Google Docs`
- **Credential Mapping**: ❌ MAJOR MISMATCH - Manifest maps `openRouterApi: openrouter`, `telegramApi: telegram`, `postgres: postgresql` but workflow uses `Postgres account`, `Header Auth account`, `Google Docs account`
- **PostgreSQL Credential**: ❌ MISMATCH - Uses `Postgres account` not `postgresql`

---

## 05-playwright-jobs.json — AI Personal Assistant - Playwright Jobs

### Basic Information
- **ID**: 05-playwright-jobs
- **Name**: AI Personal Assistant - Playwright Jobs
- **Source File**: workflows/05-playwright-jobs.json
- **Manifest**: automations/playwright-jobs/manifest.yaml

### Required Credentials
| Credential | Type | Scopes/Details |
|------------|------|----------------|
| PostgreSQL | Connection | `Postgres assistant` credential in n8n |

### Required APIs
- **Playwright Scraper Service**: HTTP GET to `http://playwright:3000/linkedin` and `/infojobs`
- **PostgreSQL**: Deduplication and job storage via `assistant_processed_items`

### Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `PLAYWRIGHT_BASE_URL` | Playwright service URL (default: `http://playwright:3000`) | ✅ |

### Required n8n Nodes
- `n8n-nodes-base.cron` (v1.2)
- `n8n-nodes-base.manualTrigger` (v1)
- `n8n-nodes-base.webhook` (v2)
- `n8n-nodes-base.code` (v2) × 2
- `n8n-nodes-base.httpRequest` (v4.2)
- `n8n-nodes-base.postgres` (v2.5)

### PostgreSQL Dependencies
- **Table**: `assistant_processed_items`
- **Operations**: Complex INSERT with CTE for deduplication (handles both linkedin and infojobs)
- **Columns used**: `item_key`, `source`, `title`, `payload`
- **Source values**: `playwright_linkedin`, `playwright_infojobs`

### Playwright Dependencies
- **Service**: Playwright scraper at `http://playwright:3000`
- **Endpoints**: `/linkedin`, `/infojobs` with query parameters
- **Parameters**: `location`, `keywords`, `termsPerQuery`, `maxJobsPerSearch`, `maxScrollSteps`, `gotoTimeout`, `selectorTimeout`
- **Output**: Normalized job objects with `item_key` format `playwright:{source}:{identity}`

### Trigger
- **Primary**: Cron daily at 08:30
- **Secondary**: Manual trigger
- **Tertiary**: Webhook at `/assistant/playwright-jobs-standalone`

### Outputs
- JSON response with scraped job summary (count, sources, job details)
- PostgreSQL deduplication records
- Webhook response

### Known Risks
1. **No AI processing**: Unlike laboral workflow, this does NOT use Gemini for summarization/scoring
2. **No notifications**: Only returns JSON - no Telegram, email, or other alerts
3. **Playwright service dependency**: Requires separate Playwright container
4. **Dual source support**: Handles both LinkedIn and InfoJobs but with different ID extraction logic
5. **Credential name**: "Postgres assistant" must match n8n exactly
6. **No filtering/scoring**: Returns all new jobs without relevance filtering

### Compatibility Status
- **Manifest Match**: ⚠️ PARTIAL - Manifest lists `openrouter` and `telegram` but workflow uses NEITHER
- **Credential Mapping**: ❌ MAJOR MISMATCH - Manifest maps `openRouterApi: openrouter`, `telegramApi: telegram`, `postgres: postgresql` but workflow ONLY uses `postgres: postgresql`
- **PostgreSQL Credential**: ✅ Matches (`postgres: postgresql`)
- **Playwright Dependency**: ✅ Listed in manifest dependencies

---

## Cross-Workflow Analysis

### Credential Name Inconsistencies
| Workflow | PostgreSQL Credential Name |
|----------|---------------------------|
| 01-email-manager | `Postgres assistant` |
| 02-laboral | `Postgres assistant` |
| 03-news | `Postgres assistant` |
| 04-personal-brand | `Postgres account` ⚠️ DIFFERENT |
| 05-playwright-jobs | `Postgres assistant` |

### AI Provider Inconsistencies
| Workflow | Manifest Says | Workflow Uses |
|----------|---------------|---------------|
| 01-email-manager | OpenRouter | Gemini (direct HTTP) |
| 02-laboral | OpenRouter | Gemini (direct HTTP) |
| 03-news | OpenRouter | Gemini (direct HTTP) |
| 04-personal-brand | OpenRouter | Gemini (via HTTP Header Auth) |
| 05-playwright-jobs | OpenRouter | None |

### Notification Channel Inconsistencies
| Workflow | Manifest Says | Workflow Uses |
|----------|---------------|---------------|
| 01-email-manager | (none listed) | Console log only |
| 02-laboral | Telegram | Telegram (direct HTTP) |
| 03-news | Telegram | WhatsApp Business API |
| 04-personal-brand | Telegram | Google Docs only |
| 05-playwright-jobs | Telegram | None (JSON response only) |

### Critical Issues Requiring Fixes

1. **Manifest-Workflow Mismatch**: All 5 manifests claim OpenRouter but workflows use Gemini directly
2. **Credential Name Drift**: Personal Brand uses `Postgres account` vs `Postgres assistant`
3. **Missing Credential Mappings**: Workflows use env vars directly instead of n8n credential references
4. **Security Risk**: API keys and tokens embedded in workflow JSON via `{{$env.VAR}}` pattern
5. **Notification Mismatch**: Manifests claim Telegram but workflows use WhatsApp, Google Docs, or nothing
6. **Personal Brand Duplication**: 5x duplicated branches should be refactored to use sub-workflows or loops

---

## Recommendations

### Immediate (Pre-Integration)
1. **Update all manifests** to reflect actual workflow requirements (Gemini, not OpenRouter)
2. **Standardize PostgreSQL credential name** to `Postgres assistant` across all workflows
3. **Fix credential mappings** in manifests to match actual n8n credential references
4. **Document actual environment variables** required by each workflow

### Security Hardening
1. **Move secrets to n8n credentials**: Replace `{{$env.GEMINI_API_KEY}}` with proper n8n credential references
2. **Use n8n credential types**: HTTP Header Auth for Gemini, Telegram API for Telegram, etc.
3. **Remove hardcoded tokens** from workflow JSON

### Architecture Improvements
1. **Refactor Personal Brand**: Use sub-workflow or loop over RSS sources
2. **Add notification abstraction**: Standardize on Telegram for all workflows
3. **Create shared Playwright node**: Avoid duplicating scraper invocation logic
4. **Externalize configuration**: Move filtering/scoring rules to config files or database

---

## Validation Checklist

- [x] All 5 workflow JSON files inspected
- [x] All 5 manifest.yaml files reviewed
- [x] Required credentials identified per workflow
- [x] Required APIs identified per workflow
- [x] Required environment variables identified per workflow
- [x] Required n8n nodes identified per workflow
- [x] PostgreSQL dependencies documented
- [x] Playwright dependencies documented
- [x] Triggers identified
- [x] Outputs documented
- [x] Known risks identified
- [x] Compatibility status assessed (manifest vs workflow)
- [x] Cross-workflow inconsistencies documented


---

## Actualización de validación E2E — 18 de agosto de 2026

La revisión actual confirmó que los cinco archivos fuente de `workflows/` son JSON válidos. Se detectó que las copias importables de `laboral`, `news`, `personal-brand` y `playwright-jobs` tenían cero nodos. Se restauraron desde sus archivos fuente correspondientes, sin modificar los originales. Después de la restauración, esas cuatro copias coinciden byte a byte con la fuente. `email-assistant` conserva una divergencia histórica de hash; conserva 30 nodos y los mismos tipos de credencial observados, pero requiere comparación humana antes de declararlo idéntico.

| Automatización | Estado importable actual | Dependencias y bloqueadores observados |
|---|---|---|
| Email Assistant | Carga JSON válida; 30 nodos. | Google OAuth, PostgreSQL y Gemini; instalación bloqueada de forma segura por credenciales ausentes. |
| Laboral | Restaurado desde fuente; 17 nodos. | PostgreSQL, Gemini, Telegram y Playwright; no se iniciaron proveedores externos. |
| News | Restaurado desde fuente; 7 nodos. | PostgreSQL, Gemini y variables WhatsApp; CredentialManager no modela un proveedor WhatsApp. |
| Personal Brand | Restaurado desde fuente; 36 nodos. | PostgreSQL, Google Docs y Header Auth; el mapping formal actual no cubre todas las credenciales n8n detectadas. |
| Playwright Jobs | Restaurado desde fuente; 8 nodos. | PostgreSQL y Playwright; el servicio Playwright estaba saludable. |
| Test Automation | Workflow autocontenido y sin credenciales. | No se pudo importar por HTTP 401 de la API n8n; no dejó workflow ni mapeos huérfanos. |

Los manifests se descubrieron correctamente tras la restauración. También se corrigió la interpretación de `postgresql`, `playwright` y `google-oauth2`: son prerrequisitos de infraestructura o OAuth, no IDs de otras automatizaciones. Por ello se validan mediante salud de servicio y requisitos de credenciales, no como metadatos de una automatización instalada.

> El ciclo completo instalar → habilitar → ejecutar → deshabilitar → desinstalar sigue **BLOCKED** por la autorización HTTP 401 de n8n. No se usaron credenciales reales, no se enviaron mensajes o correos, y no se ejecutaron workflows reales.
