"""
API Key Provider Implementations.

Supports OpenAI, Gemini, Anthropic, OpenRouter, and other API key based services.
"""

import logging
from typing import Dict, List, Any, Optional

from .providers import (
    ApiKeyProvider,
    ApiKeyCredential,
    CredentialType,
    provider_registry,
)
from .secure_store import SecureStore, get_secure_store
from ...core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(ApiKeyProvider):
    """OpenAI API Key provider."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "openai"
        self.api_base_url = "https://api.openai.com/v1"
        self.auth_header = "Authorization"
        self.auth_prefix = "Bearer"
        self.validation_endpoint = "/models"
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for OpenAI."""
        return "openAiApi"
    
    def build_n8n_credentials(self, credential: ApiKeyCredential) -> Dict[str, Any]:
        """Build n8n credential payload from API key credential."""
        return {
            "apiKey": credential.api_key,
        }
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: ApiKeyCredential
    ) -> None:
        """Store API key in secure store."""
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "api_key"),
            credential.api_key
        )
        logger.info(f"Stored OpenAI API key for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[ApiKeyCredential]:
        """Retrieve API key from secure store."""
        try:
            api_key = await self.secure_store.get(
                self._get_storage_key(account_identifier, "api_key")
            )
            if not api_key:
                return None
            return ApiKeyCredential(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to retrieve OpenAI credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete API key from secure store."""
        return await self.secure_store.delete(
            self._get_storage_key(account_identifier, "api_key")
        )


class GeminiProvider(ApiKeyProvider):
    """Google Gemini API Key provider."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "gemini"
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.auth_header = "x-goog-api-key"
        self.auth_prefix = ""
        self.validation_endpoint = "/models"
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for Gemini."""
        return "googlePalmApi"
    
    def build_n8n_credentials(self, credential: ApiKeyCredential) -> Dict[str, Any]:
        """Build n8n credential payload from API key credential."""
        return {
            "apiKey": credential.api_key,
        }
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: ApiKeyCredential
    ) -> None:
        """Store API key in secure store."""
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "api_key"),
            credential.api_key
        )
        logger.info(f"Stored Gemini API key for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[ApiKeyCredential]:
        """Retrieve API key from secure store."""
        try:
            api_key = await self.secure_store.get(
                self._get_storage_key(account_identifier, "api_key")
            )
            if not api_key:
                return None
            return ApiKeyCredential(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to retrieve Gemini credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete API key from secure store."""
        return await self.secure_store.delete(
            self._get_storage_key(account_identifier, "api_key")
        )


class AnthropicProvider(ApiKeyProvider):
    """Anthropic API Key provider."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "anthropic"
        self.api_base_url = "https://api.anthropic.com/v1"
        self.auth_header = "x-api-key"
        self.auth_prefix = ""
        self.validation_endpoint = "/models"
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for Anthropic."""
        return "anthropicApi"
    
    def build_n8n_credentials(self, credential: ApiKeyCredential) -> Dict[str, Any]:
        """Build n8n credential payload from API key credential."""
        return {
            "apiKey": credential.api_key,
        }
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: ApiKeyCredential
    ) -> None:
        """Store API key in secure store."""
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "api_key"),
            credential.api_key
        )
        logger.info(f"Stored Anthropic API key for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[ApiKeyCredential]:
        """Retrieve API key from secure store."""
        try:
            api_key = await self.secure_store.get(
                self._get_storage_key(account_identifier, "api_key")
            )
            if not api_key:
                return None
            return ApiKeyCredential(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to retrieve Anthropic credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete API key from secure store."""
        return await self.secure_store.delete(
            self._get_storage_key(account_identifier, "api_key")
        )


class OpenRouterProvider(ApiKeyProvider):
    """OpenRouter API Key provider."""
    
    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "openrouter"
        self.api_base_url = "https://openrouter.ai/api/v1"
        self.auth_header = "Authorization"
        self.auth_prefix = "Bearer"
        self.validation_endpoint = "/models"
    
    def get_n8n_credential_type(self) -> str:
        """Get n8n credential type for OpenRouter."""
        return "openRouterApi"
    
    def build_n8n_credentials(self, credential: ApiKeyCredential) -> Dict[str, Any]:
        """Build n8n credential payload from API key credential."""
        return {
            "apiKey": credential.api_key,
        }
    
    async def store_credential(
        self,
        account_identifier: str,
        credential: ApiKeyCredential
    ) -> None:
        """Store API key in secure store."""
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "api_key"),
            credential.api_key
        )
        logger.info(f"Stored OpenRouter API key for {account_identifier}")
    
    async def retrieve_credential(self, account_identifier: str) -> Optional[ApiKeyCredential]:
        """Retrieve API key from secure store."""
        try:
            api_key = await self.secure_store.get(
                self._get_storage_key(account_identifier, "api_key")
            )
            if not api_key:
                return None
            return ApiKeyCredential(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to retrieve OpenRouter credential for {account_identifier}: {e}")
            return None
    
    async def delete_credential(self, account_identifier: str) -> bool:
        """Delete API key from secure store."""
        return await self.secure_store.delete(
            self._get_storage_key(account_identifier, "api_key")
        )


# Register all API key providers
openai_provider = OpenAIProvider()
gemini_provider = GeminiProvider()
anthropic_provider = AnthropicProvider()
openrouter_provider = OpenRouterProvider()

provider_registry.register(openai_provider)
provider_registry.register(gemini_provider)
provider_registry.register(anthropic_provider)
provider_registry.register(openrouter_provider)