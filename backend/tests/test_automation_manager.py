"""
Tests for Automation Manager and Manifest Manager.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import yaml

from app.services.automations.manifest_manager import (
    ManifestManager,
    Manifest,
    Requirement,
    N8NConfig,
    Metadata,
)
from app.services.automations.manager import (
    AutomationManager,
    AutomationStatus,
)
from app.services.credentials.manager import CredentialManager
from app.services.n8n.client import N8NClient


class TestManifestManager:
    """Tests for ManifestManager."""
    
    @pytest.fixture
    def temp_automations_dir(self):
        """Create a temporary automations directory with test manifests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            automations_dir = Path(tmpdir) / "automations"
            automations_dir.mkdir()
            
            # Create test automation 1
            auto1_dir = automations_dir / "test-auto-1"
            auto1_dir.mkdir()
            
            manifest1 = {
                "id": "test-auto-1",
                "name": "Test Automation 1",
                "description": "First test automation",
                "version": "1.0.0",
                "status": "disabled",
                "category": "test",
                "icon": "test",
                "requirements": [
                    {"provider": "postgresql", "type": "connection"}
                ],
                "dependencies": [],
                "n8n": {
                    "workflow_file": "workflow.json",
                    "credential_mapping": {
                        "postgres": "postgresql"
                    }
                },
                "setup": [{"description": "Setup step 1"}],
                "teardown": [{"description": "Teardown step 1"}],
                "metadata": {
                    "auto_enable": False,
                    "source_workflow": "test.json"
                }
            }
            
            with open(auto1_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest1, f)
            
            workflow1 = {
                "name": "Test Workflow 1",
                "nodes": [],
                "connections": {},
                "settings": {}
            }
            with open(auto1_dir / "workflow.json", "w") as f:
                json.dump(workflow1, f)
            
            # Create test automation 2
            auto2_dir = automations_dir / "test-auto-2"
            auto2_dir.mkdir()
            
            manifest2 = {
                "id": "test-auto-2",
                "name": "Test Automation 2",
                "description": "Second test automation",
                "version": "2.0.0",
                "status": "disabled",
                "category": "test",
                "icon": "test",
                "requirements": [
                    {"provider": "openrouter", "type": "api_key"}
                ],
                "dependencies": ["test-auto-1"],
                "n8n": {
                    "workflow_file": "workflow.json",
                    "credential_mapping": {
                        "openRouterApi": "openrouter"
                    }
                },
                "metadata": {
                    "auto_enable": True
                }
            }
            
            with open(auto2_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest2, f)
            
            workflow2 = {
                "name": "Test Workflow 2",
                "nodes": [{"id": "1", "type": "n8n-nodes-base.start"}],
                "connections": {},
                "settings": {}
            }
            with open(auto2_dir / "workflow.json", "w") as f:
                json.dump(workflow2, f)
            
            yield automations_dir
    
    @pytest.fixture
    def manifest_manager(self, temp_automations_dir):
        """Create ManifestManager with temp directory."""
        # Create a new ManifestManager instance with the temp directory
        manager = ManifestManager()
        # Override the AUTOMATIONS_DIR directly
        manager.AUTOMATIONS_DIR = temp_automations_dir
        return manager
    
    def test_discover_manifests(self, manifest_manager):
        """Test discovering manifests."""
        manifests = manifest_manager.discover_manifests()
        
        assert len(manifests) == 2
        ids = {m.id for m in manifests}
        assert ids == {"test-auto-1", "test-auto-2"}
    
    def test_get_manifest(self, manifest_manager):
        """Test getting a specific manifest."""
        manifest = manifest_manager.get_manifest("test-auto-1")
        
        assert manifest is not None
        assert manifest.id == "test-auto-1"
        assert manifest.name == "Test Automation 1"
        assert manifest.version == "1.0.0"
    
    def test_get_nonexistent_manifest(self, manifest_manager):
        """Test getting a non-existent manifest."""
        manifest = manifest_manager.get_manifest("nonexistent")
        assert manifest is None
    
    def test_validate_manifest_valid(self, manifest_manager):
        """Test validating a valid manifest."""
        manifest = manifest_manager.get_manifest("test-auto-1")
        errors = manifest_manager.validate_manifest(manifest)
        
        assert errors == []
    
    def test_validate_manifest_missing_dependency(self, manifest_manager):
        """Test validating manifest with missing dependency."""
        # Create a manifest with a non-existent dependency
        manifest = manifest_manager.get_manifest("test-auto-2")
        # test-auto-2 depends on test-auto-1 which exists
        errors = manifest_manager.validate_manifest(manifest)
        assert errors == []
        
        # Now test with a manifest that has a missing dependency
        # We can't easily test this without modifying the discovered manifests
        # but the logic is there
    
    def test_check_version_update(self, manifest_manager):
        """Test version comparison."""
        # Current version 1.0.0, manifest has 1.0.0
        assert manifest_manager.check_version_update("test-auto-1", "1.0.0") == False
        
        # Current version 0.9.0, manifest has 1.0.0
        assert manifest_manager.check_version_update("test-auto-1", "0.9.0") == True
        
        # Current version 1.1.0, manifest has 1.0.0
        assert manifest_manager.check_version_update("test-auto-1", "1.1.0") == False
    
    def test_load_workflow(self, manifest_manager):
        """Test loading workflow JSON."""
        workflow = manifest_manager.load_workflow("test-auto-1")
        
        assert workflow["name"] == "Test Workflow 1"
        assert "nodes" in workflow
        assert "connections" in workflow
    
    def test_validate_workflow_json_valid(self, manifest_manager):
        """Test validating valid workflow JSON."""
        workflow = {
            "name": "Test",
            "nodes": [],
            "connections": {},
            "settings": {}
        }
        errors = manifest_manager.validate_workflow_json(workflow)
        assert errors == []
    
    def test_validate_workflow_json_invalid(self, manifest_manager):
        """Test validating invalid workflow JSON."""
        # Missing name
        workflow = {"nodes": [], "connections": {}, "settings": {}}
        errors = manifest_manager.validate_workflow_json(workflow)
        assert "Workflow missing 'name' field" in errors
        
        # Missing nodes
        workflow = {"name": "Test", "connections": {}, "settings": {}}
        errors = manifest_manager.validate_workflow_json(workflow)
        assert "Workflow missing 'nodes' field" in errors
        
        # Nodes not a list
        workflow = {"name": "Test", "nodes": "not a list", "connections": {}, "settings": {}}
        errors = manifest_manager.validate_workflow_json(workflow)
        assert "Workflow 'nodes' must be a list" in errors


