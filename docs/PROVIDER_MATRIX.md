# Provider Matrix

Generated: 2026-08-18
Phase: 2.8 - End-to-End Integration & Real Automations

Based on actual workflow inspection (not manifest claims).

---

## Summary Matrix

| Automation | PostgreSQL | Google OAuth2 | Gemini API | Telegram | WhatsApp | Google Docs | Playwright | OpenRouter | OpenAI | Anthropic |
|------------|------------|---------------|------------|----------|----------|-------------|------------|------------|--------|-----------|
| Email Assistant | ✅ | ✅ (Gmail, Calendar) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Laboral | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| News | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Personal Brand | ✅ | ✅ (Docs only) | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Playwright Jobs | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Test Automation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Detailed Provider Requirements

### Email Assistant (email-assistant)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Connection | Deduplication via `assistant_processed_items` | n8n credential: `Postgres assistant` |
| **Google (Gmail)** | OAuth2 | Trigger on new email, list/get messages | n8n credential: `Google OAuth2` |
| **Google (Calendar)** | OAuth2 | Create/update/delete events | n8n credential: `Google OAuth2` (same) |
| **Gemini** | API Key | Email classification & action determination | **Env var**: `GEMINI_API_KEY` in HTTP URL |

**Note**: Manifest originally claimed OpenRouter. Actual: Gemini via direct HTTP.

---

### Laboral (laboral)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Connection | Job deduplication & storage | n8n credential: `Postgres assistant` |
| **Gemini** | API Key | Job summarization & fit scoring | **Env var**: `GEMINI_API_KEY` in HTTP URL |
| **Telegram** | Bot Token | Send job notifications | **Env vars**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| **Playwright** | HTTP Service | LinkedIn job scraping | **Env var**: `PLAYWRIGHT_BASE_URL` (default: `http://playwright:3000`) |

**Note**: Manifest claimed OpenRouter + Telegram n8n credential. Actual: Gemini + Telegram via env vars.

---

### News (news)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Connection | Article deduplication | n8n credential: `Postgres assistant` |
| **Gemini** | API Key | News summarization | **Env var**: `GEMINI_API_KEY` in HTTP URL |
| **WhatsApp** | Business API | Send notifications | **Env vars**: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_RECIPIENT`, `WHATSAPP_API_VERSION` |
| **Google News** | RSS | News source | Direct HTTP (no auth) |

**Note**: Manifest claimed OpenRouter + Telegram. Actual: Gemini + WhatsApp Business API.

---

### Personal Brand (personal-brand)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Connection | Article deduplication | n8n credential: **`Postgres account`** (non-standard!) |
| **Gemini** | API Key | LinkedIn post generation | n8n credential: **`Header Auth account`** (HTTP Header Auth) |
| **Google Docs** | OAuth2 | Create/update documents | n8n credential: **`Google Docs account`** |
| **Google News** | RSS | 5 news sources | Direct HTTP (no auth) |

**Note**: Manifest claimed OpenRouter + Telegram + standard PostgreSQL. Actual: Gemini (header auth) + Google Docs + non-standard PG credential name.

---

### Playwright Jobs (playwright-jobs)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Connection | Job deduplication & storage | n8n credential: `Postgres assistant` |
| **Playwright** | HTTP Service | LinkedIn & InfoJobs scraping | **Env var**: `PLAYWRIGHT_BASE_URL` (default: `http://playwright:3000`) |

**Note**: Manifest claimed OpenRouter + Telegram + PostgreSQL. Actual: **Only PostgreSQL**. No AI, no notifications.

---

### Test Automation (test-automation)
| Provider | Type | How Used | Credential Method |
|----------|------|----------|-------------------|
| *(none)* | - | Simple manual trigger → set result | No credentials required |

---

## Provider Capability Matrix

