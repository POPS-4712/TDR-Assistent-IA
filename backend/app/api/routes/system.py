"""Non-sensitive system diagnostics and optional local service controls."""

from __future__ import annotations

import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Path as ApiPath
from sqlalchemy import text

from ...core.config import settings
from ...services.n8n.client import N8NClient
from ...services.system.service_manager import LocalServiceManager, MANAGED_SERVICES, SAFE_ACTIONS

router = APIRouter()


def _service_status(status: str, error: str | None = None) -> Dict[str, str]:
    result: Dict[str, str] = {"status": status}
    if error:
        result["error"] = error
    return result


async def _postgres_status() -> Dict[str, str]:
    try:
        from ...database.db import engine
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
        return _service_status("healthy")
    except Exception as exc:
        return _service_status("unhealthy", type(exc).__name__)


async def _n8n_status() -> Dict[str, str]:
    try:
        async with N8NClient() as client:
            healthy = await client.health_check()
        return _service_status("healthy" if healthy else "unhealthy")
    except Exception as exc:
        return _service_status("unhealthy", type(exc).__name__)


async def _playwright_status() -> Dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.PLAYWRIGHT_API_URL.rstrip('/')}/health")
        return _service_status("healthy" if response.status_code == 200 else "unhealthy")
    except httpx.HTTPError as exc:
        return _service_status("unhealthy", type(exc).__name__)


async def _all_service_statuses() -> Dict[str, Dict[str, str]]:
    return {
        "backend": _service_status("healthy"),
        "postgres": await _postgres_status(),
        "n8n": await _n8n_status(),
        "playwright": await _playwright_status(),
    }


def _first_run_complete() -> bool:
    if not settings.USER_DATA_DIR:
        return False
    return (Path(settings.USER_DATA_DIR) / "state" / "first-run-complete.json").exists()


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Return health information without exposing URLs, secrets or container IDs."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "first_run_complete": _first_run_complete(),
        "services": await _all_service_statuses(),
    }


@router.get("/version")
async def get_version() -> Dict[str, str]:
    """Return the single product version."""
    return {"version": settings.APP_VERSION}


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Return only configuration metadata that is safe for the local UI."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "portable_mode": settings.PORTABLE_MODE,
        "user_data_dir_configured": bool(settings.USER_DATA_DIR),
        "n8n_api_url": settings.N8N_API_URL,
        "playwright_api_url": settings.PLAYWRIGHT_API_URL,
    }


@router.get("/setup")
async def get_setup_status() -> Dict[str, Any]:
    """Return the non-sensitive setup state used by the first-run wizard."""
    services = await _all_service_statuses()
    return {
        "first_run_complete": _first_run_complete(),
        "user_data_dir_configured": bool(settings.USER_DATA_DIR),
        "runtime_ready": all(service["status"] == "healthy" for service in services.values()),
        "services": services,
        "external_accounts_optional": True,
        "profile_required_for_completion": True,
    }


@router.post("/setup/complete")
async def complete_setup() -> Dict[str, Any]:
    """Persist an inert first-run completion marker in the mounted user-data root."""
    if not settings.USER_DATA_DIR:
        raise HTTPException(status_code=409, detail="User-data storage is not configured for this runtime")
    marker = Path(settings.USER_DATA_DIR) / "state" / "first-run-complete.json"
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "app_version": settings.APP_VERSION,
        }, indent=2), encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=503, detail="Setup state could not be stored safely") from None
    return {"success": True, "first_run_complete": True}


@router.get("/diagnostics")
async def get_diagnostics() -> Dict[str, Any]:
    """Provide an installer-safe diagnostic report with no secret values."""
    disk = shutil.disk_usage("/")
    manager = LocalServiceManager()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "environment": settings.ENVIRONMENT,
        "first_run_complete": _first_run_complete(),
        "services": await _all_service_statuses(),
        "local_service_control": manager.availability(),
        "managed_container_statuses": manager.managed_container_statuses(),
        "disk": {"free_bytes": disk.free, "total_bytes": disk.total},
        "ports": {
            "frontend": 3001,
            "backend": 8000,
            "postgres": 5432,
            "n8n": 5678,
            "playwright": 3000,
        },
        "migrations": {"enabled": settings.ENABLE_DATABASE_MIGRATIONS, "status": "managed_on_startup"},
    }


@router.post("/services/{service}/{action}")
async def control_service(
    service: str = ApiPath(..., pattern="^(backend|postgres|n8n|playwright|frontend)$"),
    action: str = ApiPath(..., pattern="^(start|stop|restart)$"),
) -> Dict[str, Any]:
    """Apply one whitelisted action to one local product container only."""
    if service not in MANAGED_SERVICES or action not in SAFE_ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported local service action")
    result = LocalServiceManager().control(action, [service])[0]
    if not result["success"]:
        raise HTTPException(status_code=503, detail=result["message"])
    return result
