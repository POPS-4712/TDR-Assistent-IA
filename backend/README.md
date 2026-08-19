# Automation Center Backend

The backend API for Automation Center, built with FastAPI.

## Structure

```
backend/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Core utilities
│   ├── database/     # Database models and migrations
│   ├── models/       # Pydantic models
│   ├── schemas/      # API schemas
│   ├── services/     # Business logic
│   └── main.py       # FastAPI application
├── requirements.txt  # Python dependencies
└── README.md
```

## Endpoints

### System
- `GET /api/v1/system/status` - System health status
- `GET /api/v1/system/version` - Application version
- `GET /api/v1/system/config` - Non-sensitive configuration

### Automations
- `GET /api/v1/automations` - List all automations
- `GET /api/v1/automations/{id}` - Get automation details
- `POST /api/v1/automations/{id}/install` - Install automation
- `POST /api/v1/automations/{id}/enable` - Enable automation
- `POST /api/v1/automations/{id}/disable` - Disable automation
- `DELETE /api/v1/automations/{id}` - Uninstall automation
- `GET /api/v1/automations/{id}/logs` - Get automation logs

### Credentials
- `GET /api/v1/credentials` - List credentials (metadata only)
- `POST /api/v1/credentials/connect` - Start credential connection
- `GET /api/v1/credentials/google/authorize` - Generate Google OAuth URL
- `GET /api/v1/credentials/google/callback` - OAuth callback handler
- `POST /api/v1/credentials/{id}/refresh` - Refresh token
- `DELETE /api/v1/credentials/{id}` - Revoke credential

## Development

### Requirements
- Python 3.11+
- PostgreSQL 15+

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python -m app.database.migrations

# Start development server
uvicorn app.main:app --reload
```

## Security

- All secrets are encrypted using OS secure storage
- OAuth tokens are stored locally, never in database
- Logging automatically sanitizes sensitive data
- Credentials are never exposed to the frontend

## Architecture

- **Credential Manager**: Secure local storage of secrets
- **N8N Client**: API wrapper for n8n
- **Automation Manager**: Lifecycle management for automations