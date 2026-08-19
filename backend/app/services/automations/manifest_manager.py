"""
Manifest Manager for Automation Center.
Handles discovery, loading, and validation of automation manifests.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field, validator

from ...core.config import settings

logger = logging.getLogger(__name__)

# These identifiers describe runtime infrastructure or an OAuth capability in
# current manifests. They are validated by service health and credential checks,
# not by searching for a second Automation Center automation record.
EXTERNAL_RUNTIME_DEPENDENCIES = {"postgresql", "playwright", "google-oauth2"}


class Requirement(BaseModel):
    """Requirement specification for an automation."""
    provider: str
    type: str  # oauth2, api_key, token, connection
    scopes: List[str] = Field(default_factory=list)


class N8NConfig(BaseModel):
    """n8n configuration for an automation."""
    workflow_file: str
    credential_mapping: Dict[str, str] = Field(default_factory=dict)


class SetupStep(BaseModel):
    """Setup step for an automation."""
    description: str


class TeardownStep(BaseModel):
    """Teardown step for an automation."""
    description: str


class Metadata(BaseModel):
    """Additional metadata for an automation."""
    auto_enable: bool = False
    source_workflow: Optional[str] = None
    test_only: bool = False
    env_vars_required: List[str] = Field(default_factory=list)
    actual_ai_provider: Optional[str] = None
    actual_notification: Optional[str] = None


class Manifest(BaseModel):
    """Automation manifest schema."""
    id: str
    name: str
    description: str
    version: str
    status: str = "disabled"
    category: str
    icon: str
    
    requirements: List[Requirement] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    
    n8n: N8NConfig
    
    setup: List[SetupStep] = Field(default_factory=list)
    teardown: List[TeardownStep] = Field(default_factory=list)
    
    metadata: Metadata = Field(default_factory=Metadata)
    
    @validator('id')
    def validate_id(cls, v):
        """Validate automation ID format."""
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('ID must be alphanumeric with hyphens/underscores only')
        return v
    
    @validator('version')
    def validate_version(cls, v):
        """Validate version format (semver-like)."""
        parts = v.split('.')
        if len(parts) < 2:
            raise ValueError('Version must be at least major.minor')
        for part in parts:
            if not part.isdigit():
                raise ValueError('Version parts must be numeric')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status value."""
        valid_statuses = ['discovered', 'installed', 'enabled', 'disabled', 'error', 'uninstalling']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v
    
    @validator('n8n')
    def validate_n8n_config(cls, v):
        """Validate n8n configuration."""
        if not v.workflow_file:
            raise ValueError('n8n.workflow_file is required')
        # Prevent path traversal
        if '..' in v.workflow_file or v.workflow_file.startswith('/'):
            raise ValueError('workflow_file must be a relative path without traversal')
        return v


