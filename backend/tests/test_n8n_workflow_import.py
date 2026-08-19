"""Tests for n8n Public API workflow imports."""

from unittest.mock import AsyncMock

import pytest

from app.services.n8n.client import N8NClient


@pytest.mark.asyncio
async def test_import_workflow_removes_server_managed_export_fields():
    """The Public API receives only create-workflow fields from an export."""
    client = N8NClient()
    client._request = AsyncMock(return_value={"id": "workflow-123"})
    workflow_export = {
        "name": "Test Workflow",
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"},
        "active": False,
        "versionId": "version-1",
        "versionCounter": 1,
        "triggerCount": 0,
        "tags": [],
    }

    workflow_id = await client.import_workflow(workflow_export)

    assert workflow_id == "workflow-123"
    client._request.assert_awaited_once_with(
        "POST",
        "/api/v1/workflows",
        json={
            "name": "Test Workflow",
            "nodes": [],
            "connections": {},
            "settings": {"executionOrder": "v1"},
        },
    )


@pytest.mark.asyncio
async def test_deactivate_workflow_uses_public_api_deactivate_route():
    """n8n 1.121 expects POST on the dedicated deactivate route."""
    client = N8NClient()
    client._request = AsyncMock(return_value={})

    await client.deactivate_workflow("workflow-123")

    client._request.assert_awaited_once_with(
        "POST",
        "/api/v1/workflows/workflow-123/deactivate",
    )
