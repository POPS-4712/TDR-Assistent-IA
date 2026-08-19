"""FastAPI endpoints for local profile and personalization management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from ...core.logging import logger
from ...schemas.profiles import (
    ProfileAutomationInput,
    ProfileAutomationListResponse,
    ProfileAutomationResponse,
    ProfileContextResponse,
    ProfileCreate,
    ProfileExportBundle,
    ProfileFromTemplateRequest,
    ProfileImportRequest,
    ProfileListResponse,
    ProfileResponse,
    ProfileTemplateListResponse,
    ProfileUpdate,
)
from ...services.profiles import ProfileConflictError, ProfileManager, ProfileNotFoundError

router = APIRouter()
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get the stateless profile manager without initializing credential services."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def _raise_profile_http_error(error: Exception) -> None:
    if isinstance(error, ProfileNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ProfileConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    logger.exception("Unexpected profile operation failure")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Profile operation failed")


@router.get("", response_model=ProfileListResponse)
async def list_profiles() -> ProfileListResponse:
    """List local profiles, with the active profile first."""
    try:
        profiles = await get_profile_manager().list_profiles()
        return ProfileListResponse(profiles=profiles, total=len(profiles))
    except Exception as error:
        _raise_profile_http_error(error)


@router.get("/templates", response_model=ProfileTemplateListResponse)
async def list_profile_templates() -> ProfileTemplateListResponse:
    """List safe starting templates; no template contains account credentials."""
    try:
        templates = await get_profile_manager().list_templates()
        return ProfileTemplateListResponse(templates=templates, total=len(templates))
    except Exception as error:
        _raise_profile_http_error(error)


@router.post("/from-template/{template_id}", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile_from_template(
    template_id: str = Path(..., min_length=1, max_length=120),
    payload: ProfileFromTemplateRequest = ...,
) -> ProfileResponse:
    """Create a normal editable local profile from a selected template."""
    try:
        return await get_profile_manager().create_from_template(template_id, payload.name, payload.activate)
    except Exception as error:
        _raise_profile_http_error(error)


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate) -> ProfileResponse:
    """Create a custom, non-sensitive local profile."""
    try:
        return await get_profile_manager().create_profile(payload)
    except Exception as error:
        _raise_profile_http_error(error)


@router.post("/import", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def import_profile(payload: ProfileImportRequest) -> ProfileResponse:
    """Restore a validated profile export without accepting credentials or secrets."""
    try:
        return await get_profile_manager().import_profile(payload.profile, payload.activate)
    except Exception as error:
        _raise_profile_http_error(error)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: UUID = Path(...)) -> ProfileResponse:
    """Get one local profile."""
    try:
        return await get_profile_manager().get_profile(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: UUID, payload: ProfileUpdate) -> ProfileResponse:
    """Update profile metadata and configuration without touching accounts or workflows."""
    try:
        return await get_profile_manager().update_profile(profile_id, payload)
    except Exception as error:
        _raise_profile_http_error(error)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: UUID) -> None:
    """Delete only the selected profile and its dependent profile records."""
    try:
        await get_profile_manager().delete_profile(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)


@router.post("/{profile_id}/duplicate", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_profile(profile_id: UUID) -> ProfileResponse:
    """Duplicate a profile as a separate inactive local profile."""
    try:
        return await get_profile_manager().duplicate_profile(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)


@router.post("/{profile_id}/activate", response_model=ProfileResponse)
async def activate_profile(profile_id: UUID) -> ProfileResponse:
    """Switch the local active profile without affecting any credentials."""
    try:
        return await get_profile_manager().activate_profile(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)


@router.get("/{profile_id}/export", response_model=ProfileExportBundle)
async def export_profile(profile_id: UUID) -> ProfileExportBundle:
    """Export only portable preferences and automation configuration."""
    try:
        return await get_profile_manager().export_profile(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)


@router.get("/{profile_id}/automations", response_model=ProfileAutomationListResponse)
async def list_profile_automations(profile_id: UUID) -> ProfileAutomationListResponse:
    """List non-secret per-profile automation overrides."""
    try:
        automations = await get_profile_manager().list_profile_automations(profile_id)
        return ProfileAutomationListResponse(profile_id=profile_id, automations=automations, total=len(automations))
    except Exception as error:
        _raise_profile_http_error(error)


@router.put("/{profile_id}/automations/{automation_id}", response_model=ProfileAutomationResponse)
async def update_profile_automation(
    profile_id: UUID,
    automation_id: str = Path(..., min_length=1, max_length=255),
    payload: ProfileAutomationInput = ...,
) -> ProfileAutomationResponse:
    """Set the isolated configuration of one existing automation for one profile."""
    try:
        return await get_profile_manager().set_profile_automation(profile_id, automation_id, payload)
    except Exception as error:
        _raise_profile_http_error(error)


@router.get("/{profile_id}/context", response_model=ProfileContextResponse)
async def get_profile_context(profile_id: UUID) -> ProfileContextResponse:
    """Get structured secret-free context for automations and AI consumers."""
    try:
        return await get_profile_manager().get_context(profile_id)
    except Exception as error:
        _raise_profile_http_error(error)
