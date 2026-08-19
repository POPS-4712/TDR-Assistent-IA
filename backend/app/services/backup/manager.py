"""Portable, local backup of Automation Center metadata without secrets."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List
from uuid import uuid4

import yaml
from sqlalchemy import select

from ...database.db import get_session
from ...database.models import (
    Automation,
    AutomationCenterSetting,
    Credential,
    Profile,
    ProfileAutomation,
    ProfileCompany,
    ProfileInterest,
    ProfileLocation,
    ProfilePreference,
    ProfileSkill,
    ProfileTemplate,
    ProfileTopic,
)

SCHEMA_VERSION = "1.0"
SENSITIVE_MARKERS = (
    "api_key", "apikey", "access_token", "refresh_token", "token", "secret",
    "password", "authorization", "private_key", "encryption_key",
)


class BackupValidationError(ValueError):
    """Raised when a backup is malformed or contains prohibited data."""


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "hex") and hasattr(value, "__str__"):
        return str(value)
    return value


def _clean(value: Any) -> Any:
    """Recursively remove secret-shaped fields from exported data."""
    if isinstance(value, dict):
        return {
            str(key): _clean(item)
            for key, item in value.items()
            if not any(marker in str(key).casefold() for marker in SENSITIVE_MARKERS)
        }
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return _iso(value)


def _assert_safe(value: Any, path: str = "backup") -> None:
    """Reject restore payloads containing secret-shaped keys anywhere."""
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).casefold()
            if any(marker in key_text for marker in SENSITIVE_MARKERS):
                raise BackupValidationError(f"Sensitive field is not allowed at {path}.{key}")
            _assert_safe(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_safe(item, f"{path}[{index}]")


def _automation_data(item: Automation) -> Dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "version": item.version,
        "dependencies": list(item.dependencies or []),
        # n8n IDs and installed/enabled state are instance-specific and must not
        # be restored as if their remote workflows still existed.
        "restore_status": "discovered",
    }


def _credential_metadata(item: Credential) -> Dict[str, Any]:
    return {
        "provider": item.provider,
        "account_identifier": item.account_identifier,
        "scopes": list(item.scopes or []),
        "status": "requires_reauth",
        "expires_at": _iso(item.expires_at),
    }


class BackupManager:
    """Exports and restores safe local metadata without workflow secrets."""

    def __init__(self, automations_dir: Path | None = None):
        self.automations_dir = automations_dir or Path("/app/automations")

    async def create_backup(self) -> Dict[str, Any]:
        async with get_session() as session:
            automations = (await session.scalars(select(Automation))).all()
            credentials = (await session.scalars(select(Credential))).all()
            settings = (await session.scalars(select(AutomationCenterSetting))).all()
            templates = (await session.scalars(select(ProfileTemplate))).all()
            profiles = (await session.scalars(select(Profile))).all()

            profile_data = [await self._export_profile(session, profile) for profile in profiles]
            manifest_data = self._export_manifests()
            payload = {
                "kind": "automation-center-metadata-backup",
                "schema_version": SCHEMA_VERSION,
                "exported_at": datetime.utcnow().isoformat(),
                "automations": [_automation_data(item) for item in automations],
                "credential_metadata": [_credential_metadata(item) for item in credentials],
                "settings": [
                    {"key": item.key, "value": _clean(item.value)}
                    for item in settings
                    if not any(marker in str(item.key).casefold() for marker in SENSITIVE_MARKERS)
                ],
                "profile_templates": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "icon": item.icon,
                        "template_data": _clean(item.template_data),
                        "is_system": item.is_system,
                    }
                    for item in templates
                ],
                "profiles": profile_data,
                "manifests": manifest_data,
            }
        safe_payload = _clean(payload)
        _assert_safe(safe_payload)
        encoded = json.dumps(safe_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        safe_payload["integrity_sha256"] = hashlib.sha256(encoded).hexdigest()
        return safe_payload

    def validate_backup(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(bundle, dict):
            raise BackupValidationError("Backup must be a JSON object")
        if bundle.get("kind") != "automation-center-metadata-backup":
            raise BackupValidationError("Unsupported backup kind")
        if bundle.get("schema_version") != SCHEMA_VERSION:
            raise BackupValidationError("Unsupported backup schema version")
        integrity = bundle.get("integrity_sha256")
        if integrity is not None:
            content = {key: value for key, value in bundle.items() if key != "integrity_sha256"}
            expected = hashlib.sha256(
                json.dumps(content, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if integrity != expected:
                raise BackupValidationError("Backup integrity checksum does not match")
        _assert_safe(bundle)
        for key in ("automations", "settings", "profile_templates", "profiles", "manifests"):
            if not isinstance(bundle.get(key, []), list):
                raise BackupValidationError(f"Backup field '{key}' must be a list")
        return {
            "valid": True,
            "automations": len(bundle.get("automations", [])),
            "profiles": len(bundle.get("profiles", [])),
            "settings": len(bundle.get("settings", [])),
            "manifests": len(bundle.get("manifests", [])),
        }

    async def restore_backup(self, bundle: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        summary = self.validate_backup(bundle)
        if dry_run:
            return {**summary, "restored": False, "dry_run": True}

        restored = {"automations": 0, "credentials": 0, "settings": 0, "templates": 0, "profiles": 0}
        async with get_session() as session:
            for data in bundle.get("automations", []):
                if await session.get(Automation, data["id"]):
                    continue
                session.add(Automation(
                    id=data["id"], name=data["name"], description=data.get("description", ""),
                    version=data.get("version", "1.0.0"), status="discovered",
                    dependencies=data.get("dependencies", []), n8n_workflow_id=None,
                ))
                restored["automations"] += 1

            for data in bundle.get("credential_metadata", []):
                exists = await session.scalar(select(Credential).where(
                    Credential.provider == data["provider"],
                    Credential.account_identifier == data["account_identifier"],
                ))
                if exists:
                    continue
                session.add(Credential(
                    provider=data["provider"], account_identifier=data["account_identifier"],
                    scopes=data.get("scopes", []), status="requires_reauth", n8n_credential_id=None,
                ))
                restored["credentials"] += 1

            for data in bundle.get("settings", []):
                setting = await session.get(AutomationCenterSetting, data["key"])
                if setting is None:
                    session.add(AutomationCenterSetting(key=data["key"], value=data.get("value", {})))
                    restored["settings"] += 1

            for data in bundle.get("profile_templates", []):
                if await session.get(ProfileTemplate, data["id"]):
                    continue
                session.add(ProfileTemplate(
                    id=data["id"], name=data["name"], description=data.get("description", ""),
                    icon=data.get("icon", "profile"), template_data=data.get("template_data", {}),
                    is_system=bool(data.get("is_system", False)),
                ))
                restored["templates"] += 1

            for data in bundle.get("profiles", []):
                if await self._restore_profile(session, data):
                    restored["profiles"] += 1
        return {**summary, "restored": True, "dry_run": False, **restored}

    async def _export_profile(self, session: Any, profile: Profile) -> Dict[str, Any]:
        profile_id = profile.id
        preference = await session.get(ProfilePreference, profile_id)
        interests = (await session.scalars(select(ProfileInterest).where(ProfileInterest.profile_id == profile_id))).all()
        skills = (await session.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile_id))).all()
        companies = (await session.scalars(select(ProfileCompany).where(ProfileCompany.profile_id == profile_id))).all()
        locations = (await session.scalars(select(ProfileLocation).where(ProfileLocation.profile_id == profile_id))).all()
        topics = (await session.scalars(select(ProfileTopic).where(ProfileTopic.profile_id == profile_id))).all()
        automations = (await session.scalars(select(ProfileAutomation).where(ProfileAutomation.profile_id == profile_id))).all()
        return _clean({
            "name": profile.name, "description": profile.description,
            "profession_name": profile.profession_name, "profession_sector": profile.profession_sector,
            "profession_level": profile.profession_level, "goals": profile.goals,
            "languages": profile.languages, "excluded_topics": profile.excluded_topics,
            "is_enabled": profile.is_enabled,
            "preference": None if preference is None else {
                "news_frequency": preference.news_frequency, "relevance_level": preference.relevance_level,
                "sources": preference.sources, "preferred_schedule": preference.preferred_schedule,
                "notifications_enabled": preference.notifications_enabled,
                "additional_settings": preference.additional_settings,
            },
            "interests": [{"name": item.name, "weight": item.weight} for item in interests],
            "skills": [item.name for item in skills], "companies": [item.name for item in companies],
            "locations": [{"value": item.value, "country": item.country, "city": item.city, "region": item.region, "remote": item.remote} for item in locations],
            "topics": [item.name for item in topics],
            "automations": [{"automation_id": item.automation_id, "enabled": item.enabled, "configuration": item.configuration} for item in automations],
        })

    async def _restore_profile(self, session: Any, data: Dict[str, Any]) -> bool:
        name = str(data.get("name", "Restored profile"))[:120]
        if await session.scalar(select(Profile.id).where(Profile.name == name)):
            return False
        profile_id = uuid4()
        session.add(Profile(
            id=profile_id, name=name, description=data.get("description", ""),
            profession_name=data.get("profession_name", ""), profession_sector=data.get("profession_sector", ""),
            profession_level=data.get("profession_level", ""), goals=data.get("goals", []),
            languages=data.get("languages", []), excluded_topics=data.get("excluded_topics", []),
            is_active=False, is_enabled=bool(data.get("is_enabled", True)),
        ))
        preference = data.get("preference") or {}
        session.add(ProfilePreference(
            profile_id=profile_id, news_frequency=preference.get("news_frequency", "daily"),
            relevance_level=preference.get("relevance_level", "high"), sources=preference.get("sources", []),
            preferred_schedule=preference.get("preferred_schedule"),
            notifications_enabled=bool(preference.get("notifications_enabled", True)),
            additional_settings=preference.get("additional_settings", {}),
        ))
        session.add_all([ProfileInterest(profile_id=profile_id, name=item["name"], weight=item.get("weight", 5)) for item in data.get("interests", [])])
        session.add_all([ProfileSkill(profile_id=profile_id, name=name) for name in data.get("skills", [])])
        session.add_all([ProfileCompany(profile_id=profile_id, name=name) for name in data.get("companies", [])])
        session.add_all([ProfileLocation(profile_id=profile_id, **item) for item in data.get("locations", [])])
        session.add_all([ProfileTopic(profile_id=profile_id, name=name) for name in data.get("topics", [])])
        for item in data.get("automations", []):
            if await session.get(Automation, item["automation_id"]):
                session.add(ProfileAutomation(profile_id=profile_id, automation_id=item["automation_id"], enabled=bool(item.get("enabled", True)), configuration=item.get("configuration", {})))
        return True

    def _export_manifests(self) -> List[Dict[str, Any]]:
        manifests: List[Dict[str, Any]] = []
        if not self.automations_dir.exists():
            return manifests
        for path in sorted(self.automations_dir.glob("*/manifest.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            manifests.append({"automation_id": path.parent.name, "content": _clean(raw)})
        return manifests
