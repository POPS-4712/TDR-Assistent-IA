"""Regression tests for external runtime dependency handling."""

from unittest.mock import MagicMock

import pytest

from app.services.automations.manager import AutomationManager
from app.services.automations.manifest_manager import Manifest, ManifestManager, Metadata, N8NConfig


@pytest.mark.asyncio
async def test_external_runtime_dependencies_are_not_treated_as_automations():
    """Infrastructure prerequisites must not require automation metadata rows."""
    manager = AutomationManager(
        credential_manager=MagicMock(),
        n8n_client=MagicMock(),
        manifest_manager=MagicMock(),
    )
    manifest = MagicMock(dependencies=["postgresql", "playwright", "google-oauth2"])

    missing = await manager._validate_dependencies(manifest)

    assert missing == []


def test_manifest_validation_ignores_external_runtime_dependencies(tmp_path):
    """Manifest validation keeps infrastructure prerequisites outside the ID graph."""
    automation_dir = tmp_path / "test-auto"
    automation_dir.mkdir()
    (automation_dir / "workflow.json").write_text(
        '{"name":"Test","nodes":[],"connections":{},"settings":{}}',
        encoding="utf-8",
    )
    manager = ManifestManager()
    manager.AUTOMATIONS_DIR = tmp_path
    manager._manifests = {}
    manifest = Manifest(
        id="test-auto",
        name="Test",
        description="Test manifest",
        version="1.0.0",
        category="testing",
        icon="flask",
        dependencies=["postgresql", "playwright", "google-oauth2"],
        n8n=N8NConfig(workflow_file="workflow.json"),
        metadata=Metadata(),
    )

    assert manager.validate_manifest(manifest) == []
