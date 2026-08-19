"""
Credential Services Package for Automation Center.
"""
from .secure_store import SecureStore, get_secure_store, KeyringSecureStore, EncryptedFileSecureStore
from .providers import (
    CredentialProvider,
    CredentialProviderRegistry,
    CredentialType,
    CredentialMetadata,
    OAuthCredential,
    ApiKeyCredential,
    TokenCredential,
    provider_registry,
)
from .google_provider import GoogleOAuthProvider, google_provider
from .api_key_providers import (
    OpenAIProvider,
    GeminiProvider,
    AnthropicProvider,
    OpenRouterProvider,
    openai_provider,
    gemini_provider,
    anthropic_provider,
    openrouter_provider,
)
from .telegram_provider import TelegramProvider, telegram_provider
from .manager import CredentialManager, credential_manager

__all__ = [
    "SecureStore", "get_secure_store", "KeyringSecureStore", "EncryptedFileSecureStore",
    "CredentialProvider", "CredentialProviderRegistry", "CredentialType",
    "CredentialMetadata", "OAuthCredential", "ApiKeyCredential", "TokenCredential",
    "provider_registry", "GoogleOAuthProvider", "google_provider",
    "OpenAIProvider", "GeminiProvider", "AnthropicProvider", "OpenRouterProvider",
    "openai_provider", "gemini_provider", "anthropic_provider", "openrouter_provider",
    "TelegramProvider", "telegram_provider", "CredentialManager", "credential_manager",
]