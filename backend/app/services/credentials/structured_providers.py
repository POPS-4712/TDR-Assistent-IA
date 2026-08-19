"""Structured secret providers for Automation Center.

These providers keep every secret in SecureStore.  PostgreSQL receives only the
non-secret metadata returned by ``public_metadata``.
"""

from __future__ import annotations

import ipaddress
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from .providers import CredentialProvider, CredentialType, provider_registry
from .secure_store import SecureStore, get_secure_store

logger = logging.getLogger(__name__)


@dataclass
class StructuredSecretCredential:
    """A provider credential split into secret and public components."""

    secrets: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuredSecretProvider(CredentialProvider):
    """Base class for credentials whose secret is accompanied by public setup metadata."""

    secret_keys: tuple[str, ...] = ()
    public_keys: tuple[str, ...] = ()

    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.credential_type = CredentialType.STRUCTURED

    async def validate_config(self) -> bool:
        return bool(self.provider_name)

    async def get_authorization_url(self, scopes: List[str], state: str) -> str:
        raise NotImplementedError("Structured providers do not use OAuth")

    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> Any:
        raise NotImplementedError("Structured providers do not use OAuth")

    async def refresh_tokens(self, refresh_token: str) -> Any:
        raise NotImplementedError("Structured providers do not refresh tokens")

    async def revoke_tokens(self, tokens: Any) -> bool:
        return True

    async def store_credential(self, account_identifier: str, credential: StructuredSecretCredential) -> None:
        await self.secure_store.set(
            self._get_storage_key(account_identifier, "structured_secret"),
            json.dumps(credential.secrets),
        )

    async def retrieve_credential(self, account_identifier: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[StructuredSecretCredential]:
        value = await self.secure_store.get(self._get_storage_key(account_identifier, "structured_secret"))
        if not value:
            return None
        try:
            secrets = json.loads(value)
        except json.JSONDecodeError:
            logger.error("Invalid structured credential storage for provider %s", self.provider_name)
            return None
        return StructuredSecretCredential(secrets=secrets, metadata=metadata or {})

    async def delete_credential(self, account_identifier: str) -> bool:
        return await self.secure_store.delete(self._get_storage_key(account_identifier, "structured_secret"))

    def public_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {key: metadata[key] for key in self.public_keys if key in metadata and metadata[key] not in (None, "")}


class WhatsAppCloudProvider(StructuredSecretProvider):
    """Meta WhatsApp Cloud API provider using a bearer access token."""

    secret_keys = ("access_token",)
    public_keys = ("phone_number_id", "waba_id", "api_version")

    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "whatsapp_cloud"
        self.api_base_url = "https://graph.facebook.com"

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        phone_number_id = str(metadata.get("phone_number_id", "")).strip()
        api_version = str(metadata.get("api_version", "")).strip()
        if not phone_number_id or not phone_number_id.isdigit():
            raise ValueError("WhatsApp Cloud requires a numeric phone_number_id")
        if not api_version.startswith("v") or not api_version[1:].replace(".", "").isdigit():
            raise ValueError("WhatsApp Cloud requires an api_version such as v23.0")
        if metadata.get("waba_id") and not str(metadata["waba_id"]).isdigit():
            raise ValueError("WhatsApp Cloud waba_id must be numeric when provided")

    async def validate_credential(self, credential: StructuredSecretCredential) -> bool:
        self._validate_metadata(credential.metadata)
        token = credential.secrets.get("access_token", "").strip()
        if not token:
            return False
        version = credential.metadata["api_version"]
        phone_number_id = credential.metadata["phone_number_id"]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_base_url}/{version}/{phone_number_id}",
                    params={"fields": "id,status"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            if response.status_code != 200:
                return False
            data = response.json()
            return bool(data.get("id")) and str(data.get("status", "CONNECTED")).upper() == "CONNECTED"
        except (httpx.HTTPError, ValueError):
            return False

    def get_n8n_credential_type(self) -> str:
        return "httpHeaderAuth"

    def build_n8n_credentials(self, credential: StructuredSecretCredential) -> Dict[str, Any]:
        return {"name": "Authorization", "value": f"Bearer {credential.secrets['access_token']}"}


class HeaderAuthProvider(StructuredSecretProvider):
    """Generic Header Auth provider with optional, safe opt-in validation."""

    secret_keys = ("header_value",)
    public_keys = ("header_name", "validation_url")

    def __init__(self, secure_store: Optional[SecureStore] = None):
        super().__init__(secure_store)
        self.provider_name = "header_auth"

    @staticmethod
    def _safe_validation_url(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        if hostname in {"localhost", "localhost.localdomain"}:
            return False
        try:
            return not ipaddress.ip_address(hostname).is_private
        except ValueError:
            return True

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        header_name = str(metadata.get("header_name", "")).strip()
        if not header_name or any(ch in header_name for ch in "\r\n:"):
            raise ValueError("Header Auth requires a safe header_name")
        validation_url = str(metadata.get("validation_url", "")).strip()
        if validation_url and not self._safe_validation_url(validation_url):
            raise ValueError("Header Auth validation_url must be a public HTTPS URL")

    async def validate_credential(self, credential: StructuredSecretCredential) -> bool:
        self._validate_metadata(credential.metadata)
        header_value = credential.secrets.get("header_value", "").strip()
        if not header_value:
            return False
        validation_url = str(credential.metadata.get("validation_url", "")).strip()
        if not validation_url:
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                response = await client.get(
                    validation_url,
                    headers={credential.metadata["header_name"]: header_value},
                )
            return 200 <= response.status_code < 300
        except httpx.HTTPError:
            return False

    def get_n8n_credential_type(self) -> str:
        return "httpHeaderAuth"

    def build_n8n_credentials(self, credential: StructuredSecretCredential) -> Dict[str, Any]:
        return {
            "name": credential.metadata["header_name"],
            "value": credential.secrets["header_value"],
        }


whatsapp_cloud_provider = WhatsAppCloudProvider()
header_auth_provider = HeaderAuthProvider()
provider_registry.register(whatsapp_cloud_provider)
provider_registry.register(header_auth_provider)
