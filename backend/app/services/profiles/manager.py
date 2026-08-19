"""Profile persistence and lifecycle management for Automation Center."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.db import get_session
from ...database.models import (
    Automation,
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
from ...schemas.profiles import (
    InterestInput,
    LocationInput,
    ProfileAutomationInput,
    ProfileAutomationResponse,
    ProfileContextResponse,
    ProfileCreate,
    ProfileExportBundle,
    ProfileExportData,
    ProfilePreferencesInput,
    ProfileResponse,
    ProfileTemplateResponse,
    ProfileUpdate,
    ProfessionInput,
)
from .engine import PersonalizationEngine, merge_configuration
from .templates import BUILTIN_PROFILE_TEMPLATES

logger = logging.getLogger(__name__)


class ProfileNotFoundError(ValueError):
    """Raised when a requested local profile does not exist."""


class ProfileConflictError(ValueError):
    """Raised when a profile operation would violate local uniqueness rules."""


class ProfileManager:
    """Manages non-sensitive local profiles without accessing credentials or n8n."""

    def __init__(self, personalization_engine: PersonalizationEngine | None = None):
        self.personalization_engine = personalization_engine or PersonalizationEngine()

    async def list_profiles(self) -> List[ProfileResponse]:
        """Return all profiles with their personalization metadata."""
        async with get_session() as session:
            result = await session.execute(
                select(Profile).order_by(Profile.is_active.desc(), Profile.created_at.asc())
            )
            return [await self._serialize_profile(session, profile) for profile in result.scalars().all()]

    async def get_profile(self, profile_id: UUID) -> ProfileResponse:
        """Return a complete profile or a clear not-found error."""
        async with get_session() as session:
            profile = await self._require_profile(session, profile_id)
            return await self._serialize_profile(session, profile)

    async def create_profile(self, data: ProfileCreate) -> ProfileResponse:
        """Create a profile and its related non-sensitive records atomically."""
        async with get_session() as session:
            await self._ensure_name_available(session, data.name)
            profile_count = await session.scalar(select(func.count()).select_from(Profile)) or 0
            should_activate = bool(data.activate or profile_count == 0)
            if should_activate:
                await self._deactivate_all(session)

            profile = Profile(
                name=data.name,
                description=data.description,
                profession_name=data.profession.name,
                profession_sector=data.profession.sector,
                profession_level=data.profession.level,
                goals=data.goals,
                languages=data.languages,
                excluded_topics=data.excluded_topics,
                is_active=should_activate,
                is_enabled=data.is_enabled,
            )
            session.add(profile)
            await session.flush()
            await self._replace_profile_details(session, profile.id, data)
            await session.flush()
            response = await self._serialize_profile(session, profile)

        logger.info("Created profile id=%s active=%s", response.id, response.is_active)
        return response

    async def update_profile(self, profile_id: UUID, data: ProfileUpdate) -> ProfileResponse:
        """Update only declared profile fields, preserving independent credentials and workflows."""
        async with get_session() as session:
            profile = await self._require_profile(session, profile_id)
            changes = data.model_dump(exclude_unset=True)
            if "name" in changes and changes["name"] != profile.name:
                await self._ensure_name_available(session, changes["name"], exclude_profile_id=profile_id)
                profile.name = changes["name"]
            if "description" in changes:
                profile.description = changes["description"]
            if "profession" in changes:
                profession = data.profession or ProfessionInput()
                profile.profession_name = profession.name
                profile.profession_sector = profession.sector
                profile.profession_level = profession.level
            for field_name in ("goals", "languages", "excluded_topics"):
                if field_name in changes:
                    setattr(profile, field_name, changes[field_name])
            if "is_enabled" in changes:
                profile.is_enabled = changes["is_enabled"]
                if not profile.is_enabled and profile.is_active:
                    profile.is_active = False

            await self._replace_updated_details(session, profile.id, data, changes)
            profile.updated_at = datetime.utcnow()
            await session.flush()
            response = await self._serialize_profile(session, profile)

        logger.info("Updated profile id=%s", profile_id)
        return response

    async def delete_profile(self, profile_id: UUID) -> None:
        """Delete a profile and its related configuration, never accounts or credentials."""
        async with get_session() as session:
            profile = await self._require_profile(session, profile_id)
            was_active = profile.is_active
            await session.delete(profile)
            await session.flush()
            if was_active:
                replacement = await session.scalar(
                    select(Profile)
                    .where(Profile.is_enabled.is_(True))
                    .order_by(Profile.created_at.asc())
                    .limit(1)
                )
                if replacement:
                    replacement.is_active = True
                    replacement.updated_at = datetime.utcnow()

        logger.info("Deleted profile id=%s", profile_id)

    async def duplicate_profile(self, profile_id: UUID) -> ProfileResponse:
        """Create an editable duplicate with a distinct local name and inactive state."""
        source = await self.get_profile(profile_id)
        duplicated_name = await self._next_duplicate_name(source.name)
        payload = ProfileCreate(
            name=duplicated_name,
            description=source.description,
            profession=source.profession,
            interests=source.interests,
            skills=source.skills,
            companies=source.companies,
            locations=source.locations,
            languages=source.languages,
            topics=source.topics,
            excluded_topics=source.excluded_topics,
            goals=source.goals,
            preferences=source.preferences,
            automations=await self._automation_inputs(profile_id),
            is_enabled=source.is_enabled,
            activate=False,
        )
        return await self.create_profile(payload)

    async def activate_profile(self, profile_id: UUID) -> ProfileResponse:
        """Make exactly one enabled profile active without changing workflows or credentials."""
        async with get_session() as session:
            profile = await self._require_profile(session, profile_id)
            if not profile.is_enabled:
                raise ValueError("Disabled profiles cannot be activated")
            await self._deactivate_all(session)
            profile.is_active = True
            profile.updated_at = datetime.utcnow()
            await session.flush()
            response = await self._serialize_profile(session, profile)

        logger.info("Activated profile id=%s", profile_id)
        return response

    async def list_templates(self) -> List[ProfileTemplateResponse]:
        """Seed missing built-in templates and return safe template metadata."""
        await self.ensure_builtin_templates()
        async with get_session() as session:
            result = await session.execute(select(ProfileTemplate).order_by(ProfileTemplate.name.asc()))
            return [self._serialize_template(template) for template in result.scalars().all()]

    async def ensure_builtin_templates(self) -> None:
        """Idempotently store built-in starting points without overwriting custom records."""
        async with get_session() as session:
            for item in BUILTIN_PROFILE_TEMPLATES:
                template = await session.get(ProfileTemplate, item["id"])
                if template is None:
                    session.add(
                        ProfileTemplate(
                            id=item["id"],
                            name=item["name"],
                            description=item["description"],
                            icon=item["icon"],
                            template_data=item["data"],
                            is_system=True,
                        )
                    )

    async def create_from_template(self, template_id: str, name: str | None, activate: bool) -> ProfileResponse:
        """Create a normal editable profile from a built-in or local template."""
        await self.ensure_builtin_templates()
        async with get_session() as session:
            template = await session.get(ProfileTemplate, template_id)
            if template is None:
                raise ProfileNotFoundError("Profile template not found")
            data = dict(template.template_data or {})
            data["name"] = name or template.name
            data["description"] = template.description
            data["activate"] = activate
            payload = ProfileCreate.model_validate(data)
        return await self.create_profile(payload)

    async def list_profile_automations(self, profile_id: UUID) -> List[ProfileAutomationResponse]:
        """Return only profile-specific configuration, separate from automation workflow files."""
        async with get_session() as session:
            await self._require_profile(session, profile_id)
            result = await session.execute(
                select(ProfileAutomation)
                .where(ProfileAutomation.profile_id == profile_id)
                .order_by(ProfileAutomation.automation_id.asc())
            )
            return [
                ProfileAutomationResponse(
                    automation_id=item.automation_id,
                    enabled=item.enabled,
                    configuration=item.configuration or {},
                    updated_at=item.updated_at,
                )
                for item in result.scalars().all()
            ]

    async def set_profile_automation(
        self,
        profile_id: UUID,
        automation_id: str,
        data: ProfileAutomationInput,
    ) -> ProfileAutomationResponse:
        """Persist a safe configuration override for an existing Automation Center automation."""
        if automation_id != data.automation_id:
            raise ValueError("Automation ID in the path must match the request body")
        async with get_session() as session:
            await self._require_profile(session, profile_id)
            automation = await session.get(Automation, automation_id)
            if automation is None:
                raise ProfileNotFoundError("Automation not found")
            result = await session.execute(
                select(ProfileAutomation).where(
                    ProfileAutomation.profile_id == profile_id,
                    ProfileAutomation.automation_id == automation_id,
                )
            )
            profile_automation = result.scalar_one_or_none()
            if profile_automation is None:
                profile_automation = ProfileAutomation(
                    profile_id=profile_id,
                    automation_id=automation_id,
                    enabled=data.enabled,
                    configuration=data.configuration,
                )
                session.add(profile_automation)
            else:
                profile_automation.enabled = data.enabled
                profile_automation.configuration = data.configuration
                profile_automation.updated_at = datetime.utcnow()
            await session.flush()
            response = ProfileAutomationResponse(
                automation_id=profile_automation.automation_id,
                enabled=profile_automation.enabled,
                configuration=profile_automation.configuration or {},
                updated_at=profile_automation.updated_at,
            )

        logger.info("Updated profile automation profile_id=%s automation_id=%s", profile_id, automation_id)
        return response

    async def get_context(self, profile_id: UUID) -> ProfileContextResponse:
        """Return structured, secret-free context for local automations and AI integrations."""
        profile = await self.get_profile(profile_id)
        defaults = self.personalization_engine.build_automation_defaults(profile.model_dump(mode="json"))
        automations = await self.list_profile_automations(profile_id)
        for automation in automations:
            base = defaults.get(automation.automation_id, {})
            defaults[automation.automation_id] = merge_configuration(
                base,
                {"enabled": automation.enabled, **automation.configuration},
            )
        return ProfileContextResponse(
            profile_id=profile.id,
            profile_name=profile.name,
            profession=profile.profession,
            interests=profile.interests,
            skills=profile.skills,
            companies=profile.companies,
            locations=profile.locations,
            languages=profile.languages,
            topics=profile.topics,
            excluded_topics=profile.excluded_topics,
            goals=profile.goals,
            preferences=profile.preferences,
            automation_defaults=defaults,
        )

    async def export_profile(self, profile_id: UUID) -> ProfileExportBundle:
        """Export preferences and configurations only; persistence metadata and secrets are omitted."""
        profile = await self.get_profile(profile_id)
        export_data = ProfileExportData(
            name=profile.name,
            description=profile.description,
            profession=profile.profession,
            interests=profile.interests,
            skills=profile.skills,
            companies=profile.companies,
            locations=profile.locations,
            languages=profile.languages,
            topics=profile.topics,
            excluded_topics=profile.excluded_topics,
            goals=profile.goals,
            preferences=profile.preferences,
            automations=await self._automation_inputs(profile_id),
            is_enabled=profile.is_enabled,
            activate=False,
        )
        return ProfileExportBundle(exported_at=datetime.utcnow(), profile=export_data)

    async def import_profile(self, data: ProfileExportData, activate: bool = False) -> ProfileResponse:
        """Restore a safe exported profile as a new local profile."""
        payload = ProfileCreate.model_validate({**data.model_dump(), "activate": activate})
        return await self.create_profile(payload)

    async def _automation_inputs(self, profile_id: UUID) -> List[ProfileAutomationInput]:
        automations = await self.list_profile_automations(profile_id)
        return [
            ProfileAutomationInput(
                automation_id=item.automation_id,
                enabled=item.enabled,
                configuration=item.configuration,
            )
            for item in automations
        ]

    async def _next_duplicate_name(self, base_name: str) -> str:
        async with get_session() as session:
            index = 2
            candidate = f"{base_name} copy"
            while await self._name_exists(session, candidate):
                candidate = f"{base_name} copy {index}"
                index += 1
            return candidate[:120]

    async def _require_profile(self, session: AsyncSession, profile_id: UUID) -> Profile:
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ProfileNotFoundError("Profile not found")
        return profile

    async def _ensure_name_available(
        self,
        session: AsyncSession,
        name: str,
        exclude_profile_id: UUID | None = None,
    ) -> None:
        if await self._name_exists(session, name, exclude_profile_id):
            raise ProfileConflictError("A profile with this name already exists")

    async def _name_exists(
        self,
        session: AsyncSession,
        name: str,
        exclude_profile_id: UUID | None = None,
    ) -> bool:
        statement = select(Profile.id).where(func.lower(Profile.name) == name.casefold())
        if exclude_profile_id is not None:
            statement = statement.where(Profile.id != exclude_profile_id)
        return (await session.scalar(statement)) is not None

    async def _deactivate_all(self, session: AsyncSession) -> None:
        await session.execute(
            update(Profile).where(Profile.is_active.is_(True)).values(is_active=False, updated_at=datetime.utcnow())
        )

    async def _replace_profile_details(self, session: AsyncSession, profile_id: UUID, data: ProfileCreate) -> None:
        session.add(
            ProfilePreference(
                profile_id=profile_id,
                news_frequency=data.preferences.news_frequency,
                relevance_level=data.preferences.relevance_level,
                sources=data.preferences.sources,
                preferred_schedule=data.preferences.preferred_schedule,
                notifications_enabled=data.preferences.notifications_enabled,
                additional_settings=data.preferences.additional_settings,
            )
        )
        await self._replace_collection(session, ProfileInterest, profile_id, data.interests, "interests")
        await self._replace_collection(session, ProfileSkill, profile_id, data.skills, "skills")
        await self._replace_collection(session, ProfileCompany, profile_id, data.companies, "companies")
        await self._replace_collection(session, ProfileLocation, profile_id, data.locations, "locations")
        await self._replace_collection(session, ProfileTopic, profile_id, data.topics, "topics")
        await self._replace_automations(session, profile_id, data.automations)

    async def _replace_updated_details(
        self,
        session: AsyncSession,
        profile_id: UUID,
        data: ProfileUpdate,
        changes: Dict[str, Any],
    ) -> None:
        if "preferences" in changes:
            await session.execute(delete(ProfilePreference).where(ProfilePreference.profile_id == profile_id))
            preferences = data.preferences or ProfilePreferencesInput()
            session.add(
                ProfilePreference(
                    profile_id=profile_id,
                    news_frequency=preferences.news_frequency,
                    relevance_level=preferences.relevance_level,
                    sources=preferences.sources,
                    preferred_schedule=preferences.preferred_schedule,
                    notifications_enabled=preferences.notifications_enabled,
                    additional_settings=preferences.additional_settings,
                )
            )
        for key, model, value in (
            ("interests", ProfileInterest, data.interests),
            ("skills", ProfileSkill, data.skills),
            ("companies", ProfileCompany, data.companies),
            ("locations", ProfileLocation, data.locations),
            ("topics", ProfileTopic, data.topics),
        ):
            if key in changes:
                await self._replace_collection(session, model, profile_id, value or [], key)
        if "automations" in changes:
            await self._replace_automations(session, profile_id, data.automations or [])

    async def _replace_collection(
        self,
        session: AsyncSession,
        model: Any,
        profile_id: UUID,
        values: Iterable[Any],
        collection_name: str,
    ) -> None:
        await session.execute(delete(model).where(model.profile_id == profile_id))
        if collection_name == "interests":
            session.add_all(
                [ProfileInterest(profile_id=profile_id, name=item.name, weight=item.weight) for item in values]
            )
        elif collection_name == "locations":
            session.add_all(
                [
                    ProfileLocation(
                        profile_id=profile_id,
                        value=item.value,
                        country=item.country,
                        city=item.city,
                        region=item.region,
                        remote=item.remote,
                    )
                    for item in values
                ]
            )
        else:
            session.add_all([model(profile_id=profile_id, name=item) for item in values])

    async def _replace_automations(
        self,
        session: AsyncSession,
        profile_id: UUID,
        values: Iterable[ProfileAutomationInput],
    ) -> None:
        await session.execute(delete(ProfileAutomation).where(ProfileAutomation.profile_id == profile_id))
        for item in values:
            automation = await session.get(Automation, item.automation_id)
            if automation is None:
                raise ProfileNotFoundError(f"Automation not found: {item.automation_id}")
            session.add(
                ProfileAutomation(
                    profile_id=profile_id,
                    automation_id=item.automation_id,
                    enabled=item.enabled,
                    configuration=item.configuration,
                )
            )

    async def _serialize_profile(self, session: AsyncSession, profile: Profile) -> ProfileResponse:
        preferences = await session.get(ProfilePreference, profile.id)
        interests = await self._list_children(session, ProfileInterest, profile.id)
        skills = await self._list_children(session, ProfileSkill, profile.id)
        companies = await self._list_children(session, ProfileCompany, profile.id)
        locations = await self._list_children(session, ProfileLocation, profile.id)
        topics = await self._list_children(session, ProfileTopic, profile.id)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            profession=ProfessionInput(
                name=profile.profession_name,
                sector=profile.profession_sector,
                level=profile.profession_level,
            ),
            interests=[InterestInput(name=item.name, weight=item.weight) for item in interests],
            skills=[item.name for item in skills],
            companies=[item.name for item in companies],
            locations=[
                LocationInput(
                    value=item.value,
                    country=item.country,
                    city=item.city,
                    region=item.region,
                    remote=item.remote,
                )
                for item in locations
            ],
            languages=profile.languages or [],
            topics=[item.name for item in topics],
            excluded_topics=profile.excluded_topics or [],
            goals=profile.goals or [],
            preferences=ProfilePreferencesInput(
                news_frequency=preferences.news_frequency if preferences else "daily",
                relevance_level=preferences.relevance_level if preferences else "high",
                sources=preferences.sources if preferences else [],
                preferred_schedule=preferences.preferred_schedule if preferences else None,
                notifications_enabled=preferences.notifications_enabled if preferences else True,
                additional_settings=preferences.additional_settings if preferences else {},
            ),
            is_active=profile.is_active,
            is_enabled=profile.is_enabled,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    async def _list_children(self, session: AsyncSession, model: Any, profile_id: UUID) -> List[Any]:
        result = await session.execute(
            select(model).where(model.profile_id == profile_id).order_by(model.name if hasattr(model, "name") else model.value)
        )
        return list(result.scalars().all())

    @staticmethod
    def _serialize_template(template: ProfileTemplate) -> ProfileTemplateResponse:
        return ProfileTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            icon=template.icon,
            data=template.template_data or {},
            is_system=template.is_system,
        )
