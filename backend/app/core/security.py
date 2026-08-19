"""
Security utilities for Automation Center Backend.
This module handles credential encryption, OAuth state management, and logging sanitization.
"""

import base64
import hashlib
import hmac
import os
import secrets
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Allowed log parameters that should never be sanitized
ALLOWED_LOG_PARAMETERS: Set[str] = {
    "id", "name", "status", "type", "workflow_id", "automation_id",
    "provider", "account_identifier", "action", "message", "error",
    "duration", "count", "total", "page", "limit"
}

class OAuthState:
    """Manages OAuth state for PKCE flow."""
    
    def __init__(self, provider: str, code_verifier: str, created_at: Optional[datetime] = None):
        self.provider = provider
        self.code_verifier = code_verifier
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "provider": self.provider,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OAuthState":
        return cls(
            provider=data["provider"],
            code_verifier="",
            created_at=datetime.fromisoformat(data["created_at"])
        )
    
    def is_expired(self, expiry_seconds: int = 300) -> bool:
        """Check if state has expired (default 5 minutes)."""
        expiry_time = self.created_at + timedelta(seconds=expiry_seconds)
        return datetime.utcnow() > expiry_time

class CredentialEncryption:
    """Handles encryption of credential secrets using OS secure storage keys."""
    
    def __init__(self):
        self.master_key: Optional[bytes] = None
        self.fernet: Optional[Fernet] = None
    
    def derive_master_key(self, os_credential: bytes) -> bytes:
        """Derive a master encryption key from OS secure storage credential."""
        # Use PBKDF2 to derive a 32-byte key from the OS credential
        salt = os_credential[:16]  # Use first 16 bytes as salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(os_credential))
    
    def initialize(self, os_credential: bytes):
        """Initialize encryption with OS secure storage credential."""
        self.master_key = self.derive_master_key(os_credential)
        self.fernet = Fernet(self.master_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret."""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a secret."""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        return self.fernet.decrypt(ciphertext.encode()).decode()
    
    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a PKCE code verifier."""
        return secrets.token_urlsafe(64)
    
    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Generate a PKCE code challenge from verifier."""
        sha256 = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(sha256).decode().rstrip('=')
    
    @staticmethod
    def generate_oauth_state() -> str:
        """Generate a random OAuth state."""
        return secrets.token_urlsafe(32)

class SanitizedLog:
    """Handles logging with automatic sanitization of sensitive data."""
    
    SENSITIVE_KEYS: Set[str] = {
        "token", "secret", "key", "password", "credential", "authorization",
        "access_token", "refresh_token", "id_token", "client_secret",
        "code", "authorization_code", "callback"
    }
    
    REPLACEMENT: str = "[REDACTED]"
    
    @classmethod
    def sanitize_dict(cls, data: Dict, depth: int = 0, max_depth: int = 10) -> Dict:
        """Recursively sanitize a dictionary, removing sensitive values."""
        if depth > max_depth:
            return data
        
        result = {}
        for key, value in data.items():
            # Check if this key should be redacted
            key_lower = key.lower()
            is_sensitive = any(
                sensitive in key_lower 
                for sensitive in cls.SENSITIVE_KEYS
            )
            
            if is_sensitive and key not in ALLOWED_LOG_PARAMETERS:
                result[key] = cls.REPLACEMENT
            elif isinstance(value, dict):
                result[key] = cls.sanitize_dict(value, depth + 1, max_depth)
            elif isinstance(value, list):
                result[key] = cls.sanitize_list(value, depth + 1, max_depth)
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def sanitize_list(cls, data: List, depth: int = 0, max_depth: int = 10) -> List:
        """Sanitize a list of values."""
        if depth > max_depth:
            return data
        
        return [
            cls.sanitize_dict(item, depth + 1, max_depth) if isinstance(item, dict)
            else cls.sanitize_list(item, depth + 1, max_depth) if isinstance(item, list)
            else item
            for item in data
        ]
    
    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Sanitize a string containing potential secrets."""
        # Pattern to match common secret formats
        import re
        
        patterns = [
            # Bearer tokens
            r'(Bearer\s+)[^\s]+',
            # Authorization headers
            r'(Authorization:\s*)[^\s]+',
            # API keys
            r'(api[_-]?key["\s:]*)[^\s"\'\]]+',
            # Tokens
            r'(token["\s:]*)[^\s"\'\]]+',
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, cls.REPLACEMENT, result, flags=re.IGNORECASE)
        
        return result

# Global instances
oauth_state_manager = OAuthState
encryption = CredentialEncryption()
log_sanitizer = SanitizedLog