class ManifestManager:
    """
    Manages automation manifests.
    
    Responsibilities:
    - Discover manifests in automations/ directory
    - Load and parse YAML manifests
    - Validate manifest schema
    - Check for unique IDs
    - Check version compatibility
    - Verify workflow file exists
    - Validate provider requirements
    - Detect corrupted manifests
    - Detect missing dependencies
    """
    
    # Directory where automations are stored
    AUTOMATIONS_DIR = Path(settings.APP_DIR) / "automations" if hasattr(settings, "APP_DIR") else Path(__file__).parent.parent.parent / "automations"
    
    def __init__(self):
        self._manifests: Dict[str, Manifest] = {}
        self._discovered = False
    
    def discover_manifests(self) -> List[Manifest]:
        """
        Discover all manifests in the automations directory.
        
        Returns:
            List of validated Manifest objects
        """
        manifests = []
        seen_ids: Set[str] = set()
        
        if not self.AUTOMATIONS_DIR.exists():
            logger.warning(f"Automations directory not found: {self.AUTOMATIONS_DIR}")
            return manifests
        
        for automation_dir in self.AUTOMATIONS_DIR.iterdir():
            if not automation_dir.is_dir():
                continue
            
            manifest_path = automation_dir / "manifest.yaml"
            if not manifest_path.exists():
                logger.warning(f"No manifest.yaml found in {automation_dir.name}")
                continue
            
            try:
                with open(manifest_path, 'r') as f:
                    raw_manifest = yaml.safe_load(f)
                
                if not raw_manifest:
                    logger.error(f"Empty manifest in {automation_dir.name}")
                    continue
                
                # Validate and parse manifest
                manifest = Manifest(**raw_manifest)
                
                # Check for duplicate IDs
                if manifest.id in seen_ids:
                    logger.error(f"Duplicate automation ID: {manifest.id}")
                    continue
                seen_ids.add(manifest.id)
                
                # Verify workflow file exists
                workflow_path = automation_dir / manifest.n8n.workflow_file
                if not workflow_path.exists():
                    logger.error(f"Workflow file not found: {workflow_path}")
                    continue
                
                # Validate workflow JSON
                try:
                    with open(workflow_path, 'r') as f:
                        workflow_data = json.load(f)
                    if not isinstance(workflow_data, dict) or 'nodes' not in workflow_data:
                        logger.error(f"Invalid workflow JSON in {workflow_path}")
                        continue
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in workflow file {workflow_path}: {e}")
                    continue
                
                manifests.append(manifest)
                logger.info(f"Discovered automation: {manifest.id} v{manifest.version}")
                
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in {manifest_path}: {e}")
            except Exception as e:
                logger.error(f"Failed to load manifest {automation_dir.name}: {e}")
        
        self._manifests = {m.id: m for m in manifests}
        self._discovered = True
        return manifests
    
    def get_manifest(self, automation_id: str) -> Optional[Manifest]:
        """Get a manifest by ID."""
        if not self._discovered:
            self.discover_manifests()
        return self._manifests.get(automation_id)
    
    def list_manifests(self) -> List[Manifest]:
        """List all discovered manifests."""
        if not self._discovered:
            self.discover_manifests()
        return list(self._manifests.values())
    
    def validate_manifest(self, manifest: Manifest) -> List[str]:
        """
        Validate a manifest and return list of errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check ID uniqueness
        if manifest.id in self._manifests and self._manifests[manifest.id] != manifest:
            errors.append(f"Duplicate automation ID: {manifest.id}")
        
        # Check workflow file
        workflow_path = self.AUTOMATIONS_DIR / manifest.id / manifest.n8n.workflow_file
        if not workflow_path.exists():
            errors.append(f"Workflow file not found: {manifest.n8n.workflow_file}")
        
        # Check only automation-to-automation dependencies. Runtime services
        # and OAuth capabilities are represented in manifests for operational
        # documentation and are verified elsewhere in the installation flow.
        for dep in manifest.dependencies:
            if dep in EXTERNAL_RUNTIME_DEPENDENCIES:
                continue
            if dep not in self._manifests:
                errors.append(f"Missing dependency: {dep}")
        
        return errors
    
    def check_version_update(self, automation_id: str, current_version: str) -> bool:
        """
        Check if a newer version is available.
        
        Args:
            automation_id: Automation ID
            current_version: Currently installed version
            
        Returns:
            True if update available
        """
        manifest = self.get_manifest(automation_id)
        if not manifest:
            return False
        
        return self._compare_versions(manifest.version, current_version) > 0
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        parts1 = [int(p) for p in v1.split('.')]
        parts2 = [int(p) for p in v2.split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        
        return 0
    
    def get_automation_dir(self, automation_id: str) -> Path:
        """Get the automation directory path."""
        return self.AUTOMATIONS_DIR / automation_id
    
    def load_workflow(self, automation_id: str) -> Dict[str, Any]:
        """Load workflow JSON for an automation."""
        manifest = self.get_manifest(automation_id)
        if not manifest:
            raise ValueError(f"Automation not found: {automation_id}")
        
        workflow_path = self.AUTOMATIONS_DIR / automation_id / manifest.n8n.workflow_file
        with open(workflow_path, 'r') as f:
            return json.load(f)
    
    def validate_workflow_json(self, workflow_data: Dict[str, Any]) -> List[str]:
        """
        Validate workflow JSON structure.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not isinstance(workflow_data, dict):
            errors.append("Workflow must be a JSON object")
            return errors
        
        if 'name' not in workflow_data:
            errors.append("Workflow missing 'name' field")
        
        if 'nodes' not in workflow_data:
            errors.append("Workflow missing 'nodes' field")
        elif not isinstance(workflow_data['nodes'], list):
            errors.append("Workflow 'nodes' must be a list")
        
        if 'connections' not in workflow_data:
            errors.append("Workflow missing 'connections' field")
        elif not isinstance(workflow_data['connections'], dict):
            errors.append("Workflow 'connections' must be an object")
        
        if 'settings' not in workflow_data:
            errors.append("Workflow missing 'settings' field")
        
        return errors