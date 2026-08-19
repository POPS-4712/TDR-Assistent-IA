"""
API schemas for Automation Center Executions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class ExecutionSchema(BaseModel):
    """Schema for execution API responses."""
    id: str = Field(..., description="Unique execution ID")
    automation_id: str = Field(..., description="ID of the automation")
    profile_id: Optional[str] = Field(default=None, description="Non-secret profile context ID")
    workflow_id: Optional[str] = Field(default=None, description="ID of the workflow")
    n8n_execution_id: Optional[str] = Field(default=None, description="n8n execution ID")
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    result_data: Optional[Dict[str, Any]] = Field(default=None, description="Result data")

class ExecutionListResponse(BaseModel):
    """Response schema for execution list."""
    executions: List[ExecutionSchema]
    total: int = Field(..., description="Total number of executions")

class ExecutionDetailResponse(BaseModel):
    """Response schema for execution details."""
    execution: ExecutionSchema