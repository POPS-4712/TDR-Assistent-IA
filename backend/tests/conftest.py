"""Isolated credential-storage fixtures for the backend test suite.

This module is loaded only by pytest. It never changes production configuration,
uses no real credentials, and stores all generated test material under pytest's
temporary directory.
"""

from __future__ import annotations

import os
from typing import Dict

import keyring
import pytest
from keyring.backend import KeyringBackend

from app.services.credentials.secure_store import EncryptedFileSecureStore


class InMemoryKeyring(KeyringBackend):
    """Minimal keyring backend kept entirely in memory for automated tests."""

    priority = 1

    def __init__(self) -> None:
        self._items: Dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._items.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._items[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._items.pop((service, username), None)


@pytest.fixture(scope="session", autouse=True)
def isolated_credential_storage(tmp_path_factory: pytest.TempPathFactory):
    """Provide test-only keyring and encrypted vault material for all tests.

    Provider singletons are constructed during module imports, so their secure
    stores are swapped only for this pytest session and restored afterwards.
    """
    original_keyring = keyring.get_keyring()
    test_keyring = InMemoryKeyring()
    keyring.set_keyring(test_keyring)

    storage_dir = tmp_path_factory.mktemp("credential-store")
    key_path = storage_dir / "system.key"
    vault_path = storage_dir / "vault.enc"
    key_path.write_bytes(os.urandom(32))
    test_store = EncryptedFileSecureStore(vault_path=str(vault_path), key_path=str(key_path))

    from app.services.credentials.providers import provider_registry

    original_stores = {}
    for provider_name, provider in provider_registry._providers.items():
        if hasattr(provider, "secure_store"):
            original_stores[provider_name] = provider.secure_store
            provider.secure_store = test_store

    try:
        yield
    finally:
        for provider_name, secure_store in original_stores.items():
            provider_registry._providers[provider_name].secure_store = secure_store
        keyring.set_keyring(original_keyring)
