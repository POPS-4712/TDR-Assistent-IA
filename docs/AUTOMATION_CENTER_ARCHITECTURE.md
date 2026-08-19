# Automation Center Architecture

## Overview

Automation Center is a local-first application platform that enables non-technical users to install and manage automation workflows using n8n as the execution engine.

## Architecture Principles

1. **Local-First**: All data and credentials remain on the user's device
2. **Simple for Users**: No Docker, PostgreSQL, or n8n knowledge required
3. **Secure by Default**: OAuth 2.0 with PKCE, encrypted secrets, no central servers
4. **Cross-Platform**: Windows, Ubuntu, macOS, Raspberry Pi 4/5

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│                    (React Frontend)                          │
│                    Port: 3001 (Docker)                       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND API                            │
│                    (FastAPI + Python)                        │
│                    Port: 8000 (Docker)                       │
└─────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│   PostgreSQL   │  │     n8n      │  │   Playwright   │
│   (Database)   │  │ (Workflows)  │  │  (Scrapers)    │
│    Port: 5432  │  │  Port: 5678  │  │   Port: 3000   │
└────────────────┘  └────────────────┘  └────────────────┘
```

## Component Details

### Frontend (React + TypeScript + Vite)

- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **State**: Component-level state (no Redux/Context for simplicity)
- **Build**: Vite for fast development and optimized production builds

### Backend (FastAPI + Python)

#### Core Modules

```
backend/
├── app/
│   ├── api/              # FastAPI endpoints
│   │   └── routes/
│   │       ├── system.py
│   │       ├── automations.py
│   │       └── credentials.py
│   ├── core/             # Core utilities
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── database/         # Database layer
│   │   ├── db.py
│   │   ├── models.py
│   │   └── migrations.py
│   ├── models/           # Pydantic models
│   ├── schemas/          # API response schemas
│   └── services/         # Business logic
│       ├── credentials/
│       ├── n8n/
│       ├── automations/
│       ├── executions/
│       └── playwright/
└── requirements.txt
```

#### Services

1. **Credential Manager** (`services/credentials/manager.py`)
   - Uses OS secure storage (Windows Credential Manager, macOS Keychain, Linux Secret Service)
   - Encrypts secrets with Fernet using system-derived keys
   - Never stores raw secrets in PostgreSQL

2. **N8N Client** (`services/n8n/client.py`)
   - HTTP client for n8n API
   - Handles workflow import/export
   - Manages credentials in n8n

3. **Automation Manager** (`services/automations/manager.py`)
   - Installs/uninstalls automations
   - Enables/disables workflows
   - Manages automation metadata

#### Database Schema

```
credentials
├── id (UUID)
├── provider (TEXT)
├── account_identifier (TEXT)
├── scopes (TEXT[])
├── status (TEXT)
├── n8n_credential_id (TEXT)
├── last_refresh (TIMESTAMPTZ)
├── expires_at (TIMESTAMPTZ)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)

automations
├── id (TEXT)
├── name (TEXT)
├── description (TEXT)
├── version (TEXT)
├── status (TEXT)
├── manifest_url (TEXT)
├── dependencies (TEXT[])
├── n8n_workflow_id (TEXT)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)

automation_credentials
├── automation_id (TEXT)
├── credential_id (UUID)
└── created_at (TIMESTAMPTZ)

executions
├── id (TEXT)
├── automation_id (TEXT)
├── workflow_id (TEXT)
├── n8n_execution_id (TEXT)
├── status (TEXT)
├── started_at (TIMESTAMPTZ)
├── completed_at (TIMESTAMPTZ)
├── error_message (TEXT)
└── result_data (JSONB)

settings
├── key (TEXT)
├── value (JSONB)
└── updated_at (TIMESTAMPTZ)
```

### Security

#### OAuth 2.0 Flow

```
User clicks "Connect Google"
    ↓
Frontend calls /api/v1/credentials/google/authorize
    ↓
Backend generates code_verifier and code_challenge
    ↓
Backend creates OAuth state with expiration
    ↓
Backend returns Google authorization URL
    ↓
User visits Google and authorizes
    ↓
Google redirects to /api/v1/credentials/google/callback
    ↓
Backend validates state and code_verifier
    ↓
Backend exchanges code for access_token and refresh_token
    ↓
Backend stores tokens in OS secure storage (via Credential Manager)
    ↓
Backend creates PostgreSQL record with metadata
    ↓
Backend creates n8n credential
    ↓
Frontend shows connected account
```

#### Secret Storage

| Platform | Storage Method |
|----------|---------------|
| Windows | Windows Credential Manager / DPAPI |
| macOS | Keychain |
| Linux (desktop) | Secret Service / GNOME Keyring |
| Linux (headless/RPi) | Encrypted vault file with system key |

## Communication Flow

### Frontend ↔ Backend

```
React Component
    ↓
fetch('/api/v1/automations')
    ↓
FastAPI Route Handler
    ↓
Automation Manager
    ↓
Response (JSON)
    ↓
React Component updates state
```

### Backend ↔ PostgreSQL

```python
async with get_session() as session:
    result = await session.execute(
        "SELECT * FROM credentials WHERE id = :id",
        {"id": credential_id}
    )
```

### Backend ↔ n8n

```python
async with N8NClient() as client:
    workflow_id = await client.import_workflow(workflow_data)
```

## User Experience

### Installation Flow

```
1. User runs installer
   ↓
2. Installer detects OS and architecture
   ↓
3. Installer downloads and starts containers
   ↓
4. User opens http://localhost:3001
   ↓
5. User sees dashboard
```

### Automation Installation Flow

```
User clicks "Install Email Assistant"
    ↓
Frontend shows OAuth consent screen
    ↓
User authorizes Google
    ↓
Backend:
  - Stores tokens in OS secure storage
  - Creates n8n credential
  - Imports workflow
  - Creates PostgreSQL record
  ↓
Frontend shows automation as "Active"
```

### Account Disconnection Flow

```
User clicks "Disconnect Google"
    ↓
Frontend calls DELETE /api/v1/credentials/{id}
    ↓
Backend:
  - Revokes tokens in Credential Manager
  - Deletes PostgreSQL record
  - Deletes n8n credential
  ↓
Frontend shows account as "Disconnected"
```

## Deployment

### Docker Compose Services

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
  
  n8n:
    image: n8nio/n8n:1.121.3
    ports: ["5678:5678"]
  
  playwright:
    build: ./playwright
    ports: ["3000:3000"]
  
  backend:
    build: ./backend
    ports: ["8000:8000"]
  
  frontend:
    build: ./frontend
    ports: ["3001:80"]
```

## Development

### Running Development Servers

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
python -m app.database.migrations
```

## Future Enhancements

1. **Automations Marketplace**
   - Public registry of automations
   - User reviews and ratings
   - Version management

2. **Advanced OAuth Providers**
   - Microsoft OAuth
   - GitHub OAuth
   - Generic OAuth 2.0 support

3. **Workflow Editor**
   - Visual workflow builder
   - Template system
   - Version control

4. **Backup & Restore**
   - Local backup system
   - Encryption at rest
   - Automated backups

5. **User Management**
   - Multiple user profiles
   - Permission levels
   - Sharing capabilities