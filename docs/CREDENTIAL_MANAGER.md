# Credential Manager Documentation

## Overview

The Credential Manager is a secure, extensible system for managing credentials in the Automation Center. It provides a unified interface for different credential types while ensuring secrets are never exposed in logs, API responses, or PostgreSQL.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CredentialManager                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SecureStore  │  │   Providers  │  │   n8n Client │          │
│  │  (OS-specific)│  │  (Registry)  │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL (metadata only)             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **SecureStore** - OS-specific secure storage abstraction
2. **CredentialProvider** - Base classes for different credential types
3. **ProviderRegistry** - Registry for extensible provider management
4. **CredentialManager** - Main orchestration class
5. **n8n Integration** - Sync credentials with n8n for workflow execution

## Secure Storage

### Supported Platforms

| Platform | Implementation | Technology |
|----------|---------------|------------|
| Windows | KeyringSecureStore | Windows Credential Manager (DPAPI) |
| macOS | KeyringSecureStore | macOS Keychain |
| Linux Desktop | KeyringSecureStore | Secret Service (GNOME Keyring/KWallet) |
| Linux Headless/Container | EncryptedFileSecureStore | Encrypted file + system key |
| Raspberry Pi | EncryptedFileSecureStore | Encrypted file + system key |

### KeyringSecureStore

Uses the `keyring` Python library which automatically selects the appropriate backend:
- Windows: `win32cred` (Credential Manager)
- macOS: `keyring.backends.macOS.Keychain`
- Linux: `keyring.backends.SecretService.Keyring` (GNOME Keyring/KWallet)

### EncryptedFileSecureStore

For headless environments (containers, servers, Raspberry Pi):
- Encrypts vault using Fernet (AES-128)
- Key derived from system key file using PBKDF2 (100,000 iterations)
- Vault file permissions set to 0600 (owner read/write only)

### Usage

```python
from app.services.credentials import get_secure_store

store = get_secure_store()

# Store a secret
await store.set("my-key", "secret-value")

# Retrieve a secret
value = await store.get("my-key")

# Check existence
exists = await store.exists("my-key")

# Delete
await store.delete("my-key")
```

## Credential Types

### 1. OAuth 2.0 Credentials (OAuthCredential)

Used for providers implementing OAuth 2.0 with PKCE:
- Google (Gmail, Calendar, Tasks, Drive, etc.)

Fields:
- `access_token` - Short-lived access token
- `refresh_token` - Long-lived refresh token
- `expires_at` - Token expiration timestamp
- `scopes` - List of granted scopes
- `token_type` - Usually "Bearer"

### 2. API Key Credentials (ApiKeyCredential)

Used for providers using simple API keys:
- OpenAI
- Google Gemini
- Anthropic
- OpenRouter

Fields:
- `api_key` - The API key

### 3. Token Credentials (TokenCredential)

Used for simple token-based authentication:
- Telegram Bot Token

Fields:
- `token` - The token

## Providers

### Google OAuth Provider

**Provider name:** `google`
**Credential type:** OAuth
**n8n credential type:** `googleOAuth2Api`

#### Configuration

Required environment variables:
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `OAUTH_REDIRECT_BASE_URL` - Base URL for OAuth callbacks (e.g., `http://localhost:8000`)

#### Default Scopes

```python
[
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
```

#### Custom Scopes

Scopes can be specified per-request:
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/tasks`
- `https://www.googleapis.com/auth/drive.file`

#### PKCE Flow

1. Generate code_verifier (64 bytes URL-safe)
2. Generate code_challenge (SHA256 of verifier, base64url encoded)
3. Store code_verifier in SecureStore with state
4. Redirect user to authorization URL with code_challenge
5. On callback, retrieve code_verifier and exchange code for tokens
6. Store tokens in SecureStore
7. Create n8n credential
8. Save metadata to PostgreSQL

### OpenAI Provider

**Provider name:** `openai`
**Credential type:** API Key
**n8n credential type:** `openAiApi`
**Auth header:** `Authorization: Bearer <api_key>`
**Validation endpoint:** `/models`

### Gemini Provider

**Provider name:** `gemini`
**Credential type:** API Key
**n8n credential type:** `googlePalmApi`
**Auth header:** `x-goog-api-key: <api_key>`
**Validation endpoint:** `/models`

### Anthropic Provider

**Provider name:** `anthropic`
**Credential type:** API Key
**n8n credential type:** `anthropicApi`
**Auth header:** `x-api-key: <api_key>`
**Validation endpoint:** `/models`

### OpenRouter Provider

**Provider name:** `openrouter`
**Credential type:** API Key
**n8n credential type:** `openRouterApi`
**Auth header:** `Authorization: Bearer <api_key>`
**Validation endpoint:** `/models`

### Telegram Provider

**Provider name:** `telegram`
**Credential type:** Token
**n8n credential type:** `telegramApi`
**Validation endpoint:** `/getMe`

## API Endpoints

### List Credentials
```
GET /api/v1/credentials
```
Returns metadata only (no secrets).

### List Providers
```
GET /api/v1/credentials/providers
```
Returns all registered providers with their types.

### Start OAuth Flow
```
POST /api/v1/credentials/connect
Content-Type: application/json

{
  "provider": "google",
  "scopes": ["email", "profile", "gmail.modify"]
}
```
Returns authorization URL and state.

### Store API Key
```
POST /api/v1/credentials/api-key
Content-Type: application/json

{
  "provider": "openai",
  "account_identifier": "user@example.com",
  "api_key": "sk-..."
}
```

