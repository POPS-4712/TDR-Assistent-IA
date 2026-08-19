"""HTTP endpoints for metadata-only backup and restore."""

from fastapi import APIRouter, HTTPException, status

from ...schemas.backup import BackupRestoreRequest, BackupValidationRequest
from ...services.backup import BackupManager, BackupValidationError

router = APIRouter()
_backup_manager = BackupManager()


@router.get("/export")
async def export_backup():
    """Return a portable snapshot with metadata only; no credentials or secrets."""
    return await _backup_manager.create_backup()


@router.post("/validate")
async def validate_backup(payload: BackupValidationRequest):
    """Validate a prospective restore payload without writing anything."""
    try:
        return _backup_manager.validate_backup(payload.backup)
    except BackupValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/restore")
async def restore_backup(payload: BackupRestoreRequest):
    """Restore only safe metadata; dry-run is enabled unless explicitly disabled."""
    try:
        return await _backup_manager.restore_backup(payload.backup, dry_run=payload.dry_run)
    except BackupValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