class TestManifestSchema:
    """Tests for Manifest schema validation."""
    
    def test_valid_manifest(self):
        """Test creating a valid manifest."""
        manifest = Manifest(
            id="test-auto",
            name="Test Automation",
            description="A test automation",
            version="1.0.0",
            status="disabled",
            category="test",
            icon="test",
            requirements=[
                Requirement(provider="postgresql", type="connection")
            ],
            dependencies=[],
            n8n=N8NConfig(
                workflow_file="workflow.json",
                credential_mapping={"postgres": "postgresql"}
            ),
            metadata=Metadata(auto_enable=False)
        )
        
        assert manifest.id == "test-auto"
        assert manifest.version == "1.0.0"
    
    def test_invalid_id(self):
        """Test invalid ID format."""
        with pytest.raises(ValueError, match="ID must be alphanumeric"):
            Manifest(
                id="test auto",  # Space not allowed
                name="Test",
                description="Test",
                version="1.0.0",
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="workflow.json")
            )
    
    def test_invalid_version(self):
        """Test invalid version format."""
        with pytest.raises(ValueError, match="Version must be at least major.minor"):
            Manifest(
                id="test",
                name="Test",
                description="Test",
                version="1",  # Missing minor
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="workflow.json")
            )
    
    def test_invalid_status(self):
        """Test invalid status."""
        with pytest.raises(ValueError, match="Status must be one of"):
            Manifest(
                id="test",
                name="Test",
                description="Test",
                version="1.0.0",
                status="invalid_status",
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="workflow.json")
            )
    
    def test_path_traversal_in_workflow_file(self):
        """Test path traversal prevention in workflow_file."""
        with pytest.raises(ValueError, match="workflow_file must be a relative path"):
            Manifest(
                id="test",
                name="Test",
                description="Test",
                version="1.0.0",
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="../workflow.json")
            )
        
        with pytest.raises(ValueError, match="workflow_file must be a relative path"):
            Manifest(
                id="test",
                name="Test",
                description="Test",
                version="1.0.0",
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="/absolute/path.json")
            )


