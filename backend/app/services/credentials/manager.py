"""
Credential Manager for Automation Center.

Orchestrates credential management across:
- Secure storage (OS-specific)
- Provider implementations (OAuth, API Key, Token)
- PostgreSQL metadata
- n8n credential integration
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .secure_store import SecureStore, get_secure_store
from .providers import (
    CredentialProvider,
    CredentialProviderRegistry,
    CredentialType,
    OAuthCredential,
    ApiKeyCredential,
    TokenCredential,
    provider_registry,
)
from .google_provider import GoogleOAuthProvider
from .api_key_providers import (
    OpenAIProvider,
    GeminiProvider,
    AnthropicProvider,
    OpenRouterProvider,
)
from .telegram_provider import TelegramProvider
from .structured_providers import StructuredSecretCredential, StructuredSecretProvider
from ..n8n.client import N8NClient
from ...database.db import get_session
from ...database.models import Credential as CredentialModel
from ...core.config import settings
from ...core.security import encryption, log_sanitizer

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Main credential manager orchestrating all credential operations.
    
    Responsibilities:
    - Coordinate between providers, secure store, PostgreSQL, and n8n
    - Manage credential lifecycle (create, read, update, delete, refresh)
    - Ensure secrets never leave secure storage
    - Maintain metadata in PostgreSQL
    - Sync credentials with n8n
    """
    
    def __init__(
        self,
        secure_store: Optional[SecureStore] = None,
        provider_registry: Optional[CredentialProviderRegistry] = None,
        n8n_client: Optional[N8NClient] = None,
    ):
        self.secure_store = secure_store or get_secure_store()
        # Use imported global provider_registry if not provided
        from .providers import provider_registry as global_provider_registry
        self.provider_registry = provider_registry or global_provider_registry
        self.n8n_client = n8n_client
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the credential manager and all providers."""
        if self._initialized:
            return
        
        # Initialize secure store
        # (KeyringSecureStore initializes on first use)
        
        # Initialize n8n client if not provided
        if not self.n8n_client:
            self.n8n_client = N8NClient()
        
        # Validate all provider configurations
        for provider_name, provider in self.provider_registry._providers.items():
            try:
                valid = await provider.validate_config()
                if not valid:
                    logger.warning(f"Provider {provider_name} configuration invalid")
            except Exception as e:
                logger.error(f"Failed to validate provider {provider_name}: {e}")
        
        self._initialized = True
        logger.info("Credential Manager initialized successfully")
    
    # ============================================================
    # OAuth Flow Methods
    # ============================================================
    
    async def start_oauth_flow(
        self,
        provider_name: str,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Start OAuth authorization flow.
        
        Returns authorization URL and state for the frontend.
        """
        await self.initialize()
        
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        if provider.credential_type != CredentialType.OAUTH:
            raise ValueError(f"Provider {provider_name} is not an OAuth provider")
        
        # Generate state for CSRF protection
        state = encryption.generate_oauth_state()
        
        # Get authorization URL
        auth_url = await provider.get_authorization_url(scopes or [], state)
        
        return {
            "auth_url": auth_url,
            "state": state,
            "provider": provider_name,
        }
    
    async def handle_oauth_callback(
        self,
        provider_name: str,
        code: str,
        state: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback from provider.
        
        Exchanges code for tokens, stores credentials, creates n8n credential,
        and saves metadata to PostgreSQL.
        """
        await self.initialize()
        
        if error:
            logger.error(f"OAuth error from {provider_name}: {error}")
            raise ValueError(f"OAuth error: {error}")
        
        provider = self.provider_registry.get(provider_name)
        if not provider or not isinstance(provider, GoogleOAuthProvider):
            raise ValueError(f"Unknown or unsupported OAuth provider: {provider_name}")
        
        # Retrieve code_verifier from secure store
        storage_key = provider._get_storage_key(f"oauth_state:{state}", "code_verifier")
        code_verifier = await self.secure_store.get(storage_key)
        
        if not code_verifier:
            raise ValueError("Invalid or expired state")
        
        # Clean up state
        await self.secure_store.delete(storage_key)
        
        # Exchange code for tokens
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/credentials/{provider_name}/callback"
        oauth_credential = await provider.exchange_code(code, code_verifier, redirect_uri)
        
        # Get user info to identify account
        user_info = await provider.get_user_info(oauth_credential.access_token)
        account_identifier = user_info.get("email") or user_info.get("id") or "unknown"
        
        # Store tokens in secure store
        await provider.store_credential(account_identifier, oauth_credential)
        
        # Create/update n8n credential
        n8n_credential_id = await self._create_or_update_n8n_credential(
            provider, account_identifier, oauth_credential
        )
        
        # Save metadata to PostgreSQL
        credential_id = await self._save_credential_metadata(
            provider_name=provider_name,
            account_identifier=account_identifier,
            scopes=oauth_credential.scopes,
            n8n_credential_id=n8n_credential_id,
            expires_at=oauth_credential.expires_at,
        )
        
        return {
            "success": True,
            "credential_id": credential_id,
            "provider": provider_name,
            "account_identifier": account_identifier,
            "status": "active",
        }
    
    # ============================================================
    # API Key / Token Methods
    # ============================================================
    
    async def store_api_key(
        self,
        provider_name: str,
        account_identifier: str,
        api_key: str
    ) -> Dict[str, Any]:
        """Store an API key credential."""
        await self.initialize()
        
        provider = self.provider_registry.get(provider_name)
        if not provider or provider.credential_type != CredentialType.API_KEY:
            raise ValueError(f"Unknown or unsupported API key provider: {provider_name}")
        
        # Validate the API key
        credential = ApiKeyCredential(api_key=api_key)
        valid = await provider.validate_credential(credential)
        if not valid:
            raise ValueError(f"Invalid API key for {provider_name}")
        
        # Store in secure store
        await provider.store_credential(account_identifier, credential)
        
        # Create n8n credential
        n8n_credential_id = await self._create_or_update_n8n_credential(
            provider, account_identifier, credential
        )
        
        # Save metadata to PostgreSQL
        credential_id = await self._save_credential_metadata(
            provider_name=provider_name,
            account_identifier=account_identifier,
            scopes=[],
            n8n_credential_id=n8n_credential_id,
        )
        
        return {
            "success": True,
            "credential_id": credential_id,
            "provider": provider_name,
            "account_identifier": account_identifier,
            "status": "active",
        }
    
    async def store_token(
        self,
        provider_name: str,
        account_identifier: str,
        token: str
    ) -> Dict[str, Any]:
        """Store a simple token credential (e.g., Telegram bot token)."""
        await self.initialize()
        
        provider = self.provider_registry.get(provider_name)
        if not provider or provider.credential_type != CredentialType.TOKEN:
            raise ValueError(f"Unknown or unsupported token provider: {provider_name}")
        
        # Validate the token
        credential = TokenCredential(token=token)
        valid = await provider.validate_credential(credential)
        if not valid:
            raise ValueError(f"Invalid token for {provider_name}")
        
        # Store in secure store
        await provider.store_credential(account_identifier, credential)
        
        # Create n8n credential
        n8n_credential_id = await self._create_or_update_n8n_credential(
            provider, account_identifier, credential
        )
        
        # Save metadata to PostgreSQL
        credential_id = await self._save_credential_metadata(
            provider_name=provider_name,
            account_identifier=account_identifier,
            scopes=[],
            n8n_credential_id=n8n_credential_id,
        )
        
        return {
            "success": True,
            "credential_id": credential_id,
            "provider": provider_name,
            "account_identifier": account_identifier,
            "status": "active",
        }

    async def store_structured_credential(
        self,
        provider_name: str,
        account_identifier: str,
        secrets: Dict[str, str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Store a structured credential without persisting its secret components."""
        await self.initialize()
        provider = self.provider_registry.get(provider_name)
        if not isinstance(provider, StructuredSecretProvider):
            raise ValueError(f"Unknown or unsupported structured provider: {provider_name}")

        expected = set(provider.secret_keys)
        if set(secrets) != expected or any(not str(value).strip() for value in secrets.values()):
            raise ValueError(f"{provider_name} requires exactly: {sorted(expected)}")
        public_metadata = provider.public_metadata(metadata)
        credential = StructuredSecretCredential(secrets=secrets, metadata=public_metadata)
        if not await provider.validate_credential(credential):
            raise ValueError(f"Credential validation failed for {provider_name}")

        await provider.store_credential(account_identifier, credential)
        n8n_credential_id = await self._create_or_update_n8n_credential(
            provider, account_identifier, credential
        )
        credential_id = await self._save_credential_metadata(
            provider_name=provider_name,
            account_identifier=account_identifier,
            scopes=[],
            n8n_credential_id=n8n_credential_id,
            credential_metadata={
                **public_metadata,
                "_n8n_credential_type": provider.get_n8n_credential_type(),
            },
            last_validation=datetime.utcnow(),
        )
        return {
            "success": True,
            "credential_id": credential_id,
            "provider": provider_name,
            "account_identifier": account_identifier,
            "status": "active",
            "metadata": public_metadata,
        }
    
    # ============================================================
    # Credential Retrieval & Management
    # ============================================================
    
    async def _get_credential_record(self, credential_id: str) -> Optional[CredentialModel]:
        """Load the internal record, including n8n reference, for backend-only use."""
        async with get_session() as session:
            result = await session.execute(
                select(CredentialModel).where(CredentialModel.id == uuid.UUID(credential_id))
            )
            return result.scalar_one_or_none()

    @staticmethod
    def _public_credential_metadata(credential: CredentialModel) -> Dict[str, Any]:
        """Serialize account metadata without a secret or internal n8n reference."""
        return {
            "id": str(credential.id),
            "provider": credential.provider,
            "account_identifier": credential.account_identifier,
            "scopes": credential.scopes,
            "status": credential.status,
            "metadata": {
                key: value
                for key, value in (credential.credential_metadata or {}).items()
                if not key.startswith("_")
            },
            "last_refresh": credential.last_refresh.isoformat() if credential.last_refresh else None,
            "last_validation": credential.last_validation.isoformat() if credential.last_validation else None,
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "created_at": credential.created_at.isoformat(),
            "updated_at": credential.updated_at.isoformat(),
        }

    async def get_credential_metadata(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Get public credential metadata; secret and n8n ID stay internal."""
        await self.initialize()
        credential = await self._get_credential_record(credential_id)
        return self._public_credential_metadata(credential) if credential else None

    async def list_credentials(self) -> List[Dict[str, Any]]:
        """List public credential metadata only."""
        await self.initialize()
        async with get_session() as session:
            result = await session.execute(
                select(CredentialModel).order_by(CredentialModel.created_at.desc())
            )
            return [self._public_credential_metadata(item) for item in result.scalars().all()]
    
    async def validate_credential(self, credential_id: str) -> Dict[str, Any]:
        """Validate a credential without returning its secret material."""
        await self.initialize()
        record = await self._get_credential_record(credential_id)
        if not record:
            raise ValueError(f"Credential not found: {credential_id}")
        provider = self.provider_registry.get(record.provider)
        if not provider:
            raise ValueError(f"Provider not found: {record.provider}")

        if record.expires_at and record.expires_at <= datetime.utcnow():
            await self._update_credential_metadata(
                credential_id, status="reauth_required", last_validation=datetime.utcnow()
            )
            return {"credential_id": credential_id, "result": "EXPIRED", "status": "reauth_required"}

        if isinstance(provider, StructuredSecretProvider):
            credential = await provider.retrieve_credential(
                record.account_identifier, record.credential_metadata or {}
            )
        else:
            credential = await provider.retrieve_credential(record.account_identifier)

        valid = bool(credential and await provider.validate_credential(credential))
        status = "active" if valid else "error"
        await self._update_credential_metadata(
            credential_id, status=status, last_validation=datetime.utcnow()
        )
        return {
            "credential_id": credential_id,
            "result": "VALID" if valid else "INVALID",
            "status": status,
        }

    async def refresh_credential(self, credential_id: str) -> Dict[str, Any]:
        """Refresh a credential (OAuth tokens or re-validate API keys)."""
        await self.initialize()
        
        record = await self._get_credential_record(credential_id)
        if not record:
            raise ValueError(f"Credential not found: {credential_id}")
        
        provider = self.provider_registry.get(record.provider)
        if not provider:
            raise ValueError(f"Provider not found: {record.provider}")
        
        account_identifier = record.account_identifier
        
        if provider.credential_type == CredentialType.OAUTH:
            # Refresh OAuth tokens
            if isinstance(provider, GoogleOAuthProvider):
                new_credential = await provider.refresh_if_needed(account_identifier)
                if new_credential:
                    # Update n8n credential
                    await self._update_n8n_credential(
                        provider, record.n8n_credential_id, new_credential
                    )
                    # Update PostgreSQL
                    await self._update_credential_metadata(
                        credential_id,
                        expires_at=new_credential.expires_at,
                        last_refresh=datetime.utcnow(),
                    )
                    return {"success": True, "credential_id": credential_id, "status": "active"}
                else:
                    raise ValueError("Failed to refresh credential")
        
        elif provider.credential_type in [CredentialType.API_KEY, CredentialType.TOKEN]:
            # Re-validate API key/token
            if provider.credential_type == CredentialType.API_KEY:
                credential = await provider.retrieve_credential(account_identifier)
            else:
                credential = await provider.retrieve_credential(account_identifier)
            
            if credential and await provider.validate_credential(credential):
                await self._update_credential_metadata(
                    credential_id,
                    last_refresh=datetime.utcnow(),
                )
                return {"success": True, "credential_id": credential_id, "status": "active"}
            else:
                raise ValueError("Credential validation failed")
        
        raise ValueError(f"Unsupported credential type for refresh: {provider.credential_type}")
    
    async def revoke_credential(self, credential_id: str) -> Dict[str, Any]:
        """Revoke a credential completely."""
        await self.initialize()
        
        record = await self._get_credential_record(credential_id)
        if not record:
            raise ValueError(f"Credential not found: {credential_id}")
        
        provider = self.provider_registry.get(record.provider)
        if not provider:
            raise ValueError(f"Provider not found: {record.provider}")
        
        account_identifier = record.account_identifier
        n8n_credential_id = record.n8n_credential_id
        
        # Revoke with provider if supported
        if provider.credential_type == CredentialType.OAUTH:
            credential = await provider.retrieve_credential(account_identifier)
            if credential:
                await provider.revoke_tokens(credential)
        
        # Delete from secure store
        await provider.delete_credential(account_identifier)
        
        # Delete from n8n
        if n8n_credential_id and self.n8n_client:
            try:
                async with self.n8n_client as client:
                    await client.delete_credential(n8n_credential_id)
            except Exception as e:
                logger.warning(f"Failed to delete n8n credential {n8n_credential_id}: {e}")
        
        # Update PostgreSQL status to revoked
        async with get_session() as session:
            await session.execute(
                CredentialModel.__table__.update()
                .where(CredentialModel.id == uuid.UUID(credential_id))
                .values(status="revoked", n8n_credential_id=None)
            )
        
        return {"success": True, "credential_id": credential_id}
    
    # ============================================================
    # n8n Integration
    # ============================================================
    
    async def _create_or_update_n8n_credential(
        self,
        provider: CredentialProvider,
        account_identifier: str,
        credential: Any
    ) -> Optional[str]:
        """Create or update credential in n8n."""
        if not self.n8n_client:
            return None
        
        try:
            async with self.n8n_client as client:
                n8n_credentials = provider.build_n8n_credentials(credential)
                credential_type = provider.get_n8n_credential_type()
                name = f"automation-center-{provider.provider_name}-{account_identifier}"
                
                # Try to find existing credential
                # For now, always create new - n8n doesn't have a good "get by name" API
                n8n_credential_id = await client.create_credential(
                    credential_type=credential_type,
                    credentials=n8n_credentials,
                    name=name,
                )
                return n8n_credential_id
        except Exception as e:
            logger.error(f"Failed to create n8n credential: {e}")
            return None
    
    async def _update_n8n_credential(
        self,
        provider: CredentialProvider,
        n8n_credential_id: str,
        credential: Any
    ) -> bool:
        """Update existing credential in n8n."""
        if not self.n8n_client or not n8n_credential_id:
            return False
        
        try:
            async with self.n8n_client as client:
                n8n_credentials = provider.build_n8n_credentials(credential)
                await client.update_credential(n8n_credential_id, n8n_credentials)
                return True
        except Exception as e:
            logger.error(f"Failed to update n8n credential {n8n_credential_id}: {e}")
            return False
    
    # ============================================================
    # PostgreSQL Metadata Operations
    # ============================================================
    
    async def _save_credential_metadata(
        self,
        provider_name: str,
        account_identifier: str,
        scopes: List[str],
        n8n_credential_id: Optional[str],
        expires_at: Optional[datetime] = None,
        credential_metadata: Optional[Dict[str, Any]] = None,
        last_validation: Optional[datetime] = None,
    ) -> str:
        """Save credential metadata to PostgreSQL."""
        import uuid
        
        async with get_session() as session:
            # Check if credential already exists
            result = await session.execute(
                select(CredentialModel).where(
                    CredentialModel.provider == provider_name,
                    CredentialModel.account_identifier == account_identifier
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.scopes = scopes
                existing.status = "active"
                existing.n8n_credential_id = n8n_credential_id
                existing.expires_at = expires_at
                existing.credential_metadata = credential_metadata or {}
                existing.last_validation = last_validation
                existing.updated_at = datetime.utcnow()
                credential_id = str(existing.id)
            else:
                # Create new
                credential_id = str(uuid.uuid4())
                new_credential = CredentialModel(
                    id=uuid.UUID(credential_id),
                    provider=provider_name,
                    account_identifier=account_identifier,
                    scopes=scopes,
                    status="active",
                    n8n_credential_id=n8n_credential_id,
                    credential_metadata=credential_metadata or {},
                    last_validation=last_validation,
                    expires_at=expires_at,
                )
                session.add(new_credential)
            
            return credential_id
    
    async def _update_credential_metadata(
        self,
        credential_id: str,
        expires_at: Optional[datetime] = None,
        last_refresh: Optional[datetime] = None,
        last_validation: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> None:
        """Update credential metadata in PostgreSQL."""
        async with get_session() as session:
            update_data = {"updated_at": datetime.utcnow()}
            if expires_at:
                update_data["expires_at"] = expires_at
            if last_refresh:
                update_data["last_refresh"] = last_refresh
            if last_validation:
                update_data["last_validation"] = last_validation
            if status:
                update_data["status"] = status
            
            await session.execute(
                CredentialModel.__table__.update()
                .where(CredentialModel.id == uuid.UUID(credential_id))
                .values(**update_data)
            )
    
    # ============================================================
    # Provider Information
    # ============================================================
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """List safe provider capabilities for Accounts without configuration data."""
        labels = {
            "google": "Google", "gemini": "Google Gemini", "telegram": "Telegram",
            "whatsapp_cloud": "WhatsApp Cloud API", "header_auth": "Header Auth",
            "openai": "OpenAI", "anthropic": "Anthropic", "openrouter": "OpenRouter",
        }
        descriptions = {
            "whatsapp_cloud": "Token de sistema Meta, Phone Number ID y versión de Graph API.",
            "header_auth": "Header HTTP configurable; el valor permanece en el almacenamiento seguro.",
        }
        return [
            {
                "name": name,
                "display_name": labels.get(name, name.replace("_", " ").title()),
                "credential_type": provider.credential_type.value,
                "scopes": list(getattr(provider, "default_scopes", [])),
                "description": descriptions.get(name),
            }
            for name, provider in self.provider_registry._providers.items()
        ]
    
    def get_provider(self, provider_name: str) -> Optional[CredentialProvider]:
        """Get a provider by name."""
        return self.provider_registry.get(provider_name)


# Global instance
credential_manager = CredentialManager()