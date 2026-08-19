"""
API schemas for Automation Center Automations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class AutomationSchema(BaseModel):
    """Schema for automation API responses."""
    id: str = Field(..., description="Unique identifier for the automation")
    name: str = Field(..., description="Display name of the automation")
    description: str = Field(..., description="Description of the automation")
    version: str = Field(..., description="Version string")
    status: str = Field(default="disabled", description="Current status")
    manifest_url: Optional[str] = Field(default=None, description="URL to manifest file")
    dependencies: List[str] = Field(default_factory=list, description="List of dependency IDs")
    n8n_workflow_id: Optional[str] = Field(default=None, description="n8n workflow ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class AutomationListResponse(BaseModel):
    """Response schema for automation list."""
    automations: List[AutomationSchema]
    total: int = Field(..., description="Total number of automations")

class AutomationDetailResponse(BaseModel):
    """Response schema for automation details."""
    automation: AutomationSchema