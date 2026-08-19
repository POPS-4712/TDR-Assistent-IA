"""Pydantic schemas and security validation for the profile system."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_FORBIDDEN_FIELD_NAMES = {
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "token",
    "client_secret",
    "secret",
    "password",
    "credential",
    "credentials",
    "authorization",
    "bearer",
    "private_key",
    "n8n_api_key",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\b(?:sk|rk|pk)_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{16,}\b", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def _is_forbidden_field_name(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    return (
        normalized in _FORBIDDEN_FIELD_NAMES
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_api_key")
    )


def _assert_safe_payload(value: Any, path: str = "payload") -> None:
    """Reject secret-looking keys and values from profile data and configurations."""
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if _is_forbidden_field_name(key_text):
                raise ValueError(f"Sensitive field '{key_text}' is not allowed in profiles")
            _assert_safe_payload(item, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_safe_payload(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            raise ValueError(f"Sensitive value is not allowed in {path}")


class SafeModel(BaseModel):
    """Base schema that rejects undeclared fields and secret-like payloads."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_secrets(cls, value: Any) -> Any:
        _assert_safe_payload(value)
        return value


class ProfessionInput(SafeModel):
    name: str = Field(default="", max_length=160)
    sector: str = Field(default="", max_length=160)
    level: str = Field(default="", max_length=120)


class InterestInput(SafeModel):
    name: str = Field(min_length=1, max_length=160)
    weight: int = Field(default=5, ge=1, le=10)


class LocationInput(SafeModel):
    value: str = Field(min_length=1, max_length=160)
    country: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    region: Optional[str] = Field(default=None, max_length=120)
    remote: bool = False


class ProfilePreferencesInput(SafeModel):
    news_frequency: str = Field(default="daily", max_length=40)
    relevance_level: str = Field(default="high", max_length=40)
    sources: List[str] = Field(default_factory=list, max_length=30)
    preferred_schedule: Optional[str] = Field(default=None, max_length=120)
    notifications_enabled: bool = True
    additional_settings: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, values: List[str]) -> List[str]:
        return _clean_unique_strings(values, "sources")


class ProfileAutomationInput(SafeModel):
    automation_id: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    configuration: Dict[str, Any] = Field(default_factory=dict)


class ProfileBase(SafeModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    profession: ProfessionInput = Field(default_factory=ProfessionInput)
    goals: List[str] = Field(default_factory=list, max_length=30)
    languages: List[str] = Field(default_factory=list, max_length=30)
    excluded_topics: List[str] = Field(default_factory=list, max_length=50)

    @field_validator("goals", "languages", "excluded_topics")
    @classmethod
    def validate_tag_lists(cls, values: List[str]) -> List[str]:
        return _clean_unique_strings(values, "profile tags")


class ProfileCreate(ProfileBase):
    interests: List[InterestInput] = Field(default_factory=list, max_length=50)
    skills: List[str] = Field(default_factory=list, max_length=50)
    companies: List[str] = Field(default_factory=list, max_length=50)
    locations: List[LocationInput] = Field(default_factory=list, max_length=30)
    topics: List[str] = Field(default_factory=list, max_length=50)
    preferences: ProfilePreferencesInput = Field(default_factory=ProfilePreferencesInput)
    automations: List[ProfileAutomationInput] = Field(default_factory=list, max_length=100)
    is_enabled: bool = True
    activate: bool = False

    @field_validator("skills", "companies", "topics")
    @classmethod
    def validate_collection_lists(cls, values: List[str]) -> List[str]:
        return _clean_unique_strings(values, "profile collection")

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, values: List[InterestInput]) -> List[InterestInput]:
        names = [item.name.casefold() for item in values]
        if len(names) != len(set(names)):
            raise ValueError("Interest names must be unique")
        return values

    @field_validator("locations")
    @classmethod
    def validate_locations(cls, values: List[LocationInput]) -> List[LocationInput]:
        names = [item.value.casefold() for item in values]
        if len(names) != len(set(names)):
            raise ValueError("Location values must be unique")
        return values

    @field_validator("automations")
    @classmethod
    def validate_automations(cls, values: List[ProfileAutomationInput]) -> List[ProfileAutomationInput]:
        ids = [item.automation_id for item in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Automation IDs must be unique per profile")
        return values


class ProfileUpdate(SafeModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    profession: Optional[ProfessionInput] = None
    goals: Optional[List[str]] = Field(default=None, max_length=30)
    languages: Optional[List[str]] = Field(default=None, max_length=30)
    excluded_topics: Optional[List[str]] = Field(default=None, max_length=50)
    interests: Optional[List[InterestInput]] = Field(default=None, max_length=50)
    skills: Optional[List[str]] = Field(default=None, max_length=50)
    companies: Optional[List[str]] = Field(default=None, max_length=50)
    locations: Optional[List[LocationInput]] = Field(default=None, max_length=30)
    topics: Optional[List[str]] = Field(default=None, max_length=50)
    preferences: Optional[ProfilePreferencesInput] = None
    automations: Optional[List[ProfileAutomationInput]] = Field(default=None, max_length=100)
    is_enabled: Optional[bool] = None

    @field_validator("goals", "languages", "excluded_topics", "skills", "companies", "topics")
    @classmethod
    def validate_optional_tag_lists(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        return None if values is None else _clean_unique_strings(values, "profile tags")


class ProfileResponse(ProfileBase):
    id: UUID
    interests: List[InterestInput] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)
    locations: List[LocationInput] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    preferences: ProfilePreferencesInput = Field(default_factory=ProfilePreferencesInput)
    is_active: bool
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ProfileListResponse(SafeModel):
    profiles: List[ProfileResponse]
    total: int


class ProfileAutomationResponse(ProfileAutomationInput):
    updated_at: datetime


class ProfileAutomationListResponse(SafeModel):
    profile_id: UUID
    automations: List[ProfileAutomationResponse]
    total: int


class ProfileTemplateResponse(SafeModel):
    id: str
    name: str
    description: str
    icon: str
    data: Dict[str, Any]
    is_system: bool


class ProfileTemplateListResponse(SafeModel):
    templates: List[ProfileTemplateResponse]
    total: int


class ProfileContextResponse(SafeModel):
    profile_id: UUID
    profile_name: str
    profession: ProfessionInput
    interests: List[InterestInput]
    skills: List[str]
    companies: List[str]
    locations: List[LocationInput]
    languages: List[str]
    topics: List[str]
    excluded_topics: List[str]
    goals: List[str]
    preferences: ProfilePreferencesInput
    automation_defaults: Dict[str, Dict[str, Any]]


class ProfileExportData(ProfileCreate):
    """Portable profile representation that deliberately excludes server metadata."""

    activate: bool = False


class ProfileExportBundle(SafeModel):
    schema_version: str = "1.0"
    exported_at: datetime
    profile: ProfileExportData


class ProfileImportRequest(SafeModel):
    schema_version: str = Field(default="1.0", max_length=20)
    exported_at: Optional[datetime] = None
    profile: ProfileExportData
    activate: bool = False


def _clean_unique_strings(values: List[str], label: str) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{label} cannot contain empty values")
        if len(normalized) > 160:
            raise ValueError(f"{label} entries must be at most 160 characters")
        key = normalized.casefold()
        if key not in seen:
            cleaned.append(normalized)
            seen.add(key)
    return cleaned


class ProfileFromTemplateRequest(SafeModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    activate: bool = False