### Store Token
```
POST /api/v1/credentials/token
Content-Type: application/json

{
  "provider": "telegram",
  "account_identifier": "my_bot",
  "token": "123456:ABC-DEF..."
}
```

### Generate OAuth URL
```
GET /api/v1/credentials/{provider}/authorize?scopes=email,profile,gmail.modify
```

### OAuth Callback
```
GET /api/v1/credentials/{provider}/callback?code=...&state=...
```
Handles OAuth callback, exchanges code for tokens, stores credentials.

### Refresh Credential
```
POST /api/v1/credentials/{credential_id}/refresh
```
- OAuth: Refreshes access token using refresh token
- API Key/Token: Re-validates credential

### Revoke Credential
```
DELETE /api/v1/credentials/{credential_id}
```
- Revokes tokens with provider (if supported)
- Deletes from SecureStore
- Deletes from n8n
- Marks as revoked in PostgreSQL

### Get Credential Metadata
```
GET /api/v1/credentials/{credential_id}
```
Returns metadata only (no secrets).

## n8n Integration

The CredentialManager automatically creates and manages n8n credentials:

1. When a credential is stored, a corresponding n8n credential is created
2. When a credential is refreshed, the n8n credential is updated
3. When a credential is revoked, the n8n credential is deleted

### n8n Credential Types Mapping

| Provider | n8n Credential Type |
|----------|---------------------|
| Google OAuth | `googleOAuth2Api` |
| OpenAI | `openAiApi` |
| Gemini | `googlePalmApi` |
| Anthropic | `anthropicApi` |
| OpenRouter | `openRouterApi` |
| Telegram | `telegramApi` |

## Security Model

### Secrets Never Stored In

- ❌ PostgreSQL (only metadata)
- ❌ API responses
- ❌ Logs (automatically sanitized)
- ❌ Frontend
- ❌ Workflow JSON
- ❌ Configuration files
- ❌ Backups (unless SecureStore is backed up)

### Secrets Only In

- ✅ OS Secure Storage (Keyring/Encrypted File)
- ✅ n8n (encrypted at rest by n8n)
- ✅ Memory during operations (briefly)

### Sanitization

The `SanitizedLog` class automatically redacts sensitive keys:
- `token`, `secret`, `key`, `password`, `credential`, `authorization`
- `access_token`, `refresh_token`, `id_token`, `client_secret`
- `code`, `authorization_code`, `callback`

## Adding a New Provider

### 1. Create Provider Class

```python
from app.services.credentials.providers import ApiKeyProvider, ApiKeyCredential
from app.services.credentials.secure_store import SecureStore

class MyProvider(ApiKeyProvider):
    def __init__(self, secure_store: SecureStore = None):
        super().__init__(secure_store)
        self.provider_name = "myprovider"
        self.api_base_url = "https://api.myprovider.com/v1"
        self.auth_header = "Authorization"
        self.auth_prefix = "Bearer"
        self.validation_endpoint = "/validate"
    
    def get_n8n_credential_type(self) -> str:
        return "myProviderApi"
    
    def build_n8n_credentials(self, credential: ApiKeyCredential) -> Dict[str, Any]:
        return {"apiKey": credential.api_key}
```

### 2. Register Provider

```python
from app.services.credentials import provider_registry
from app.services.credentials.my_provider import MyProvider

my_provider = MyProvider()
provider_registry.register(my_provider)
```

### 3. Add to __init__.py

```python
from .my_provider import MyProvider, my_provider
__all__.extend(["MyProvider", "my_provider"])
```

## Configuration

### Environment Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_BASE_URL=http://localhost:8000

# n8n
N8N_API_KEY=your-n8n-api-key
N8N_API_URL=http://n8n:5678

# PostgreSQL
POSTGRES_DB=assistant
POSTGRES_USER=assistant
POSTGRES_PASSWORD=secure-password
```

### SecureStore Configuration

For EncryptedFileSecureStore (headless):
- `vault_path`: `/etc/automation-center/vault.enc` (default)
- `key_path`: `/etc/automation-center/system.key` (default)

Generate system key:
```bash
# Generate 32+ bytes of random data
head -c 32 /dev/urandom > /etc/automation-center/system.key
chmod 600 /etc/automation-center/system.key
```

## Testing

Run tests:
```bash
cd backend
pytest tests/test_credential_manager.py -v
```

Test coverage:
- SecureStore implementations
- Provider registry
- Google OAuth provider
- API Key providers
- Telegram provider
- CredentialManager orchestration
- Security (no secrets in logs, PostgreSQL, API responses)

## Troubleshooting

### Keyring not available on Linux headless

Install dependencies:
```bash
# Ubuntu/Debian
apt-get install -y libsecret-1-dev gnome-keyring

# Or use EncryptedFileSecureStore (automatic in containers)
```

### n8n credential creation fails

Check:
1. n8n is running and accessible
2. N8N_API_KEY is correct
3. n8n version supports the credential type

### OAuth callback fails

Check:
1. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set
2. OAUTH_REDIRECT_BASE_URL matches Google Cloud Console
3. Authorized redirect URI in Google Cloud Console includes `/api/v1/credentials/google/callback`

## Migration from Old System

The old credential system stored encrypted secrets in PostgreSQL. The new system:

1. Moves secrets to OS Secure Storage
2. Keeps only metadata in PostgreSQL
3. Adds n8n integration
4. Supports multiple credential types
5. Provides extensible provider architecture

No automatic migration - credentials need to be re-added through the new API.