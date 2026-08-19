"""
Pydantic models for Automation Center Settings.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

class SettingBase(BaseModel):
    """Base setting model."""
    key: str = Field(..., description="Unique setting key")
    value: Dict[str, Any] = Field(..., description="Setting value")

class Setting(SettingBase):
    """Full setting model."""
    updated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat(), description="Last update timestamp")

class SettingCreate(SettingBase):
    """Model for creating a new setting."""
    pass

class SettingUpdate(BaseModel):
    """Model for updating a setting."""
    value: Optional[Dict[str, Any]] = None