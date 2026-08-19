"""
Pydantic models for Automation Center Automations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class AutomationBase(BaseModel):
    """Base automation model."""
    id: str = Field(..., description="Unique identifier for the automation")
    name: str = Field(..., description="Display name of the automation")
    description: str = Field(..., description="Description of the automation")
    version: str = Field(..., description="Version string")

class Automation(AutomationBase):
    """Full automation model."""
    status: str = Field(default="disabled", description="Current status")
    manifest_url: Optional[str] = Field(default=None, description="URL to manifest file")
    dependencies: List[str] = Field(default_factory=list, description="List of dependency IDs")
    n8n_workflow_id: Optional[str] = Field(default=None, description="n8n workflow ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class AutomationCreate(AutomationBase):
    """Model for creating a new automation."""
    status: str = Field(default="disabled")
    manifest_url: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    n8n_workflow_id: Optional[str] = None

class AutomationUpdate(BaseModel):
    """Model for updating an automation."""
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    manifest_url: Optional[str] = None
    dependencies: Optional[List[str]] = None
    n8n_workflow_id: Optional[str] = None