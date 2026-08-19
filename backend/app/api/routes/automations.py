"""
Automation endpoints for Automation Center.
"""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from ...core.logging import logger
from ...services.automations.manager import AutomationManager, AutomationStatus
from ...services.credentials.manager import CredentialManager
from ...services.n8n.client import N8NClient
from ...services.automations.manifest_manager import ManifestManager

router = APIRouter()


class AutomationRunRequest(BaseModel):
    """Optional active-profile selection for an explicit run request."""

    profile_id: Optional[str] = None



# Global instances (in production, use dependency injection)
_credential_manager: Optional[CredentialManager] = None
_n8n_client: Optional[N8NClient] = None
_manifest_manager: Optional[ManifestManager] = None
_automation_manager: Optional[AutomationManager] = None


def get_automation_manager() -> AutomationManager:
    """Get or create automation manager instance."""
    global _credential_manager, _n8n_client, _manifest_manager, _automation_manager
    
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    if _n8n_client is None:
        _n8n_client = N8NClient()
    if _manifest_manager is None:
        _manifest_manager = ManifestManager()
    if _automation_manager is None:
        _automation_manager = AutomationManager(
            credential_manager=_credential_manager,
            n8n_client=_n8n_client,
            manifest_manager=_manifest_manager,
        )
    
    return _automation_manager


@router.get("", response_model=Dict[str, Any])
async def list_automations() -> Dict[str, Any]:
    """
    List all automations.
    
    Returns metadata about all discovered/installed automations.
    """
    try:
        automation_manager = get_automation_manager()
        automations = await automation_manager.list_automations()
        
        return {"automations": automations, "total": len(automations)}
    except Exception as e:
        logger.error(f"Failed to list automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/discover", response_model=Dict[str, Any])
async def discover_automations() -> Dict[str, Any]:
    """
    Discover automations from the automations/ directory.
    
    Scans the automations directory for manifests and creates/updates
    database records for new discoveries.
    """
    try:
        automation_manager = get_automation_manager()
        automations = await automation_manager.discover_automations()
        
        return {"automations": automations, "total": len(automations)}
    except Exception as e:
        logger.error(f"Failed to discover automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preflight", response_model=Dict[str, Any])
async def preflight_all_automations() -> Dict[str, Any]:
    """Discover and evaluate all local automations without importing workflows."""
    try:
        return await get_automation_manager().preflight_all_automations()
    except Exception as exc:
        logger.error("Automatic preflight failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Automatic preflight failed")

@router.post("/{automation_id}/preflight", response_model=Dict[str, Any])
async def preflight_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """Return readiness checks without installing or changing the automation."""
    try:
        return await get_automation_manager().preflight_automation(automation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Preflight failed for automation %s: %s", automation_id, type(exc).__name__)
        raise HTTPException(status_code=500, detail="Automation preflight failed")

@router.get("/{automation_id}/accounts", response_model=Dict[str, Any])
async def resolve_automation_accounts(automation_id: str = Path(...)) -> Dict[str, Any]:
    """Resolve connected accounts and exact n8n mappings without exposing secrets."""
    try:
        return await get_automation_manager().resolve_automation_accounts(automation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Account resolution failed for automation %s: %s", automation_id, type(exc).__name__)
        raise HTTPException(status_code=500, detail="Automation account resolution failed")


@router.get("/{automation_id}", response_model=Dict[str, Any])

async def get_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """
    Get automation details by ID.
    
    Args:
        automation_id: Unique ID of the automation
        
    Returns:
        Automation details including manifest and metadata
    """
    try:
        automation_manager = get_automation_manager()
        automation = await automation_manager.get_automation(automation_id)
        
        if not automation:
            raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
        
        return {"automation": automation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{automation_id}/install", response_model=Dict[str, Any])
async def install_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """
    Install an automation.
    
    Flow:
    1. Find manifest
    2. Validate manifest
    3. Check not already installed
    4. Check dependencies
    5. Check required credentials
    6. Validate workflow JSON
    7. Import workflow in n8n
    8. Get n8n workflow ID
    9. Assign credentials
    10. Create metadata in PostgreSQL
    11. Create automation_credentials
    12. Status = installed
    
    Args:
        automation_id: Unique ID for the automation
        
    Returns:
        Installation result with n8n workflow ID
    """
    try:
        automation_manager = get_automation_manager()
        result = await automation_manager.install_automation(automation_id)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to install automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{automation_id}/run", response_model=Dict[str, Any])
async def run_automation(
    payload: AutomationRunRequest,
    automation_id: str = Path(...),
) -> Dict[str, Any]:
    """Explicitly trigger an enabled imported workflow with safe profile context."""
    try:
        return await get_automation_manager().run_automation(automation_id, payload.profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Run failed for automation %s: %s", automation_id, type(exc).__name__)
        raise HTTPException(status_code=500, detail="Automation execution failed safely")


@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def refresh_execution(execution_id: str = Path(...)) -> Dict[str, Any]:
    """Refresh non-sensitive status metadata for one tracked execution."""
    try:
        return await get_automation_manager().refresh_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Execution refresh failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Execution refresh failed safely")


@router.post("/{automation_id}/enable", response_model=Dict[str, Any])

async def enable_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """
    Enable an automation by activating its n8n workflow.
    
    Args:
        automation_id: Unique ID of the automation
        
    Returns:
        Enable result
    """
    try:
        automation_manager = get_automation_manager()
        result = await automation_manager.enable_automation(automation_id)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to enable automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{automation_id}/disable", response_model=Dict[str, Any])
async def disable_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """
    Disable an automation by deactivating its n8n workflow.
    
    Args:
        automation_id: Unique ID of the automation
        
    Returns:
        Disable result
    """
    try:
        automation_manager = get_automation_manager()
        result = await automation_manager.disable_automation(automation_id)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to disable automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{automation_id}", response_model=Dict[str, Any])
async def uninstall_automation(automation_id: str = Path(...)) -> Dict[str, Any]:
    """
    Uninstall an automation.
    
    Flow:
    1. Disable workflow
    2. Delete workflow from n8n
    3. Delete automation_credentials
    4. Delete automation metadata
    5. NO delete global user credentials
    
    Args:
        automation_id: Unique ID of the automation
        
    Returns:
        Uninstall result
    """
    try:
        automation_manager = get_automation_manager()
        result = await automation_manager.uninstall_automation(automation_id)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to uninstall automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{automation_id}/logs", response_model=Dict[str, Any])
async def get_automation_logs(
    automation_id: str = Path(...),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Get automation execution logs.
    
    Args:
        automation_id: Unique ID of the automation
        limit: Maximum number of logs to return
        
    Returns:
        Execution history
    """
    try:
        automation_manager = get_automation_manager()
        logs = await automation_manager.get_automation_logs(automation_id, limit)
        
        return {"automation_id": automation_id, "logs": logs, "total": len(logs)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get logs for automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/updates/check", response_model=Dict[str, Any])
async def check_for_updates() -> Dict[str, Any]:
    """
    Check for available updates for installed automations.
    
    Returns:
        List of automations with update_available flag
    """
    try:
        automation_manager = get_automation_manager()
        updates = await automation_manager.check_for_updates()
        
        return {"updates": updates, "total": len(updates)}
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))