"""
Google OAuth 2.0 Provider Implementation.

Supports Google OAuth with PKCE for secure authorization flow.
Configurable scopes for Gmail, Calendar, Tasks, Drive, etc.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .providers import (
    OAuthProvider,
    OAuthCredential,
    CredentialType,
    provider_registry,
)
from .secure_store import SecureStore, get_secure_store
from ...core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider with PKCE support."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "google"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.revoke_url = "https://oauth2.googleapis.com/revoke"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # Load from settings/environment
        self.client_id = settings.GOOGLE_CLIENT_ID or ""
        self.client_secret = settings.GOOGLE_CLIENT_SECRET or ""
        
        # Default scopes - can be overridden per-request
        self.default_scopes = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for Google OAuth."""
        return "googleOAuth2Api"
    
    def build_n8n_credentials(self, credential: OAuthCredential) -> Dict[str, Any]:
        """Build n8n credential payload from OAuth credential."""
        return {
            "accessToken": credential.access_token,
            "refreshToken": credential.refresh_token,
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "scope": " ".join(credential.scopes),
        }
    
    async def validate_config(self) -> bool:
        """Validate Google OAuth configuration."""
        if not self.client_id:
            logger.warning("Google OAuth: GOOGLE_CLIENT_ID not configured")
            return False
        if not self.client_secret:
            logger.warning("Google OAuth: GOOGLE_CLIENT_SECRET not configured")
            return False
        return await super().validate_config()
    
    async def get_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from Google."""
        user_info = await self.get_user_info(access_token)
        return user_info.get("email")
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: OAuthCredential
    ) -> None:
        """Store OAuth credential in secure store."""
        # Store access token
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "access_token"),
            credential.access_token
        )
        # Store refresh token
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "refresh_token"),
            credential.refresh_token
        )
        # Store scopes
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "scopes"),
            ",".join(credential.scopes)
        )
        # Store expires_at
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "expires_at"),
            credential.expires_at.isoformat()
        )
        logger.info(f"Stored Google OAuth credential for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[OAuthCredential]:
        """Retrieve OAuth credential from secure store."""
        try:
            access_token = await self.secure_store.get(
                self._get_storage_key(account_identifier, "access_token")
            )
            if not access_token:
                return None
            
            refresh_token = await self.secure_store.get(
                self._get_storage_key(account_identifier, "refresh_token")
            )
            scopes_str = await self.secure_store.get(
                self._get_storage_key(account_identifier, "scopes")
            )
            expires_at_str = await self.secure_store.get(
                self._get_storage_key(account_identifier, "expires_at")
            )
            
            scopes = scopes_str.split(",") if scopes_str else self.default_scopes
            expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else datetime.utcnow()
            
            return OAuthCredential(
                access_token=access_token,
                refresh_token=refresh_token or "",
                expires_at=expires_at,
                scopes=scopes,
            )
        except Exception as e:
            logger.error(f"Failed to retrieve Google credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete OAuth credential from secure store."""
        deleted = True
        for secret_type in ["access_token", "refresh_token", "scopes", "expires_at"]:
            result = await self.secure_store.delete(
                self._get_storage_key(account_identifier, secret_type)
            )
            deleted = deleted and result
        return deleted
    
    async def needs_refresh(self, account_identifier: str, buffer_seconds: int = 1800) -> bool:
        """Check if credential needs refresh."""
        credential = await self.retrieve_credential(account_identifier)
        if not credential:
            return False
        
        from datetime import timedelta
        return credential.expires_at <= datetime.utcnow() + timedelta(seconds=buffer_seconds)
    
    async def refresh_if_needed(
        self,
        account_identifier: str,
        buffer_seconds: int = 1800
    ) -> Optional[OAuthCredential]:
        """Refresh credential if it's about to expire."""
        if not await self.needs_refresh(account_identifier, buffer_seconds):
            credential = await self.retrieve_credential(account_identifier)
            return credential

        logger.info(f"Refreshing Google OAuth credential for {account_identifier}")

        credential = await self.retrieve_credential(account_identifier)
        if not credential or not credential.refresh_token:
            logger.error(f"No refresh token available for {account_identifier}")
            return None

        try:
            new_credential = await self.refresh_tokens(credential.refresh_token)
            await self.store_credential(account_identifier, new_credential)
            return new_credential
        except Exception as e:
            logger.error(f"Failed to refresh Google credential for {account_identifier}: {e}")
            return None

    async def validate_credential(self, credential: OAuthCredential) -> bool:
        """Validate OAuth credential by making a test API call to Google."""
        try:
            user_info = await self.get_user_info(credential.access_token)
            return bool(user_info.get("email"))
        except Exception as e:
            logger.warning(f"Google OAuth credential validation failed: {e}")
            return False


# Register the provider
google_provider = GoogleOAuthProvider()
provider_registry.register(google_provider)
