import pytest

from app.services.backup.manager import BackupManager, BackupValidationError, _clean


def safe_backup():
    return {
        "kind": "automation-center-metadata-backup",
        "schema_version": "1.0",
        "exported_at": "2026-08-18T00:00:00Z",
        "automations": [],
        "credential_metadata": [],
        "settings": [],
        "profile_templates": [],
        "profiles": [],
        "manifests": [],
    }


def test_clean_removes_secret_shaped_metadata_recursively():
    cleaned = _clean({
        "visible": {"nested": "ok", "api_key": "must-not-survive"},
        "token": "must-not-survive",
        "items": [{"name": "safe", "refresh_token": "must-not-survive"}],
    })

    assert cleaned == {"visible": {"nested": "ok"}, "items": [{"name": "safe"}]}


def test_validate_accepts_metadata_only_backup():
    result = BackupManager().validate_backup(safe_backup())

    assert result["valid"] is True
    assert result["automations"] == 0
    assert result["profiles"] == 0


@pytest.mark.parametrize("field_name", ["api_key", "access_token", "password", "authorization"])
def test_validate_rejects_sensitive_fields_anywhere(field_name):
    backup = safe_backup()
    backup["profiles"] = [{"name": "Safe", "preference": {field_name: "value"}}]

    with pytest.raises(BackupValidationError, match="Sensitive field"):
        BackupManager().validate_backup(backup)


def test_validate_rejects_unsupported_backup_kind():
    backup = safe_backup()
    backup["kind"] = "other"

    with pytest.raises(BackupValidationError, match="Unsupported backup kind"):
        BackupManager().validate_backup(backup)


def test_validate_rejects_altered_bundle_when_checksum_is_present():
    backup = safe_backup()
    backup["integrity_sha256"] = "0" * 64

    with pytest.raises(BackupValidationError, match="integrity checksum"):
        BackupManager().validate_backup(backup)


@pytest.mark.anyio
async def test_restore_dry_run_does_not_write_and_reports_snapshot_counts():
    backup = safe_backup()
    backup["automations"] = [{"id": "sample", "name": "Sample", "description": "", "version": "1.0"}]

    result = await BackupManager().restore_backup(backup, dry_run=True)

    assert result["restored"] is False
    assert result["dry_run"] is True
    assert result["automations"] == 1
