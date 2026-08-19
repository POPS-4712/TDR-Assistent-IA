"""
Credential Provider abstraction and implementations.

Provides a unified interface for different credential types:
- OAuth 2.0 providers (Google, etc.)
- API Key providers (OpenAI, Gemini, Anthropic, OpenRouter, etc.)
- Token providers (Telegram, etc.)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import httpx

from ...core.config import settings
from ...core.security import encryption
from .secure_store import SecureStore, get_secure_store

logger = logging.getLogger(__name__)


class CredentialType(Enum):
    """Types of credentials supported."""
    OAUTH = "oauth"
    API_KEY = "api_key"
    TOKEN = "token"
    STRUCTURED = "structured"


@dataclass
class CredentialMetadata:
    """Metadata for a credential (no secrets)."""
    provider: str
    account_identifier: str
    credential_type: CredentialType
    scopes: List[str] = field(default_factory=list)
    status: str = "active"
    expires_at: Optional[datetime] = None
    last_refresh: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthCredential:
    """OAuth credential with tokens."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: List[str]
    token_type: str = "Bearer"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApiKeyCredential:
    """API Key credential."""
    api_key: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenCredential:
    """Simple token credential."""
    token: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class CredentialProvider(ABC):
    """Abstract base class for credential providers."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        self.secure_store = secure_store or get_secure_store()
        self.provider_name: str = ""
        self.credential_type: CredentialType = CredentialType.TOKEN
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate provider configuration (client IDs, endpoints, etc.)."""
        pass
    
    @abstractmethod
    async def get_authorization_url(self, scopes: List[str], state: str) -> str:
        """Get OAuth authorization URL (for OAuth providers)."""
        pass
    
    @abstractmethod
    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> Any:
        """Exchange authorization code for tokens (for OAuth providers)."""
        pass
    
    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> Any:
        """Refresh access tokens using refresh token."""
        pass
    
    @abstractmethod
    async def revoke_tokens(self, tokens: Any) -> bool:
        """Revoke tokens with provider (if supported)."""
        pass
    
    @abstractmethod
    async def validate_credential(self, credential: Any) -> bool:
        """Validate a credential by making a test API call."""
        pass
    
    @abstractmethod
    def get_n8n_credential_type(self) -> str:
        """Get the n8n credential type name."""
        pass
    
    @abstractmethod
    def build_n8n_credentials(self, credential: Any) -> Dict[str, Any]:
        """Build n8n credential payload from stored credential."""
        pass
    
    def _get_storage_key(self, account_identifier: str, secret_type: str) -> str:
        """Generate storage key for secure store."""
        return f"{self.provider_name}:{account_identifier}:{secret_type}"


