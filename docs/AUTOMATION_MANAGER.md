# Automation Manager Documentation

## Overview

The Automation Manager is the core component responsible for managing the complete lifecycle of automations in the Automation Center. It orchestrates the interaction between the manifest system, n8n workflow engine, credential management, and PostgreSQL persistence.

## Architecture

```
Frontend
    ↓
FastAPI (API Routes)
    ↓
AutomationManager
    ├── ManifestManager (discovery, validation, versioning)
    ├── CredentialManager (credential mapping, assignment)
    ├── N8NClient (workflow import, activate, deactivate, delete)
    └── PostgreSQL (metadata, status, relationships)
```

## Components

### 1. Manifest Manager (`manifest_manager.py`)

Responsible for:
- Discovering manifests in `automations/` directory
- Loading and parsing YAML manifests
- Validating manifest schema (strict validation)
- Checking for unique IDs
- Checking version compatibility
- Verifying workflow file exists
- Validating provider requirements
- Detecting corrupted manifests
- Detecting missing dependencies
- Version comparison for updates

### 2. Automation Manager (`manager.py`)

Responsible for:
- Automation installation (with rollback on failure)
- Enabling/disabling automations
- Uninstalling automations (preserves global credentials)
- Credential mapping and assignment
- Status state machine enforcement
- Version checking
- Operation logging (no secrets)

### 3. N8N Client (`n8n/client.py`)

Responsible for:
- Workflow import/export
- Workflow activation/deactivation
- Workflow deletion
- Credential management in n8n
- Execution monitoring

### 4. Credential Manager (`credentials/manager.py`)

Responsible for:
- Secure credential storage (OS keyring)
- Provider implementations (OAuth, API Key, Token)
- PostgreSQL metadata (NO secrets)
- n8n credential synchronization

## Manifest Schema

### Required Fields

```yaml
id: string (alphanumeric, hyphens, underscores only)
name: string
description: string
version: string (semver-like, at least major.minor)
status: enum [discovered, installed, enabled, disabled, error, uninstalling]
category: string
icon: string

requirements:
  - provider: string
    type: enum [oauth2, api_key, token, connection]
    scopes: [string] (optional)

dependencies: [string] (automation IDs)

n8n:
  workflow_file: string (relative path, no traversal)
  credential_mapping:
    n8n_credential_name: provider_name

setup:
  - description: string

teardown:
  - description: string

metadata:
  auto_enable: boolean (default: false)
  source_workflow: string (optional)
  test_only: boolean (default: false)
```

### Example Manifest

```yaml
id: email-assistant
name: Email Assistant
description: AI-powered email management
version: 1.0.0
status: disabled
category: communication
icon: mail

requirements:
  - provider: google
    type: oauth2
    scopes:
      - https://www.googleapis.com/auth/gmail.modify
      - https://www.googleapis.com/auth/calendar
  - provider: openrouter
    type: api_key
  - provider: postgresql
    type: connection

dependencies:
  - google-oauth2
  - postgresql

n8n:
  workflow_file: workflow.json
  credential_mapping:
    googleOAuth2Api: google
    openRouterApi: openrouter
    postgres: postgresql

setup:
  - description: "Configure Google OAuth2 credentials"
  - description: "Add OpenRouter API key"
  - description: "Set up PostgreSQL connection"

teardown:
  - description: "Deactivate workflow in n8n"
  - description: "Remove automation credentials mapping"
  - description: "Delete automation metadata"

metadata:
  auto_enable: false
  source_workflow: "01-email-manager.json"
```

## Installation Flow

```
install_automation(automation_id)
    ↓
1. Find manifest
2. Validate manifest (schema, dependencies, workflow)
3. Check not already installed
4. Check dependencies exist in database
5. Check required credentials exist (active)
6. Validate workflow JSON structure
7. Import workflow in n8n → get n8n_workflow_id
8. Assign credentials (map n8n credential names to n8n credential IDs)
9. Create/update automation record in PostgreSQL
10. Create automation_credentials relationships
11. Status = installed
12. If auto_enable: true → enable_automation()
```

### Rollback on Failure

If any step fails after workflow import:
1. Delete imported workflow from n8n
2. Update database status to `error`
3. Raise exception

## Credential Mapping

The manifest defines a `credential_mapping` that maps n8n credential names to provider names:

```yaml
credential_mapping:
  googleOAuth2Api: google      # n8n credential name → provider
  openRouterApi: openrouter
  postgres: postgresql
```

The Automation Manager:
1. Looks up active credentials for each provider in PostgreSQL
2. Gets the `n8n_credential_id` from credential metadata
3. Creates `automation_credentials` relationships
4. Updates n8n workflow with credential references (when supported)

**Security**: Secrets are NEVER stored in PostgreSQL or passed to frontend. Only metadata and n8n credential IDs are stored.

## Status State Machine

```
discovered
    ↓
installed
    ↓
enabled ←→ disabled
    ↓
uninstalling
    ↓
discovered (after uninstall)

error → installed (retry)
error → disabled (retry)
```

### Valid Transitions

| From | To |
|------|-----|
| discovered | installed, error |
| installed | enabled, disabled, uninstalling, error |
| enabled | disabled, uninstalling, error |
| disabled | enabled, uninstalling, error |
| uninstalling | discovered |
| error | installed, disabled |

