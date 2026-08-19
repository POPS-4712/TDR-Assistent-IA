"""Pydantic contracts for metadata-only backup and restore."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class BackupValidationRequest(BaseModel):
    backup: Dict[str, Any]


class BackupRestoreRequest(BaseModel):
    backup: Dict[str, Any]
    dry_run: bool = Field(default=True, description="Validate first; no data is written when true.")