| Capability | Google | Gemini | OpenRouter | OpenAI | Anthropic | Telegram | WhatsApp | Playwright | PostgreSQL |
|------------|--------|--------|------------|--------|-----------|----------|----------|------------|------------|
| OAuth2 Support | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| API Key Support | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Token Support | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Used in Workflows | 2 | 4 | 0 | 0 | 0 | 1 | 1 | 2 | 5 |
| Credential Manager Support | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅* |

*PostgreSQL is a connection, not a credential provider per se. Managed via n8n credential.

---

## Credential Manager Provider Registry

From `backend/app/services/credentials/manager.py` initialization:

```python
# Registered providers:
- google          (OAuth2)     → GoogleOAuthProvider
- openai          (API_KEY)    → OpenAIProvider
- gemini          (API_KEY)    → GeminiProvider
- anthropic       (API_KEY)    → AnthropicProvider
- openrouter      (API_KEY)    → OpenRouterProvider
- telegram        (TOKEN)      → TelegramProvider
```

**Missing from registry but used in workflows:**
- `whatsapp` (Token/API) - Not implemented in Credential Manager
- `playwright` (Service URL) - Not a credential, just env var

---

## Environment Variables Required Per Automation

| Automation | Required Env Vars |
|------------|-------------------|
| Email Assistant | `GEMINI_API_KEY`, `GEMINI_MODEL`, `TZ` |
| Laboral | `GEMINI_API_KEY`, `GEMINI_MODEL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PLAYWRIGHT_BASE_URL`, `TZ` |
| News | `GEMINI_API_KEY`, `GEMINI_MODEL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_RECIPIENT`, `WHATSAPP_API_VERSION` |
| Personal Brand | `GEMINI_API_KEY`, `GEMINI_MODEL` |
| Playwright Jobs | `PLAYWRIGHT_BASE_URL` |
| Test Automation | *(none)* |

---

## n8n Credential Names Used in Workflows

| Workflow | Credential Name | Type | Notes |
|----------|-----------------|------|-------|
| 01-email-manager | `Google OAuth2` | Google OAuth2 | Used for both Gmail & Calendar |
| 01-email-manager | `Postgres assistant` | PostgreSQL | Standard name |
| 02-laboral | `Postgres assistant` | PostgreSQL | Standard name |
| 03-news | `Postgres assistant` | PostgreSQL | Standard name |
| 04-personal-brand | `Postgres account` | PostgreSQL | **NON-STANDARD** |
| 04-personal-brand | `Header Auth account` | HTTP Header Auth | For Gemini API key |
| 04-personal-brand | `Google Docs account` | Google Docs OAuth2 | For Google Docs |
| 05-playwright-jobs | `Postgres assistant` | PostgreSQL | Standard name |

---

## Recommendations for Credential Integration

### 1. Standardize PostgreSQL Credential Name
All workflows should use `Postgres assistant` as the credential name. Personal Brand must be updated.

### 2. Move Secrets to n8n Credentials
Replace `{{$env.VAR}}` patterns with proper n8n credential references:
- Gemini API Key → n8n "HTTP Header Auth" or custom credential type
- Telegram Bot Token → n8n "Telegram API" credential
- WhatsApp credentials → n8n "HTTP Header Auth" or custom credential

### 3. Add Missing Providers to Credential Manager
- Implement `WhatsAppProvider` for WhatsApp Business API
- Consider `PlaywrightConfigProvider` for service URL management

### 4. Update Manifest Credential Mappings
All manifests now reflect actual workflow requirements (see updated manifests).

---

## Test Credential Strategy

For E2E testing without real credentials:

| Provider | Test Approach |
|----------|---------------|
| Google OAuth2 | Mock OAuth flow; use test Google account |
| Gemini API Key | Use test API key with quota limits |
| Telegram Bot Token | Use test bot in private chat |
| WhatsApp Business API | Mock HTTP responses; use test sandbox |
| PostgreSQL | Use test database (separate schema) |
| Playwright | Use local Playwright service with test pages |

Never use production credentials in automated tests.