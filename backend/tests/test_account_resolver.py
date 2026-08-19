"""Tests for public-safe automation account resolution."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.automations.account_resolver import AccountResolver
from app.services.automations.manifest_manager import Manifest, N8NConfig, Requirement


def _manifest(*, scopes=None, mapping=None):
    return Manifest(
        id="account-resolution-test",
        name="Account resolution test",
        description="Test manifest",
        version="1.0.0",
        category="testing",
        icon="flask",
        requirements=[Requirement(provider="google", type="oauth2", scopes=scopes or [])],
        n8n=N8NConfig(workflow_file="workflow.json", credential_mapping=mapping or {"gmailOAuth2": "google"}),
    )


def _credential(**overrides):
    values = {
        "provider": "google",
        "account_identifier": "Personal Google",
        "scopes": ["gmail.readonly"],
        "status": "active",
        "n8n_credential_id": "internal-n8n-credential-id",
        "credential_metadata": {"_n8n_credential_type": "gmailOAuth2", "safe_label": "Personal"},
        "expires_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_missing_account_is_blocked_with_safe_reason():
    result = AccountResolver().resolve(_manifest(), [])

    assert result["ready"] is False
    assert result["accounts"][0]["status"] == "missing"
    assert result["accounts"][0]["account"] is None
    assert "google: account not connected" in result["missing_requirements"]
    assert result["credential_mappings"][0]["compatible"] is False


def test_valid_account_with_required_scopes_and_mapping_is_ready():
    result = AccountResolver().resolve(
        _manifest(scopes=["gmail.readonly"]),
        [_credential()],
    )

    assert result["ready"] is True
    assert result["accounts"][0]["validation_status"] == "valid"
    assert result["accounts"][0]["scopes"] == {
        "required": ["gmail.readonly"],
        "granted": ["gmail.readonly"],
    }
    assert result["credential_mappings"][0]["status"] == "compatible"


def test_missing_scope_blocks_account_resolution():
    result = AccountResolver().resolve(
        _manifest(scopes=["gmail.readonly", "calendar"]),
        [_credential()],
    )

    assert result["ready"] is False
    assert result["accounts"][0]["validation_status"] == "blocked"
    assert "google: missing scopes: calendar" in result["missing_requirements"]


def test_invalid_or_expired_account_is_not_eligible():
    expired = _credential(expires_at=datetime.utcnow() - timedelta(minutes=1))
    result = AccountResolver().resolve(_manifest(), [expired])

    assert result["ready"] is False
    assert result["accounts"][0]["status"] == "reauth_required"
    assert result["accounts"][0]["validation_status"] == "invalid"


def test_incompatible_n8n_type_is_blocked_without_internal_reference():
    result = AccountResolver().resolve(
        _manifest(mapping={"googleCalendarOAuth2Api": "google"}),
        [_credential()],
    )

    assert result["ready"] is False
    mapping = result["credential_mappings"][0]
    assert mapping["compatible"] is False
    assert mapping["status"] == "missing_compatible_mapping"
    assert AccountResolver.MISSING_MAPPING_PREFIX in mapping["missing_requirements"][0]
    assert "internal-n8n-credential-id" not in str(result)
    assert "_n8n_credential_type" not in str(result)
