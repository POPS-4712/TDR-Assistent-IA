from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import profiles as profile_routes
from app.main import app
from app.schemas.profiles import (
    ProfileAutomationResponse,
    ProfileContextResponse,
    ProfileCreate,
    ProfileExportBundle,
    ProfileResponse,
    ProfileTemplateResponse,
    ProfilePreferencesInput,
    ProfessionInput,
)


PROFILE_ID = uuid4()


def make_profile(profile_id: UUID = PROFILE_ID, name: str = "Perfil de prueba") -> ProfileResponse:
    now = datetime.utcnow()
    return ProfileResponse(
        id=profile_id,
        name=name,
        description="Seguro y local",
        profession=ProfessionInput(name="Engineer", sector="Technology", level=""),
        interests=[],
        skills=["Python"],
        companies=[],
        locations=[],
        languages=["Spanish"],
        topics=["Automation"],
        excluded_topics=[],
        goals=["Follow industry news"],
        preferences=ProfilePreferencesInput(),
        is_active=True,
        is_enabled=True,
        created_at=now,
        updated_at=now,
    )


class FakeProfileManager:
    def __init__(self) -> None:
        self.profile = make_profile()
        self.create_calls = 0

    async def list_profiles(self):
        return [self.profile]

    async def get_profile(self, profile_id):
        return self.profile

    async def create_profile(self, payload: ProfileCreate):
        self.create_calls += 1
        self.profile = make_profile(name=payload.name)
        return self.profile

    async def update_profile(self, profile_id, payload):
        return self.profile

    async def delete_profile(self, profile_id):
        return None

    async def duplicate_profile(self, profile_id):
        return make_profile(uuid4(), "Perfil de prueba copy")

    async def activate_profile(self, profile_id):
        return self.profile

    async def list_templates(self):
        return [
            ProfileTemplateResponse(
                id="technology",
                name="Tecnología",
                description="Starting point",
                icon="code",
                data={},
                is_system=True,
            )
        ]

    async def create_from_template(self, template_id, name, activate):
        return make_profile(name=name or "Tecnología")

    async def list_profile_automations(self, profile_id):
        return []

    async def set_profile_automation(self, profile_id, automation_id, payload):
        return ProfileAutomationResponse(
            automation_id=automation_id,
            enabled=payload.enabled,
            configuration=payload.configuration,
            updated_at=datetime.utcnow(),
        )

    async def get_context(self, profile_id):
        profile = self.profile
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
            automation_defaults={"news": {"topics": ["Automation"]}},
        )

    async def export_profile(self, profile_id):
        raise AssertionError("Not required in this API contract test")

    async def import_profile(self, profile, activate):
        return make_profile(name=profile.name)


@pytest.fixture
def client(monkeypatch):
    manager = FakeProfileManager()
    monkeypatch.setattr(profile_routes, "_profile_manager", manager)
    return TestClient(app), manager


def test_lists_profiles(client) -> None:
    api_client, _ = client

    response = api_client.get("/api/v1/profiles")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["profiles"][0]["is_active"] is True


def test_creates_safe_profile(client) -> None:
    api_client, manager = client
    payload = {
        "name": "Perfil nuevo",
        "profession": {"name": "Designer", "sector": "Creative", "level": ""},
        "interests": [],
        "skills": [],
        "companies": [],
        "locations": [],
        "languages": ["Spanish"],
        "topics": [],
        "excluded_topics": [],
        "goals": [],
        "preferences": {"news_frequency": "weekly", "relevance_level": "medium", "sources": []},
        "automations": [],
    }

    response = api_client.post("/api/v1/profiles", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "Perfil nuevo"
    assert manager.create_calls == 1


def test_rejects_secret_before_profile_manager(client) -> None:
    api_client, manager = client
    payload = {
        "name": "Perfil inseguro",
        "profession": {"name": "Engineer", "sector": "Technology", "level": ""},
        "preferences": {"additional_settings": {"api_key": "sk_123456789012345678901234"}},
    }

    response = api_client.post("/api/v1/profiles", json=payload)

    assert response.status_code == 422
    assert manager.create_calls == 0


def test_exposes_only_structured_safe_context(client) -> None:
    api_client, _ = client

    response = api_client.get(f"/api/v1/profiles/{PROFILE_ID}/context")

    assert response.status_code == 200
    body = response.json()
    assert body["automation_defaults"]["news"]["topics"] == ["Automation"]
    assert "credentials" not in body
    assert "api_key" not in body