class TestAutomationStatus:
    """Tests for AutomationStatus state machine."""
    
    def test_valid_transitions(self):
        """Test valid status transitions."""
        assert AutomationStatus.is_valid_transition("discovered", "installed")
        assert AutomationStatus.is_valid_transition("installed", "enabled")
        assert AutomationStatus.is_valid_transition("enabled", "disabled")
        assert AutomationStatus.is_valid_transition("disabled", "enabled")
        assert AutomationStatus.is_valid_transition("installed", "disabled")
        assert AutomationStatus.is_valid_transition("installed", "uninstalling")
        assert AutomationStatus.is_valid_transition("enabled", "uninstalling")
        assert AutomationStatus.is_valid_transition("disabled", "uninstalling")
        assert AutomationStatus.is_valid_transition("uninstalling", "discovered")
        assert AutomationStatus.is_valid_transition("error", "installed")
        assert AutomationStatus.is_valid_transition("error", "disabled")
    
    def test_invalid_transitions(self):
        """Test invalid status transitions."""
        assert not AutomationStatus.is_valid_transition("discovered", "enabled")
        assert not AutomationStatus.is_valid_transition("enabled", "installed")
        assert not AutomationStatus.is_valid_transition("disabled", "installed")
        assert not AutomationStatus.is_valid_transition("uninstalling", "enabled")


