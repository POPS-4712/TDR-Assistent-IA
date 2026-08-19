"""
API schemas for Automation Center Settings.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

class SettingSchema(BaseModel):
    """Schema for setting API responses."""
    key: str = Field(..., description="Unique setting key")
    value: Dict[str, Any] = Field(..., description="Setting value")
    updated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat(), description="Last update timestamp")

class SettingDetailResponse(BaseModel):
    """Response schema for setting details."""
    setting: SettingSchema