Invalid transitions raise `ValueError`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/automations` | List all automations |
| GET | `/api/v1/automations/discover` | Discover automations from directory |
| GET | `/api/v1/automations/{id}` | Get automation details |
| POST | `/api/v1/automations/{id}/install` | Install automation |
| POST | `/api/v1/automations/{id}/enable` | Enable automation |
| POST | `/api/v1/automations/{id}/disable` | Disable automation |
| DELETE | `/api/v1/automations/{id}` | Uninstall automation |
| GET | `/api/v1/automations/{id}/logs` | Get execution logs |
| GET | `/api/v1/automations/updates/check` | Check for updates |

### Response Format

All responses follow this pattern:
```json
{
  "success": true,
  "automation_id": "email-assistant",
  "n8n_workflow_id": "n8n-wf-123",
  "status": "installed",
  "credentials_mapped": ["googleOAuth2Api", "openRouterApi"],
  "auto_enabled": false
}
```

Error responses:
```json
{
  "detail": "Missing required credentials: postgresql"
}
```

## Database Schema

### automations table

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(255) PK | Automation ID |
| name | VARCHAR(255) | Display name |
| description | TEXT | Description |
| version | VARCHAR(50) | Version string |
| status | VARCHAR(50) | Current status |
| manifest_url | VARCHAR(1000) | Path to manifest |
| dependencies | TEXT[] | Dependency IDs |
| n8n_workflow_id | VARCHAR(255) | n8n workflow ID |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |

### automation_credentials table

| Column | Type | Description |
|--------|------|-------------|
| automation_id | VARCHAR(255) FK | Automation ID |
| credential_id | UUID FK | Credential ID |
| created_at | TIMESTAMP | Creation time |

**CASCADE DELETE**: When automation is deleted, automation_credentials are deleted. Credentials table is NOT affected.

## Security

### Secrets Handling

- **NEVER** store secrets in PostgreSQL
- **NEVER** log secrets (tokens, API keys, OAuth codes, client secrets)
- **NEVER** return secrets in API responses
- Use `yaml.safe_load()` for manifest parsing (no code execution)
- Prevent path traversal in `workflow_file` paths
- Validate all inputs with Pydantic models

### Logging

Operations are logged with:
- `automation_id`
- `operation` (install, enable, disable, uninstall)
- `status` (success, error)
- `duration_ms`
- `error` (if failed, no secrets)

## Versioning

### Check for Updates

```python
updates = await automation_manager.check_for_updates()
# Returns: [{"automation_id": "...", "current_version": "1.0.0", "available_version": "1.1.0", "update_available": true}]
```

### Version Comparison

Semantic version comparison (major.minor.patch):
- `1.0.0` < `1.0.1` < `1.1.0` < `2.0.0`
- Missing parts treated as 0: `1.0` == `1.0.0`

**Auto-update is NOT implemented in this phase.** Updates are detected but require manual intervention.

## Uninstall Behavior

Uninstalling an automation:
1. Disables workflow (if enabled)
2. Deletes workflow from n8n
3. Deletes `automation_credentials` relationships
4. Deletes automation metadata from `automations` table
5. **PRESERVES** global credentials in `credentials` table

This is by design: credentials belong to the user, not to the automation.

## Testing

### Unit Tests

Run tests:
```bash
cd backend
pytest tests/test_automation_manager.py -v
```

Test coverage:
- ManifestManager: discovery, validation, versioning
- Manifest schema: valid/invalid manifests, path traversal
- AutomationStatus: valid/invalid transitions
- AutomationManager: install, enable, disable, uninstall, rollback
- Security: no secrets, path traversal, safe YAML

### Integration Tests

Integration tests require running services:
- PostgreSQL
- n8n
- Backend

```bash
docker compose up -d
cd backend
pytest tests/test_automation_manager.py::TestAutomationManager -v
```

## Existing Workflows

The following existing workflows are **preserved** and **NOT modified**:

- `workflows/01-email-manager.json`
- `workflows/02-laboral.json`
- `workflows/03-news.json`
- `workflows/04-personal-brand.json`
- `workflows/05-playwright-jobs.json`

These workflows remain in their original location. Migration to the new `automations/` structure will be a separate controlled phase.

## Test Automation

A test automation is provided at `automations/test-automation/`:

```
automations/test-automation/
├── manifest.yaml
├── workflow.json
└── README.md
```

This automation:
- Has NO credentials
- Has NO external services
- Uses only Manual Trigger → Set nodes
- Safe for testing full lifecycle: discover → validate → install → get → enable → disable → uninstall

## Docker Deployment

All services communicate via Docker network:

```yaml
services:
  backend:
    # ...
    environment:
      - N8N_API_URL=http://n8n:5678
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
  n8n:
    # ...
  postgres:
    # ...
```

**Never use `localhost` for internal service communication.**

## Troubleshooting

### Common Issues

1. **Manifest not discovered**
   - Check `automations/` directory structure
   - Verify `manifest.yaml` exists and is valid YAML
   - Check logs for validation errors

2. **Installation fails: missing credentials**
   - Ensure required credentials are configured in Credential Manager
   - Check credential status is `active`
   - Verify provider name matches manifest

3. **Enable fails: n8n activation error**
   - Check n8n is healthy: `GET /healthz`
   - Verify workflow was imported correctly
   - Check n8n logs for credential reference errors

4. **Version mismatch**
   - Run `GET /api/v1/automations/updates/check`
   - Manual update required (not automated in this phase)

### Logs

Check backend logs:
```bash
docker compose logs -f backend
```

Look for:
```
Automation operation completed: {"automation_id": "...", "operation": "install", "status": "success", "duration_ms": 1234.56}
Automation operation failed: {"automation_id": "...", "operation": "install", "status": "error", "duration_ms": 567.89, "error": "..."}
```

## Future Enhancements (Phase 2.7+)

- Automated updates with rollback
- Workflow migration from legacy `workflows/` directory
- Automation templates/marketplace
- Execution scheduling and monitoring
- Multi-environment support (dev/staging/prod)
- Audit trail for all operations