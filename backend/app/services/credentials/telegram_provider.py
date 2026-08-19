"""
Telegram Bot Token Provider Implementation.

Supports Telegram Bot API token storage and validation.
"""

import logging
from typing import Dict, List, Any, Optional

from .providers import (
    TokenProvider,
    TokenCredential,
    CredentialType,
    provider_registry,
)
from .secure_store import SecureStore, get_secure_store

logger = logging.getLogger(__name__)


class TelegramProvider(TokenProvider):
    """Telegram Bot Token provider."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "telegram"
        self.api_base_url = "https://api.telegram.org/bot"
        self.validation_endpoint = "/getMe"
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for Telegram."""
        return "telegramApi"
    
    def build_n8n_credentials(self, credential: TokenCredential) -> Dict[str, Any]:
        """Build n8n credential payload from token credential."""
        return {
            "accessToken": credential.token,
        }
    
    async def validate_config(self) -> bool:
        """Validate Telegram configuration."""
        # Telegram doesn't require special config, just the bot token
        return await super().validate_config()
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: TokenCredential
    ) -> None:
        """Store bot token in secure store."""
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "bot_token"),
            credential.token
        )
        logger.info(f"Stored Telegram bot token for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[TokenCredential]:
        """Retrieve bot token from secure store."""
        try:
            token = await self.secure_store.get(
                self._get_storage_key(account_identifier, "bot_token")
            )
            if not token:
                return None
            return TokenCredential(token=token)
        except Exception as e:
            logger.error(f"Failed to retrieve Telegram credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete bot token from secure store."""
        return await self.secure_store.delete(
            self._get_storage_key(account_identifier, "bot_token")
        )
    
    async def get_bot_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get bot information from Telegram API."""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}{token}{self.validation_endpoint}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    return data.get("result")
                return None
        except Exception as e:
            logger.error(f"Failed to get Telegram bot info: {e}")
            return None
    
    async def validate_credential(self, credential: TokenCredential) -> bool:
        """Validate bot token by calling getMe endpoint."""
        bot_info = await self.get_bot_info(credential.token)
        return bot_info is not None


# Register the provider
telegram_provider = TelegramProvider()
provider_registry.register(telegram_provider)