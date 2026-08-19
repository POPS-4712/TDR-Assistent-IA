"""API schemas for Automation Center credentials without secret leakage."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CredentialSchema(BaseModel):
    """Public credential metadata; no secret or n8n internal identifier."""

    id: str = Field(..., description="Unique identifier (UUID)")
    provider: str = Field(..., description="Provider name")
    account_identifier: str = Field(..., description="Account identifier")
    scopes: List[str] = Field(default_factory=list)
    status: str = Field(default="active")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_refresh: Optional[datetime] = None
    last_validation: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CredentialListResponse(BaseModel):
    credentials: List[CredentialSchema]
    total: int


class CredentialDetailResponse(BaseModel):
    credential: CredentialSchema


class StructuredCredentialRequest(BaseModel):
    """Secret values are accepted only for immediate secure-store persistence."""

    provider: str = Field(..., min_length=1, max_length=100)
    account_identifier: str = Field(..., min_length=1, max_length=255)
    secrets: Dict[str, str] = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CredentialValidationResponse(BaseModel):
    credential_id: str
    result: str = Field(..., pattern="^(VALID|INVALID|EXPIRED|REAUTH_REQUIRED)$")
    status: str
