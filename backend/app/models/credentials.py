"""
Pydantic models for Automation Center Credentials.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class CredentialBase(BaseModel):
    """Base credential model."""
    provider: str = Field(..., description="Provider name (e.g., google, microsoft)")
    account_identifier: str = Field(..., description="Account identifier (e.g., email)")
    scopes: List[str] = Field(default_factory=list, description="List of authorized scopes")

class Credential(CredentialBase):
    """Full credential model."""
    id: str = Field(..., description="Unique identifier (UUID)")
    status: str = Field(default="active", description="Current status")
    n8n_credential_id: Optional[str] = Field(default=None, description="n8n credential ID")
    last_refresh: Optional[datetime] = Field(default=None, description="Last token refresh timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Token expiration timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class CredentialCreate(CredentialBase):
    """Model for creating a new credential."""
    status: str = Field(default="active")
    n8n_credential_id: Optional[str] = None

class CredentialUpdate(BaseModel):
    """Model for updating a credential."""
    status: Optional[str] = None
    n8n_credential_id: Optional[str] = None
    last_refresh: Optional[datetime] = None
    expires_at: Optional[datetime] = None