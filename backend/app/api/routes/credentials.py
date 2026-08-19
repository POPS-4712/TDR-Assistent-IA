"""
Credential endpoints for Automation Center.

Uses the new CredentialManager architecture with:
- SecureStore for secret storage
- Provider registry for extensible credential types
- PostgreSQL for metadata only
- n8n integration for workflow credentials
"""

import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import logger
from ...core.security import encryption
from ...services.credentials.manager import credential_manager
from ...services.credentials.providers import CredentialType, provider_registry
from ...schemas.credentials import StructuredCredentialRequest, CredentialValidationResponse

router = APIRouter()


# Request/Response models
class ConnectRequest(BaseModel):
    provider: str
    scopes: Optional[List[str]] = None


class ApiKeyRequest(BaseModel):
    provider: str
    account_identifier: str
    api_key: str


class TokenRequest(BaseModel):
    provider: str
    account_identifier: str
    token: str


class RefreshRequest(BaseModel):
    credential_id: str


@router.get("", response_model=Dict[str, Any])
async def list_credentials() -> Dict[str, Any]:
    """
    List all credentials (metadata only).
    
    Returns credential metadata without exposing secrets.
    """
    try:
        credentials = await credential_manager.list_credentials()
        return {"credentials": credentials, "total": len(credentials)}
    except Exception as e:
        logger.error(f"Failed to list credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers", response_model=Dict[str, Any])
async def list_providers() -> Dict[str, Any]:
    """
    List all available credential providers.
    """
    try:
        providers = credential_manager.list_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect", response_model=Dict[str, Any])
async def connect_credential(request: ConnectRequest) -> Dict[str, Any]:
    """
    Start credential connection flow.
    
    For OAuth providers, generates and returns the authorization URL.
    For API key/token providers, returns instructions.
    
    Args:
        provider: Provider name (e.g., google, openai, telegram)
        scopes: Optional list of scopes for OAuth providers
        
    Returns:
        Authorization URL for OAuth flow or instructions for other types
    """
    try:
        provider = provider_registry.get(request.provider)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
        
        if provider.credential_type == CredentialType.OAUTH:
            result = await credential_manager.start_oauth_flow(
                request.provider,
                request.scopes
            )
            return result
        elif provider.credential_type == CredentialType.API_KEY:
            return {
                "type": "api_key",
                "message": f"Use POST /api/v1/credentials/api-key to store {request.provider} API key",
                "provider": request.provider,
            }
        elif provider.credential_type == CredentialType.TOKEN:
            return {
                "type": "token",
                "message": f"Use POST /api/v1/credentials/token to store {request.provider} token",
                "provider": request.provider,
            }
        elif provider.credential_type == CredentialType.STRUCTURED:
            return {
                "type": "structured",
                "message": f"Use POST /api/v1/credentials/structured to connect {request.provider}",
                "provider": request.provider,
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider type: {provider.credential_type}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start credential connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api-key", response_model=Dict[str, Any])
async def store_api_key(request: ApiKeyRequest) -> Dict[str, Any]:
    """
    Store an API key credential.
    
    Args:
        provider: Provider name (e.g., openai, gemini, anthropic, openrouter)
        account_identifier: Identifier for the account (e.g., email, username)
        api_key: The API key to store
        
    Returns:
        Credential metadata
    """
    try:
        result = await credential_manager.store_api_key(
            request.provider,
            request.account_identifier,
            request.api_key
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/token", response_model=Dict[str, Any])
async def store_token(request: TokenRequest) -> Dict[str, Any]:
    """
    Store a token credential (e.g., Telegram bot token).
    
    Args:
        provider: Provider name (e.g., telegram)
        account_identifier: Identifier for the account (e.g., bot username)
        token: The token to store
        
    Returns:
        Credential metadata
    """
    try:
        result = await credential_manager.store_token(
            request.provider,
            request.account_identifier,
            request.token
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/structured", response_model=Dict[str, Any])
async def store_structured_credential(request: StructuredCredentialRequest) -> Dict[str, Any]:
    """Persist structured secrets directly in secure storage and return metadata only."""
    try:
        return await credential_manager.store_structured_credential(
            request.provider,
            request.account_identifier,
            request.secrets,
            request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Failed to store structured credential")
        raise HTTPException(status_code=500, detail="Credential connection failed")


@router.post("/{credential_id}/validate", response_model=CredentialValidationResponse)
async def validate_credential(credential_id: str) -> CredentialValidationResponse:
    """Validate a stored credential without exposing its secret material."""
    try:
        return CredentialValidationResponse(**await credential_manager.validate_credential(credential_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Credential validation failed")
        raise HTTPException(status_code=500, detail="Credential validation failed")


@router.get("/{provider}/authorize", response_model=Dict[str, str])
async def generate_oauth_url(
    provider: str,
    scopes: Optional[str] = Query(None, description="Comma-separated scopes")
) -> Dict[str, str]:
    """
    Generate OAuth authorization URL for a provider.
    
    Args:
        provider: Provider name (e.g., google)
        scopes: Optional comma-separated scopes
        
    Returns:
        Authorization URL with PKCE parameters
    """
    try:
        scope_list = scopes.split(",") if scopes else None
        result = await credential_manager.start_oauth_flow(provider, scope_list)
        return {"auth_url": result["auth_url"], "state": result["state"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{provider}/callback", response_model=Dict[str, Any])
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Handle OAuth callback from provider.
    
    Validates state, exchanges code for tokens, stores credentials,
    creates n8n credential, and saves metadata to PostgreSQL.
    
    Args:
        provider: Provider name (e.g., google)
        code: Authorization code from provider
        state: OAuth state for validation
        error: Error message if authorization failed
        
    Returns:
        Credential information
    """
    try:
        result = await credential_manager.handle_oauth_callback(
            provider, code, state, error
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{credential_id}/refresh", response_model=Dict[str, Any])
async def refresh_credential(credential_id: str) -> Dict[str, Any]:
    """
    Refresh a credential token.
    
    For OAuth: refreshes access token using refresh token
    For API keys/tokens: re-validates the credential
    
    Args:
        credential_id: ID of the credential to refresh
        
    Returns:
        Refresh result
    """
    try:
        result = await credential_manager.refresh_credential(credential_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refresh credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{credential_id}", response_model=Dict[str, Any])
async def revoke_credential(credential_id: str) -> Dict[str, Any]:
    """
    Revoke a credential completely.
    
    - Revokes tokens with provider (if supported)
    - Deletes from secure store
    - Deletes from n8n
    - Marks as revoked in PostgreSQL
    
    Args:
        credential_id: ID of the credential to revoke
        
    Returns:
        Revocation result
    """
    try:
        result = await credential_manager.revoke_credential(credential_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to revoke credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{credential_id}", response_model=Dict[str, Any])
async def get_credential(credential_id: str) -> Dict[str, Any]:
    """
    Get credential metadata by ID.
    
    Returns metadata only - no secrets.
    
    Args:
        credential_id: ID of the credential
        
    Returns:
        Credential metadata
    """
    try:
        metadata = await credential_manager.get_credential_metadata(credential_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Credential not found")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))