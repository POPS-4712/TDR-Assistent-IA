"""Security-focused tests for structured credential providers."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.credentials.manager import CredentialManager
from app.services.credentials.structured_providers import (
    HeaderAuthProvider,
    StructuredSecretCredential,
    WhatsAppCloudProvider,
)


class MemorySecureStore:
    def __init__(self):
        self.values = {}

    async def set(self, key, value):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        return self.values.pop(key, None) is not None


class TestStructuredProviders:
    def test_whatsapp_metadata_requires_numeric_identifiers_and_version(self):
        provider = WhatsAppCloudProvider(secure_store=MemorySecureStore())
        provider._validate_metadata({"phone_number_id": "123456", "waba_id": "987654", "api_version": "v26.0"})
        with pytest.raises(ValueError, match="phone_number_id"):
            provider._validate_metadata({"phone_number_id": "not-an-id", "api_version": "v26.0"})
        with pytest.raises(ValueError, match="api_version"):
            provider._validate_metadata({"phone_number_id": "123456", "api_version": "latest"})

    def test_whatsapp_n8n_payload_is_header_auth(self):
        provider = WhatsAppCloudProvider(secure_store=MemorySecureStore())
        payload = provider.build_n8n_credentials(
            StructuredSecretCredential(
                secrets={"access_token": "unit-test-token"},
                metadata={"phone_number_id": "123456", "api_version": "v26.0"},
            )
        )
        assert provider.get_n8n_credential_type() == "httpHeaderAuth"
        assert payload["name"] == "Authorization"
        assert payload["value"] == "Bearer unit-test-token"

    @pytest.mark.asyncio
    async def test_header_auth_stores_only_json_in_secure_store(self):
        store = MemorySecureStore()
        provider = HeaderAuthProvider(secure_store=store)
        credential = StructuredSecretCredential(
            secrets={"header_value": "unit-test-secret"},
            metadata={"header_name": "X-API-Key"},
        )
        await provider.store_credential("test-account", credential)
        assert len(store.values) == 1
        stored_key = next(iter(store.values))
        assert "test-account" in stored_key
        restored = await provider.retrieve_credential("test-account", credential.metadata)
        assert restored is not None
        assert restored.secrets == credential.secrets
        assert restored.metadata == credential.metadata

    @pytest.mark.asyncio
    async def test_header_auth_rejects_non_public_validation_url(self):
        provider = HeaderAuthProvider(secure_store=MemorySecureStore())
        credential = StructuredSecretCredential(
            secrets={"header_value": "unit-test-secret"},
            metadata={"header_name": "Authorization", "validation_url": "http://localhost:8000/check"},
        )
        with pytest.raises(ValueError, match="public HTTPS"):
            await provider.validate_credential(credential)


class TestPublicCredentialSerialization:
    def test_public_metadata_hides_secret_and_n8n_reference(self):
        now = datetime.utcnow()
        record = SimpleNamespace(
            id="credential-id",
            provider="whatsapp_cloud",
            account_identifier="test-account",
            scopes=[],
            status="active",
            credential_metadata={"phone_number_id": "123456", "api_version": "v26.0"},
            n8n_credential_id="internal-only-reference",
            last_refresh=None,
            last_validation=now,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )
        payload = CredentialManager._public_credential_metadata(record)
        serialized = str(payload).lower()
        assert "internal-only-reference" not in serialized
        assert "n8n_credential_id" not in payload
        assert "token" not in serialized
        assert payload["metadata"]["phone_number_id"] == "123456"
