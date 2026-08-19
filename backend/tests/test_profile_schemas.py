import pytest
from pydantic import ValidationError

from app.schemas.profiles import ProfileCreate, ProfileImportRequest


def valid_profile_payload() -> dict:
    return {
        "name": "Perfil de prueba",
        "description": "Perfil local no sensible",
        "profession": {"name": "Engineer", "sector": "Technology", "level": ""},
        "interests": [{"name": "Automation", "weight": 8}],
        "skills": ["Python"],
        "companies": ["Example"],
        "locations": [{"value": "Madrid", "country": "Spain", "remote": True}],
        "languages": ["Spanish", "English"],
        "topics": ["Technology"],
        "excluded_topics": [],
        "goals": ["Follow industry news"],
        "preferences": {"news_frequency": "daily", "relevance_level": "high", "sources": []},
        "automations": [],
    }


def test_profile_accepts_safe_preferences_and_configuration() -> None:
    payload = valid_profile_payload()
    payload["automations"] = [
        {
            "automation_id": "news",
            "enabled": True,
            "configuration": {"topics": ["Technology"], "frequency": "daily"},
        }
    ]

    profile = ProfileCreate.model_validate(payload)

    assert profile.name == "Perfil de prueba"
    assert profile.automations[0].configuration["frequency"] == "daily"


@pytest.mark.parametrize(
    "field,value",
    [
        ("api_key", "sk_123456789012345678901234"),
        ("access_token", "not-allowed"),
        ("password", "not-allowed"),
    ],
)
def test_profile_rejects_secret_named_fields(field: str, value: str) -> None:
    payload = valid_profile_payload()
    payload["preferences"]["additional_settings"] = {field: value}

    with pytest.raises(ValidationError, match="not allowed"):
        ProfileCreate.model_validate(payload)


def test_profile_rejects_secret_looking_value() -> None:
    payload = valid_profile_payload()
    payload["topics"] = ["sk_123456789012345678901234"]

    with pytest.raises(ValidationError, match="Sensitive value"):
        ProfileCreate.model_validate(payload)


def test_import_rejects_secret_fields_before_restore() -> None:
    payload = {"schema_version": "1.0", "profile": valid_profile_payload()}
    payload["profile"]["automations"] = [
        {"automation_id": "news", "configuration": {"refresh_token": "not-allowed"}}
    ]

    with pytest.raises(ValidationError, match="Sensitive field"):
        ProfileImportRequest.model_validate(payload)


def test_import_accepts_complete_export_bundle_metadata() -> None:
    payload = {
        "schema_version": "1.0",
        "exported_at": "2026-08-18T18:00:00Z",
        "profile": valid_profile_payload(),
        "activate": False,
    }

    request = ProfileImportRequest.model_validate(payload)

    assert request.exported_at is not None
    assert request.profile.name == "Perfil de prueba"
