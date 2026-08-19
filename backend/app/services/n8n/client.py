"""
n8n Client for Automation Center.
Provides methods to interact with n8n API for workflow and credential management.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from ...core.config import settings

logger = logging.getLogger(__name__)

class N8NClient:
    """
    Client for n8n API.
    
    All methods are async and use httpx for HTTP requests.
    Credentials are never passed to the frontend.
    """
    
    def __init__(self):
        self.base_url = settings.N8N_API_URL.rstrip("/")
        self.api_key = settings.N8N_API_KEY
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=60.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for n8n API requests."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to n8n API."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("n8n API error: HTTP %s", e.response.status_code)
            raise
    
    async def create_credential(
        self,
        credential_type: str,
        credentials: Dict[str, Any],
        name: Optional[str] = None
    ) -> str:
        """
        Create a new credential in n8n.
        
        Args:
            credential_type: Type of credential (e.g., googleOAuth2Api, postgres)
            credentials: The credential data
            name: Optional name for the credential
            
        Returns:
            The n8n credential ID
        """
        payload = {
            "name": name or f"automation-center-{credential_type}-{__import__('uuid').uuid4().hex[:8]}",
            "type": credential_type,
            "nodesAccess": {},
            "credentials": credentials
        }
        
        result = await self._request("POST", "/api/v1/credentials", json=payload)
        return result["id"]
    
    async def update_credential(
        self,
        credential_id: str,
        credentials: Dict[str, Any]
    ) -> None:
        """
        Update an existing credential in n8n.
        
        Args:
            credential_id: n8n credential ID
            credentials: New credential data
        """
        await self._request("PUT", f"/api/v1/credentials/{credential_id}", json={"credentials": credentials})
    
    async def delete_credential(self, credential_id: str) -> None:
        """
        Delete a credential from n8n.
        
        Args:
            credential_id: n8n credential ID
        """
        await self._request("DELETE", f"/api/v1/credentials/{credential_id}")
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow details from n8n.
        
        Args:
            workflow_id: n8n workflow ID
            
        Returns:
            Workflow details
        """
        return await self._request("GET", f"/api/v1/workflows/{workflow_id}")
    
    async def import_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Create a workflow through the n8n Public API.

        Workflow exports contain server-managed fields such as ``active``,
        ``versionId``, and ``tags``. n8n 1.121 rejects those read-only fields
        on ``POST /api/v1/workflows`` because the request schema forbids extra
        properties. Keep the source export intact and send only fields accepted
        by the create-workflow contract.
        """
        allowed_fields = {
            "name",
            "description",
            "nodes",
            "connections",
            "settings",
            "nodeGroups",
            "staticData",
            "pinData",
            "projectId",
            "parentFolderId",
        }
        payload = {key: value for key, value in workflow_data.items() if key in allowed_fields}
        result = await self._request("POST", "/api/v1/workflows", json=payload)
        return result["id"]
    
    async def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> None:
        """
        Update an existing workflow in n8n.
        
        Args:
            workflow_id: n8n workflow ID
            workflow_data: Updated workflow definition
        """
        allowed_fields = {
            "name", "description", "nodes", "connections", "settings",
            "nodeGroups", "staticData", "pinData", "projectId", "parentFolderId",
        }
        payload = {key: value for key, value in workflow_data.items() if key in allowed_fields}
        await self._request("PUT", f"/api/v1/workflows/{workflow_id}", json=payload)
    
    async def delete_workflow(self, workflow_id: str) -> None:
        """
        Delete a workflow from n8n.
        
        Args:
            workflow_id: n8n workflow ID
        """
        await self._request("DELETE", f"/api/v1/workflows/{workflow_id}")
    
    async def activate_workflow(self, workflow_id: str) -> None:
        """
        Activate a workflow in n8n.
        
        Args:
            workflow_id: n8n workflow ID
        """
        await self._request("POST", f"/api/v1/workflows/{workflow_id}/activate")
    
    async def deactivate_workflow(self, workflow_id: str) -> None:
        """
        Deactivate a workflow in n8n.
        
        Args:
            workflow_id: n8n workflow ID
        """
        await self._request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")
    
    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get execution details from n8n.
        
        Args:
            execution_id: n8n execution ID
            
        Returns:
            Execution details
        """
        return await self._request("GET", f"/api/v1/executions/{execution_id}")
    
    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List executions from n8n.
        
        Args:
            workflow_id: Optional workflow ID filter
            status: Optional status filter
            limit: Maximum number of results
            
        Returns:
            List of executions
        """
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        
        result = await self._request("GET", "/api/v1/executions", params=params)
        return result.get("data", [])
    
    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Trigger a workflow execution in n8n.
        
        Args:
            workflow_id: n8n workflow ID
            data: Input data for the workflow
            credentials: Credential overrides for this execution
            
        Returns:
            n8n execution ID
        """
        payload = {"data": data or {}, "mode": "manual"}
        if credentials:
            payload["credentials"] = credentials
        
        result = await self._request("POST", f"/api/v1/workflows/{workflow_id}/execute", json=payload)
        return result["executionId"]
    
    async def health_check(self) -> bool:
        """
        Check if n8n is healthy.
        
        Returns:
            True if healthy
        """
        # Initialize client if not already initialized
        needs_close = False
        if not self.client:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=60.0
            )
            needs_close = True
        
        try:
            response = await self.client.get("/healthz")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"n8n health check failed: {e}")
            return False
        finally:
            if needs_close and self.client:
                await self.client.aclose()