class OAuthProvider(CredentialProvider):
    """Base class for OAuth 2.0 providers."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.credential_type = CredentialType.OAUTH
        self.auth_url: str = ""
        self.token_url: str = ""
        self.revoke_url: Optional[str] = None
        self.userinfo_url: Optional[str] = None
        self.client_id: str = ""
        self.client_secret: str = ""
        self.default_scopes: List[str] = []
    
    async def validate_config(self) -> bool:
        """Validate OAuth configuration."""
        if not self.client_id or not self.client_secret:
            logger.warning(f"{self.provider_name}: Missing client_id or client_secret")
            return False
        if not self.auth_url or not self.token_url:
            logger.warning(f"{self.provider_name}: Missing auth_url or token_url")
            return False
        return True
    
    async def get_authorization_url(self, scopes: List[str], state: str) -> str:
        """Generate OAuth authorization URL with PKCE."""
        code_verifier = encryption.generate_code_verifier()
        code_challenge = encryption.generate_code_challenge(code_verifier)
        
        # Store code_verifier with state for later validation
        storage_key = self._get_storage_key(f"oauth_state:{state}", "code_verifier")
        await self.secure_store.set(storage_key, code_verifier)
        
        scope_str = " ".join(scopes) if scopes else " ".join(self.default_scopes)
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/credentials/{self.provider_name}/callback"
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope_str,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.auth_url}?{query}"
    
    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> OAuthCredential:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            })
            response.raise_for_status()
            data = response.json()
        
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return OAuthCredential(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=expires_at,
            scopes=data.get("scope", "").split() if data.get("scope") else self.default_scopes,
            token_type=data.get("token_type", "Bearer"),
        )
    
    async def refresh_tokens(self, refresh_token: str) -> OAuthCredential:
        """Refresh access token using refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            response.raise_for_status()
            data = response.json()
        
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return OAuthCredential(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=expires_at,
            scopes=data.get("scope", "").split() if data.get("scope") else self.default_scopes,
            token_type=data.get("token_type", "Bearer"),
        )
    
    async def revoke_tokens(self, tokens: OAuthCredential) -> bool:
        """Revoke tokens with provider if revoke endpoint exists."""
        if not self.revoke_url:
            logger.info(f"{self.provider_name}: No revoke endpoint configured")
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.revoke_url, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "token": tokens.access_token,
                })
                response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"{self.provider_name}: Failed to revoke tokens remotely: {e}")
            return False
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from provider."""
        if not self.userinfo_url:
            return {}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()


class ApiKeyProvider(CredentialProvider):
    """Base class for API Key providers."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.credential_type = CredentialType.API_KEY
        self.api_base_url: str = ""
        self.auth_header: str = "Authorization"
        self.auth_prefix: str = "Bearer"
        self.validation_endpoint: str = ""
    
    async def validate_config(self) -> bool:
        """Validate API key provider configuration."""
        if not self.api_base_url:
            logger.warning(f"{self.provider_name}: Missing api_base_url")
            return False
        return True
    
    async def get_authorization_url(self, scopes: List[str], state: str) -> str:
        """API key providers don't use OAuth flow."""
        raise NotImplementedError("API key providers don't use OAuth authorization")
    
    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> Any:
        """API key providers don't use OAuth flow."""
        raise NotImplementedError("API key providers don't use OAuth code exchange")
    
    async def refresh_tokens(self, refresh_token: str) -> Any:
        """API keys don't typically refresh."""
        raise NotImplementedError("API keys don't use token refresh")
    
    async def revoke_tokens(self, tokens: Any) -> bool:
        """API keys can't be revoked remotely."""
        return True
    
    async def validate_credential(self, credential: ApiKeyCredential) -> bool:
        """Validate API key by making a test request."""
        if not self.validation_endpoint:
            return True  # Can't validate without endpoint
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {self.auth_header: f"{self.auth_prefix} {credential.api_key}"}
                response = await client.get(
                    f"{self.api_base_url}{self.validation_endpoint}",
                    headers=headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"{self.provider_name}: Credential validation failed: {e}")
            return False


class TokenProvider(CredentialProvider):
    """Base class for simple token providers."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.credential_type = CredentialType.TOKEN
        self.api_base_url: str = ""
        self.validation_endpoint: str = ""
    
    async def validate_config(self) -> bool:
        """Validate token provider configuration."""
        if not self.api_base_url:
            logger.warning(f"{self.provider_name}: Missing api_base_url")
            return False
        return True
    
    async def get_authorization_url(self, scopes: List[str], state: str) -> str:
        """Token providers don't use OAuth flow."""
        raise NotImplementedError("Token providers don't use OAuth authorization")
    
    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> Any:
        """Token providers don't use OAuth flow."""
        raise NotImplementedError("Token providers don't use OAuth code exchange")
    
    async def refresh_tokens(self, refresh_token: str) -> Any:
        """Tokens don't typically refresh."""
        raise NotImplementedError("Tokens don't use token refresh")
    
    async def revoke_tokens(self, tokens: Any) -> bool:
        """Tokens can't be revoked remotely."""
        return True
    
    async def validate_credential(self, credential: TokenCredential) -> bool:
        """Validate token by making a test request."""
        if not self.validation_endpoint:
            return True  # Can't validate without endpoint
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {credential.token}"}
                response = await client.get(
                    f"{self.api_base_url}{self.validation_endpoint}",
                    headers=headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"{self.provider_name}: Credential validation failed: {e}")
            return False


class CredentialProviderRegistry:
    """Registry for credential providers."""
    
    def __init__(self):
        self._providers: Dict[str, CredentialProvider] = {}
    
    def register(self, provider: CredentialProvider) -> None:
        """Register a provider."""
        self._providers[provider.provider_name] = provider
        logger.info(f"Registered credential provider: {provider.provider_name}")
    
    def get(self, provider_name: str) -> Optional[CredentialProvider]:
        """Get a provider by name."""
        return self._providers.get(provider_name)
    
    def list(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def get_by_type(self, credential_type: CredentialType) -> List[CredentialProvider]:
        """Get all providers of a specific type."""
        return [p for p in self._providers.values() if p.credential_type == credential_type]


# Global registry instance
provider_registry = CredentialProviderRegistry()