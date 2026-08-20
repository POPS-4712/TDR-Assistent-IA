"""Tests for n8n Public API workflow imports."""

from unittest.mock import AsyncMock

import httpx
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


@pytest.mark.asyncio
async def test_public_api_authentication_requires_configured_key():
    """Missing configuration is blocked before making a network call."""
    client = N8NClient()
    client.api_key = None

    assert await client.validate_public_api_authentication() == {"status": "not_configured"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(200, "valid"), (401, "rejected"), (403, "rejected"), (500, "unavailable")],
)
async def test_public_api_authentication_classifies_response_without_exposing_content(status_code, expected):
    """Only the safe status classification leaves the n8n client boundary."""
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/workflows"
        assert request.url.params["limit"] == "1"
        return httpx.Response(status_code, json={"opaque": "response"})

    client = N8NClient()
    client.api_key = "test-public-api-key"
    client.client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client._get_headers(),
        transport=httpx.MockTransport(handler),
    )
    try:
        assert await client.validate_public_api_authentication() == {"status": expected}
    finally:
        await client.client.aclose()