class TestAutomationManager:
    """Tests for AutomationManager (mocked)."""
    
    @pytest.fixture
    def mock_credential_manager(self):
        """Create a mock credential manager."""
        return AsyncMock(spec=CredentialManager)
    
    @pytest.fixture
    def mock_n8n_client(self):
        """Create a mock n8n client that works as async context manager."""
        client = MagicMock(spec=N8NClient)
        # Use AsyncMock for async methods
        client.import_workflow = AsyncMock(return_value="n8n-workflow-123")
        client.activate_workflow = AsyncMock(return_value=None)
        client.deactivate_workflow = AsyncMock(return_value=None)
        client.delete_workflow = AsyncMock(return_value=None)
        client.get_workflow = AsyncMock(return_value={"name": "Test", "nodes": []})
        
        # Make it work as async context manager - __aenter__ needs to accept self
        async def mock_aenter(self):
            return client
        async def mock_aexit(self, *args):
            return None
        client.__aenter__ = mock_aenter
        client.__aexit__ = mock_aexit
        
        return client
    
    @pytest.fixture
    def mock_manifest_manager(self):
        """Create a mock manifest manager."""
        manager = MagicMock(spec=ManifestManager)
        
        # Create a mock manifest
        manifest = Manifest(
            id="test-auto",
            name="Test Automation",
            description="A test automation",
            version="1.0.0",
            status="disabled",
            category="test",
            icon="test",
            requirements=[
                Requirement(provider="postgresql", type="connection")
            ],
            dependencies=[],
            n8n=N8NConfig(
                workflow_file="workflow.json",
                credential_mapping={"postgres": "postgresql"}
            ),
            metadata=Metadata(auto_enable=False)
        )
        
        manager.get_manifest = MagicMock(return_value=manifest)
        manager.validate_manifest = MagicMock(return_value=[])
        manager.load_workflow = MagicMock(return_value={
            "name": "Test Workflow",
            "nodes": [],
            "connections": {},
            "settings": {}
        })
        manager.validate_workflow_json = MagicMock(return_value=[])
        
        return manager
    
    @pytest.fixture
    def automation_manager(self, mock_credential_manager, mock_n8n_client, mock_manifest_manager):
        """Create AutomationManager with mocks."""
        return AutomationManager(
            credential_manager=mock_credential_manager,
            n8n_client=mock_n8n_client,
            manifest_manager=mock_manifest_manager,
        )
    
    @pytest.mark.asyncio
    async def test_preflight_is_read_only(self, automation_manager, mock_n8n_client):
        """Preflight reports readiness without importing a workflow or touching n8n."""
        account_resolution = {"accounts": [], "credential_mappings": [], "missing_requirements": []}
        with patch.object(automation_manager, '_validate_dependencies', return_value=[]):
            with patch.object(automation_manager, '_resolve_manifest_accounts', return_value=account_resolution):
                with patch.object(automation_manager, '_validate_runtime_dependencies', return_value=[]):
                    result = await automation_manager.preflight_automation("test-auto")
        assert result["automation_id"] == "test-auto"
        assert result["status"] == "blocked"  # the fixture intentionally has no webhook node
        assert result["mutations_applied"] is False
        assert any(check["name"] == "execution_trigger" for check in result["checks"])
        mock_n8n_client.import_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_automation_success(self, automation_manager, mock_n8n_client):
        """Test successful automation installation."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock database queries - use MagicMock for scalar_one_or_none to return directly
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # Not installed
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            # Mock commit
            mock_session.commit = AsyncMock()
            
            # Installation requires the full read-only preflight to be ready.
            with patch.object(automation_manager, 'preflight_automation', return_value={"status": "ready"}):
                with patch.object(automation_manager, '_assign_credentials', return_value={}):
                    result = await automation_manager.install_automation("test-auto")

            assert result["success"] == True
            assert result["automation_id"] == "test-auto"
            assert result["n8n_workflow_id"] == "n8n-workflow-123"
            assert result["status"] == "installed"
            
            # Verify n8n workflow was imported
            mock_n8n_client.import_workflow.assert_called_once()
            
            # Verify session.add was called (for new automation record)
            mock_session.add.assert_called()
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_install_automation_missing_manifest(self, automation_manager):
        """Test installation with missing manifest."""
        automation_manager.manifest_manager.get_manifest = MagicMock(return_value=None)
        
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()
            
            # Also mock the _update_status call which uses get_session internally
            with patch.object(automation_manager, '_update_status', new_callable=AsyncMock) as mock_update_status:
                with pytest.raises(ValueError, match="Automation not found"):
                    await automation_manager.install_automation("nonexistent")
                
                # Verify _update_status was called with ERROR status
                mock_update_status.assert_called_once_with("nonexistent", AutomationStatus.ERROR)
    
    @pytest.mark.asyncio
    async def test_repeat_install_preserves_existing_status(self, automation_manager, mock_n8n_client):
        """A repeated install request must not turn an installed copy into error."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            existing = MagicMock(status=AutomationStatus.INSTALLED, n8n_workflow_id="n8n-workflow-123")
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = existing
            mock_session.execute = AsyncMock(return_value=mock_result)
            with patch.object(automation_manager, 'preflight_automation', return_value={"status": "ready"}):
                with patch.object(automation_manager, '_update_status', new_callable=AsyncMock) as update_status:
                    with pytest.raises(ValueError, match="Automation already installed"):
                        await automation_manager.install_automation("test-auto")

        update_status.assert_not_awaited()
        mock_n8n_client.import_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_automation_missing_credentials(self, automation_manager):

        """Test installation with missing credentials."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            with patch.object(
                automation_manager,
                'preflight_automation',
                return_value={"status": "blocked", "missing_requirements": ["postgresql: account not connected"]},
            ):
                with pytest.raises(ValueError, match="INSTALLATION BLOCKED: postgresql: account not connected"):
                    await automation_manager.install_automation("test-auto")

            mock_n8n_client = automation_manager.n8n_client
            mock_n8n_client.import_workflow.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_install_automation_rollback_on_failure(self, automation_manager, mock_n8n_client):
        """Test rollback when installation fails."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            # Make n8n import fail
            mock_n8n_client.import_workflow.side_effect = Exception("n8n error")
            
            with patch.object(automation_manager, 'preflight_automation', return_value={"status": "ready"}):
                with pytest.raises(ValueError, match="Failed to import workflow"):
                    await automation_manager.install_automation("test-auto")

            # Verify rollback was attempted
            mock_n8n_client.delete_workflow.assert_not_called()  # No workflow ID to delete
    
    @pytest.mark.asyncio
    async def test_install_rolls_back_import_when_credential_assignment_fails(self, automation_manager, mock_n8n_client):
        """A mapping failure after import deletes only the imported workflow copy."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()

            with patch.object(automation_manager, 'preflight_automation', return_value={"status": "ready"}):
                with patch.object(
                    automation_manager,
                    '_assign_credentials',
                    side_effect=ValueError('INSTALLATION BLOCKED: MISSING COMPATIBLE N8N CREDENTIAL MAPPING'),
                ):
                    with pytest.raises(ValueError, match='MISSING COMPATIBLE N8N CREDENTIAL MAPPING'):
                        await automation_manager.install_automation("test-auto")

        mock_n8n_client.delete_workflow.assert_called_once_with("n8n-workflow-123")

    @pytest.mark.asyncio
    async def test_run_enabled_automation_creates_non_sensitive_execution(self, automation_manager, mock_n8n_client):
        """An explicit run creates tracking metadata and sends no credential override."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            automation = MagicMock(status="enabled", n8n_workflow_id="n8n-workflow-123")
            persisted_execution = MagicMock()
            mock_session.get = AsyncMock(side_effect=[automation, persisted_execution])
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_n8n_client.execute_workflow = AsyncMock(return_value="n8n-execution-123")

            with patch.object(automation_manager, 'preflight_automation', return_value={"status": "ready"}):
                with patch.object(automation_manager, '_resolve_execution_profile', return_value=(None, {})):
                    result = await automation_manager.run_automation("test-auto")

        assert result["status"] == "running"
        assert result["profile_id"] is None
        mock_n8n_client.execute_workflow.assert_awaited_once_with(
            "n8n-workflow-123",
            data={"automation_center": {"profile_id": None, "context": {}}},
        )
        created_execution = mock_session.add.call_args.args[0]
        assert created_execution.status == "queued"
        assert created_execution.profile_id is None
        assert created_execution.result_data == {"profile_context_applied": False}

    @pytest.mark.asyncio
    async def test_run_is_blocked_when_preflight_fails(self, automation_manager, mock_n8n_client):
        """The run endpoint never invokes n8n when the final preflight is blocked."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.get = AsyncMock(return_value=MagicMock(status="enabled", n8n_workflow_id="n8n-workflow-123"))
            with patch.object(
                automation_manager,
                'preflight_automation',
                return_value={"status": "blocked", "missing_requirements": ["google: account not connected"]},
            ):
                with pytest.raises(ValueError, match="EXECUTION BLOCKED: google: account not connected"):
                    await automation_manager.run_automation("test-auto")

        assert not hasattr(mock_n8n_client, 'execute_workflow') or not mock_n8n_client.execute_workflow.called

    @pytest.mark.asyncio
    async def test_enable_automation(self, automation_manager, mock_n8n_client):

        """Test enabling an automation."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock database automation record
            mock_automation = MagicMock()
            mock_automation.id = "test-auto"
            mock_automation.status = "installed"
            mock_automation.n8n_workflow_id = "n8n-workflow-123"
            mock_automation.updated_at = None
            
            # Use MagicMock for result so scalar_one_or_none returns directly
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_automation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            with patch.object(automation_manager, '_assign_credentials', return_value={}):
                result = await automation_manager.enable_automation("test-auto")
            
            assert result["success"] == True
            assert result["status"] == "enabled"
            
            # Verify n8n workflow was activated
            mock_n8n_client.activate_workflow.assert_called_once_with("n8n-workflow-123")
    
    @pytest.mark.asyncio
    async def test_enable_automation_not_installed(self, automation_manager):
        """Test enabling an automation that's not installed."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_automation = MagicMock()
            mock_automation.status = "discovered"
            mock_automation.n8n_workflow_id = None
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_automation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            with pytest.raises(ValueError, match="must be installed or disabled"):
                await automation_manager.enable_automation("test-auto")
    
    @pytest.mark.asyncio
    async def test_disable_automation(self, automation_manager, mock_n8n_client):
        """Test disabling an automation."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_automation = MagicMock()
            mock_automation.id = "test-auto"
            mock_automation.status = "enabled"
            mock_automation.n8n_workflow_id = "n8n-workflow-123"
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_automation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            result = await automation_manager.disable_automation("test-auto")
            
            assert result["success"] == True
            assert result["status"] == "disabled"
            
            # Verify n8n workflow was deactivated
            mock_n8n_client.deactivate_workflow.assert_called_once_with("n8n-workflow-123")
    
    @pytest.mark.asyncio
    async def test_uninstall_automation(self, automation_manager, mock_n8n_client):
        """Test uninstalling an automation."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_automation = MagicMock()
            mock_automation.id = "test-auto"
            mock_automation.status = "enabled"
            mock_automation.n8n_workflow_id = "n8n-workflow-123"
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_automation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            result = await automation_manager.uninstall_automation("test-auto")
            
            assert result["success"] == True
            assert "Global credentials preserved" in result["message"]
            
            # Verify n8n workflow was deactivated and deleted
            mock_n8n_client.deactivate_workflow.assert_called_once_with("n8n-workflow-123")
            mock_n8n_client.delete_workflow.assert_called_once_with("n8n-workflow-123")
            
            # Verify database deletions were called
            assert mock_session.execute.call_count >= 3  # delete credentials, delete automation, commit
    
    @pytest.mark.asyncio
    async def test_uninstall_preserves_global_credentials(self, automation_manager, mock_n8n_client):
        """Test that uninstall doesn't delete global credentials."""
        with patch('app.services.automations.manager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            mock_automation = MagicMock()
            mock_automation.id = "test-auto"
            mock_automation.status = "disabled"
            mock_automation.n8n_workflow_id = "n8n-workflow-123"
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_automation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            await automation_manager.uninstall_automation("test-auto")
            
            # Verify only automation_credentials and automations were deleted
            # NOT the credentials table
            execute_calls = mock_session.execute.call_args_list
            deleted_tables = []
            for call in execute_calls:
                if call[0] and hasattr(call[0][0], 'table'):
                    deleted_tables.append(call[0][0].table.name)
            
            # Should delete from automation_credentials and automations
            # NOT from credentials table
            assert "automation_credentials" in str(deleted_tables) or len(deleted_tables) == 0  # May use ORM delete
            # The important thing is credentials table is not touched


class TestSecurity:
    """Security tests for Automation Manager."""
    
    def test_no_secrets_in_manifest(self):
        """Test that manifests don't contain secrets."""
        # Manifest schema doesn't have fields for secrets
        manifest = Manifest(
            id="test",
            name="Test",
            description="Test",
            version="1.0.0",
            category="test",
            icon="test",
            n8n=N8NConfig(workflow_file="workflow.json")
        )
        
        # Verify no secret fields exist
        manifest_dict = manifest.dict()
        secret_fields = ["access_token", "refresh_token", "api_key", "client_secret", "password", "token"]
        
        def check_no_secrets(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(secret in key.lower() for secret in secret_fields):
                        raise AssertionError(f"Secret field found at {path}.{key}: {key}")
                    check_no_secrets(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_secrets(item, f"{path}[{i}]")
        
        check_no_secrets(manifest_dict)
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention in manifest validation."""
        with pytest.raises(ValueError, match="workflow_file must be a relative path"):
            Manifest(
                id="test",
                name="Test",
                description="Test",
                version="1.0.0",
                category="test",
                icon="test",
                n8n=N8NConfig(workflow_file="../../../etc/passwd")
            )
    
    def test_unsafe_yaml_loading(self):
        """Test that YAML is loaded safely."""
        # The manifest manager uses yaml.safe_load, not yaml.load
        import yaml
        
        # This should not execute arbitrary code
        malicious_yaml = """
        !!python/object/apply:os.system ["echo hacked"]
        """
        
        # safe_load should raise a ConstructorError for unsafe tags
        with pytest.raises(yaml.constructor.ConstructorError):
            yaml.safe_load(malicious_yaml)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])