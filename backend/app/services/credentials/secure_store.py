"""
Secure Store abstraction for OS-specific credential storage.

Provides a unified interface for storing secrets across different platforms:
- Windows: Windows Credential Manager / DPAPI
- macOS: Keychain
- Linux Desktop: Secret Service / GNOME Keyring
- Linux Headless: Encrypted vault file with system key
- Raspberry Pi: Encrypted vault file with system key
"""

import os
import platform
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path

import keyring
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class SecureStore(ABC):
    """Abstract base class for secure storage implementations."""
    
    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Store a secret value."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Retrieve a secret value."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a secret value. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a secret exists."""
        pass
    
    @abstractmethod
    async def list_keys(self) -> List[str]:
        """List all stored keys (metadata only)."""
        pass


class KeyringSecureStore(SecureStore):
    """Secure store using OS keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)."""
    
    def __init__(self, service_name: str = "automation-center"):
        self.service_name = service_name
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure keyring is available."""
        if not self._initialized:
            # Test keyring availability
            try:
                keyring.get_keyring()
                self._initialized = True
            except Exception as e:
                logger.error(f"Keyring not available: {e}")
                raise RuntimeError("OS secure storage not available")
    
    async def set(self, key: str, value: str) -> None:
        await self._ensure_initialized()
        try:
            keyring.set_password(self.service_name, key, value)
            logger.debug(f"Stored secret for key: {key}")
        except Exception as e:
            logger.error(f"Failed to store secret for key {key}: {e}")
            raise
    
    async def get(self, key: str) -> Optional[str]:
        await self._ensure_initialized()
        try:
            value = keyring.get_password(self.service_name, key)
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve secret for key {key}: {e}")
            raise
    
    async def delete(self, key: str) -> bool:
        await self._ensure_initialized()
        try:
            keyring.delete_password(self.service_name, key)
            logger.debug(f"Deleted secret for key: {key}")
            return True
        except Exception as e:
            logger.debug(f"Secret not found for deletion: {key}")
            return False
    
    async def exists(self, key: str) -> bool:
        await self._ensure_initialized()
        try:
            value = keyring.get_password(self.service_name, key)
            return value is not None
        except Exception:
            return False
    
    async def list_keys(self) -> List[str]:
        """Keyring doesn't support listing keys directly."""
        # This would require platform-specific implementation
        # For now, return empty list - credentials should be tracked in PostgreSQL
        return []


class EncryptedFileSecureStore(SecureStore):
    """Secure store using encrypted file for headless systems (Linux/Raspberry Pi)."""
    
    def __init__(self, vault_path: str = "/etc/automation-center/vault.enc", key_path: str = "/etc/automation-center/system.key"):
        self.vault_path = Path(vault_path)
        self.key_path = Path(key_path)
        self._fernet: Optional[Fernet] = None
        self._vault: Dict[str, str] = {}
        self._loaded = False
    
    def _derive_key(self, key_material: bytes) -> bytes:
        """Derive a Fernet key from key material."""
        salt = key_material[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key_material))
    
    async def _load(self):
        """Load and decrypt the vault."""
        if self._loaded:
            return
        
        # Read system key
        if not self.key_path.exists():
            raise RuntimeError(f"System key not found at {self.key_path}")
        
        with open(self.key_path, "rb") as f:
            key_material = f.read()
        
        key = self._derive_key(key_material)
        self._fernet = Fernet(key)
        
        # Load vault if exists
        if self.vault_path.exists():
            with open(self.vault_path, "rb") as f:
                encrypted_data = f.read()
            try:
                decrypted = self._fernet.decrypt(encrypted_data)
                import json
                self._vault = json.loads(decrypted.decode())
            except InvalidToken:
                logger.error("Failed to decrypt vault - invalid key or corrupted data")
                self._vault = {}
        else:
            self._vault = {}
        
        self._loaded = True
    
    async def _save(self):
        """Encrypt and save the vault."""
        if not self._loaded or not self._fernet:
            raise RuntimeError("Vault not loaded")
        
        import json
        data = json.dumps(self._vault).encode()
        encrypted = self._fernet.encrypt(data)
        
        # Ensure directory exists
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.vault_path, "wb") as f:
            f.write(encrypted)
        
        # Set restrictive permissions
        os.chmod(self.vault_path, 0o600)
    
    async def set(self, key: str, value: str) -> None:
        await self._load()
        self._vault[key] = value
        await self._save()
        logger.debug(f"Stored secret for key: {key}")
    
    async def get(self, key: str) -> Optional[str]:
        await self._load()
        return self._vault.get(key)
    
    async def delete(self, key: str) -> bool:
        await self._load()
        if key in self._vault:
            del self._vault[key]
            await self._save()
            logger.debug(f"Deleted secret for key: {key}")
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        await self._load()
        return key in self._vault
    
    async def list_keys(self) -> List[str]:
        await self._load()
        return list(self._vault.keys())


def get_secure_store() -> SecureStore:
    """
    Factory function to get the appropriate SecureStore implementation
    based on the current platform and environment.
    """
    system = platform.system().lower()
    is_headless = not os.isatty(0) if hasattr(os, 'isatty') else False
    
    # Check if running in container/headless
    in_container = os.path.exists("/.dockerenv") or os.environ.get("CONTAINER") == "true"
    
    if system == "windows":
        # Windows: Use DPAPI via keyring
        logger.info("Using Windows Credential Manager (DPAPI) for secure storage")
        return KeyringSecureStore()
    
    elif system == "darwin":
        # macOS: Use Keychain via keyring
        logger.info("Using macOS Keychain for secure storage")
        return KeyringSecureStore()
    
    elif system == "linux":
        if in_container or is_headless:
            # Linux headless/container: Use encrypted file
            logger.info("Using encrypted file vault for secure storage (headless Linux)")
            return EncryptedFileSecureStore()
        else:
            # Linux desktop: Use Secret Service via keyring
            logger.info("Using Linux Secret Service (GNOME Keyring/KWallet) for secure storage")
            return KeyringSecureStore()
    
    else:
        # Fallback: Try keyring
        logger.warning(f"Unknown platform {system}, attempting to use keyring")
        return KeyringSecureStore()