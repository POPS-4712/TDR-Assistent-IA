"""
Automation Manager for Automation Center.
Handles automation installation, configuration, and lifecycle management.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.security import log_sanitizer

from ...database.db import get_session
from ...database.models import (
    Automation as AutomationModel,
    AutomationCredential as AutomationCredentialModel,
    Credential as CredentialModel,
    Execution,
    Profile,
)

from ..credentials.manager import CredentialManager
from ..profiles.manager import ProfileManager

from ..n8n.client import N8NClient
from .account_resolver import AccountResolver
from .manifest_manager import ManifestManager, Manifest

logger = logging.getLogger(__name__)


class AutomationStatus:
    """Valid automation statuses."""

    DISCOVERED = "discovered"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    BLOCKED = "blocked"
    UNINSTALLING = "uninstalling"

    ALL = [DISCOVERED, INSTALLING, INSTALLED, ENABLED, DISABLED, BLOCKED, ERROR, UNINSTALLING]

    # Valid transitions
    TRANSITIONS = {
        DISCOVERED: [INSTALLING, INSTALLED, BLOCKED, ERROR],
        INSTALLING: [INSTALLED, BLOCKED, ERROR],
        INSTALLED: [ENABLED, DISABLED, UNINSTALLING, ERROR],
        ENABLED: [DISABLED, UNINSTALLING, ERROR],
        DISABLED: [ENABLED, UNINSTALLING, ERROR],
        UNINSTALLING: [DISCOVERED],  # After uninstall, can be rediscovered
        BLOCKED: [INSTALLING, INSTALLED, ERROR],
        ERROR: [INSTALLING, INSTALLED, DISABLED, BLOCKED],  # Can retry from error
    }

    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if a status transition is valid."""
        return to_status in cls.TRANSITIONS.get(from_status, [])


class AutomationManager:
    """
    Manages automation workflows and their lifecycle.
    
    Architecture:
    Frontend -> FastAPI -> AutomationManager
        ├── ManifestManager (discovery, validation)
        ├── CredentialManager (credential mapping, assignment)
        ├── N8NClient (workflow import, activate, deactivate, delete)
        └── PostgreSQL (metadata, status, relationships)
    """
    
    # Directory where automations are stored
    AUTOMATIONS_DIR = Path(settings.APP_DIR) / "automations" if hasattr(settings, "APP_DIR") else Path(__file__).parent.parent.parent / "automations"
    
    def __init__(
        self,
        credential_manager: CredentialManager,
        n8n_client: N8NClient,
        manifest_manager: Optional[ManifestManager] = None,
        account_resolver: Optional[AccountResolver] = None,
    ):
        self.credential_manager = credential_manager
        self.n8n_client = n8n_client
        self.manifest_manager = manifest_manager or ManifestManager()
        self.account_resolver = account_resolver or AccountResolver()
        self._discovered = False

    # ============================================================
    # Discovery & Manifest Operations
    # ============================================================
    
    async def discover_automations(self) -> List[Dict[str, Any]]:
        """
        Discover all automations in the automations directory.
        Creates/updates metadata in PostgreSQL for new discoveries.
        
        Returns:
            List of automation definitions with status
        """
        manifests = self.manifest_manager.discover_manifests()
        results = []
        
        async with get_session() as session:
            for manifest in manifests:
                # Check if automation exists in database
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == manifest.id)
                )
                db_automation = result.scalar_one_or_none()
                
                if not db_automation:
                    # New discovery - create metadata
                    db_automation = AutomationModel(
                        id=manifest.id,
                        name=manifest.name,
                        description=manifest.description,
                        version=manifest.version,
                        status=AutomationStatus.DISCOVERED,
                        manifest_url=f"file://{self.AUTOMATIONS_DIR / manifest.id / 'manifest.yaml'}",
                        dependencies=manifest.dependencies,
                        n8n_workflow_id=None,
                    )
                    session.add(db_automation)
                    logger.info(f"Discovered new automation: {manifest.id} v{manifest.version}")
                else:
                    # Existing - check version
                    if db_automation.version != manifest.version:
                        logger.info(f"Version mismatch for {manifest.id}: DB={db_automation.version}, Manifest={manifest.version}")
                        # Don't auto-update - just log
                
                results.append({
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                    "version": manifest.version,
                    "status": db_automation.status,
                    "category": manifest.category,
                    "icon": manifest.icon,
                    "dependencies": manifest.dependencies,
                    "n8n_workflow_id": db_automation.n8n_workflow_id,
                    "update_available": db_automation.version != manifest.version,
                    "created_at": db_automation.created_at.isoformat() if db_automation.created_at else None,
                    "updated_at": db_automation.updated_at.isoformat() if db_automation.updated_at else None,
                })
            
            await session.commit()
        
        self._discovered = True
        return results
    
    async def get_automation(self, automation_id: str) -> Optional[Dict[str, Any]]:
        """Get an automation by ID from database."""
        async with get_session() as session:
            result = await session.execute(
                select(AutomationModel).where(AutomationModel.id == automation_id)
            )
            db_automation = result.scalar_one_or_none()
            
            if not db_automation:
                return None
            
            manifest = self.manifest_manager.get_manifest(automation_id)
            
            return {
                "id": db_automation.id,
                "name": db_automation.name,
                "description": db_automation.description,
                "version": db_automation.version,
                "status": db_automation.status,
                "manifest_url": db_automation.manifest_url,
                "dependencies": db_automation.dependencies,
                "n8n_workflow_id": db_automation.n8n_workflow_id,
                "created_at": db_automation.created_at.isoformat() if db_automation.created_at else None,
                "updated_at": db_automation.updated_at.isoformat() if db_automation.updated_at else None,
                "manifest": manifest.dict() if manifest else None,
            }
    
    async def list_automations(self) -> List[Dict[str, Any]]:
        """List all automations from database."""
        async with get_session() as session:
            result = await session.execute(
                select(AutomationModel).order_by(AutomationModel.created_at.desc())
            )
            automations = result.scalars().all()
            
            # Runtime state remains persisted in PostgreSQL, while non-operational
            # labels come directly from the local manifest. This keeps the UI
            # current without mutating metadata during automatic preflight.
            return [
                {
                    "id": a.id,
                    "name": (manifest.name if (manifest := self.manifest_manager.get_manifest(a.id)) else a.name),
                    "description": (manifest.description if manifest else a.description),
                    "version": (manifest.version if manifest else a.version),
                    "status": a.status,
                    "manifest_url": a.manifest_url,
                    "dependencies": (manifest.dependencies if manifest else a.dependencies),
                    "n8n_workflow_id": a.n8n_workflow_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                }
                for a in automations
            ]

        # ============================================================
    # Preflight & Installation Flow
    # ============================================================

    async def preflight_automation(self, automation_id: str) -> Dict[str, Any]:
        """Evaluate installation readiness without mutating n8n or database state."""
        manifest = self.manifest_manager.get_manifest(automation_id)
        if not manifest:
            raise ValueError(f"Automation not found: {automation_id}")

        checks: List[Dict[str, Any]] = []
        manifest_errors = self.manifest_manager.validate_manifest(manifest)
        checks.append({"name": "manifest", "status": "pass" if not manifest_errors else "blocked", "details": manifest_errors})

        workflow_errors: List[str] = []
        try:
            workflow = self.manifest_manager.load_workflow(automation_id)
            workflow_errors = self.manifest_manager.validate_workflow_json(workflow)
        except Exception as exc:
            workflow_errors = ["workflow could not be loaded"]
            logger.warning("Preflight could not load workflow %s: %s", automation_id, type(exc).__name__)
        checks.append({"name": "workflow", "status": "pass" if not workflow_errors else "blocked", "details": workflow_errors})

        dependencies = await self._validate_dependencies(manifest)
        checks.append({"name": "dependencies", "status": "pass" if not dependencies else "blocked", "details": dependencies})

        account_resolution = await self._resolve_manifest_accounts(manifest)
        requirements = account_resolution["missing_requirements"]
        checks.append({"name": "requirements", "status": "pass" if not requirements else "blocked", "details": account_resolution["accounts"]})

        mapping_failures = [item for item in account_resolution["credential_mappings"] if not item["compatible"]]
        checks.append({"name": "credential_mapping", "status": "pass" if not mapping_failures else "blocked", "details": account_resolution["credential_mappings"]})

        public_api_auth = await self.n8n_client.validate_public_api_authentication()
        public_api_status = public_api_auth.get("status", "unavailable")
        public_api_messages = {
            "not_configured": ["n8n Public API authentication not configured"],
            "rejected": ["n8n Public API authentication rejected or revoked"],
            "unavailable": ["n8n Public API authentication unavailable"],
        }
        public_api_blockers = public_api_messages.get(public_api_status, [])
        checks.append({
            "name": "n8n_public_api_auth",
            "status": "pass" if public_api_status == "valid" else "blocked",
            "details": [public_api_status],
        })

        runtime_dependencies = [*(await self._validate_runtime_dependencies(manifest)), *public_api_blockers]
        checks.append({"name": "runtime_dependencies", "status": "pass" if not runtime_dependencies else "blocked", "details": runtime_dependencies})

        checks.append({
            "name": "profile_compatibility",
            "status": "pass",
            "details": {"status": "optional", "message": "A profile may be selected at explicit run time; no profile data is required to install."},
        })

        webhook_nodes = []
        if not workflow_errors:
            webhook_nodes = [node.get("name", "") for node in workflow.get("nodes", []) if node.get("type") == "n8n-nodes-base.webhook"]
        checks.append({
            "name": "execution_trigger",
            "status": "pass" if webhook_nodes else "blocked",
            "details": webhook_nodes or ["profile-aware execution requires a declared webhook trigger in the copied workflow"],
        })

        blocked = [check for check in checks if check["status"] != "pass"]
        return {
            "automation_id": automation_id,
            "status": "ready" if not blocked else "blocked",
            "checks": checks,
            "requirements": [{"provider": req.provider, "scopes": req.scopes or [], "type": req.type} for req in manifest.requirements],
            "accounts": account_resolution["accounts"],
            "credential_mappings": account_resolution["credential_mappings"],
            "missing_requirements": list(dict.fromkeys([*requirements, *runtime_dependencies])),
            "runtime_dependencies": runtime_dependencies,
            "profile_compatibility": {"status": "optional"},
            "supports_profile_execution": bool(webhook_nodes),
            "mutations_applied": False,
        }
    
    async def preflight_all_automations(self) -> Dict[str, Any]:
        """Discover local manifests and evaluate every automation without side effects in n8n."""
        discovered = await self.discover_automations()
        results: List[Dict[str, Any]] = []
        for automation in discovered:
            automation_id = automation.get("id")
            if not automation_id:
                continue
            try:
                results.append(await self.preflight_automation(automation_id))
            except Exception as exc:
                logger.warning("Automatic preflight failed for automation %s: %s", automation_id, type(exc).__name__)
                results.append({
                    "automation_id": automation_id,
                    "status": "error",
                    "checks": [{"name": "preflight", "status": "error", "details": ["automatic preflight failed"]}],
                    "requirements": [],
                    "supports_profile_execution": False,
                    "mutations_applied": False,
                })
        return {"automations": results, "total": len(results), "mutations_applied": False}

    async def install_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Install an automation.
        
        Flow:
        1. Find manifest
        2. Validate manifest
        3. Check not already installed
        4. Check dependencies
        5. Check required credentials
        6. Validate workflow JSON
        7. Import workflow in n8n
        8. Get n8n workflow ID
        9. Assign credentials
        10. Create metadata in PostgreSQL
        11. Create automation_credentials
        12. Status = installed
        
        Args:
            automation_id: Automation ID to install
            
        Returns:
            Installation result with n8n workflow ID
        """
        start_time = time.time()
        operation = "install"
        
        try:
            # 1. Find manifest.
            manifest = self.manifest_manager.get_manifest(automation_id)
            if not manifest:
                raise ValueError(f"Automation not found: {automation_id}")

            # 2. Complete the full read-only preflight before any import or
            # metadata mutation. A blocked preflight is never bypassed.
            preflight = await self.preflight_automation(automation_id)
            if preflight["status"] != "ready":
                reasons = preflight.get("missing_requirements") or [
                    check.get("name", "preflight")
                    for check in preflight.get("checks", [])
                    if check.get("status") != "pass"
                ]
                raise ValueError("INSTALLATION BLOCKED: " + "; ".join(str(reason) for reason in reasons))

            # 3. Check not already installed.
            async with get_session() as session:
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == automation_id)
                )
                db_automation = result.scalar_one_or_none()
                if db_automation and db_automation.status in [
                    AutomationStatus.INSTALLED,
                    AutomationStatus.ENABLED,
                    AutomationStatus.DISABLED,
                ]:
                    raise ValueError(f"Automation already installed: {automation_id}")

            # A discovered record exists after automatic preflight. Record the
            # installation phase only after every read-only guard succeeded.
            await self._update_status(automation_id, AutomationStatus.INSTALLING)

            # 4. The preflight already validated dependencies, accounts, scopes,
            # n8n compatibility and runtime prerequisites without side effects.

            # 5. Validate workflow JSON again immediately before importing its copy.

            workflow_data = self.manifest_manager.load_workflow(automation_id)
            workflow_errors = self.manifest_manager.validate_workflow_json(workflow_data)
            if workflow_errors:
                raise ValueError(f"Workflow validation failed: {workflow_errors}")
            
            # 7. Import workflow in n8n
            n8n_workflow_id = None
            try:
                async with self.n8n_client as client:
                    n8n_workflow_id = await client.import_workflow(workflow_data)
                logger.info(f"Imported workflow to n8n: {n8n_workflow_id}")
            except Exception as e:
                logger.error(f"Failed to import workflow: {e}")
                raise ValueError(f"Failed to import workflow to n8n: {e}")
            
            # 8. Assign credentials
            credential_mapping = await self._assign_credentials(automation_id, manifest, n8n_workflow_id)
            
            # 9-11. Create metadata in PostgreSQL
            async with get_session() as session:
                # Update or create automation record
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == automation_id)
                )
                db_automation = result.scalar_one_or_none()
                
                if db_automation:
                    db_automation.status = AutomationStatus.INSTALLED
                    db_automation.n8n_workflow_id = n8n_workflow_id
                    db_automation.version = manifest.version
                    db_automation.dependencies = manifest.dependencies
                    db_automation.updated_at = datetime.utcnow()
                else:
                    db_automation = AutomationModel(
                        id=automation_id,
                        name=manifest.name,
                        description=manifest.description,
                        version=manifest.version,
                        status=AutomationStatus.INSTALLED,
                        manifest_url=f"file://{self.AUTOMATIONS_DIR / automation_id / 'manifest.yaml'}",
                        dependencies=manifest.dependencies,
                        n8n_workflow_id=n8n_workflow_id,
                    )
                    session.add(db_automation)
                
                # Persist relationships only for the exact accounts selected for
                # the imported workflow copy; provider-wide fallback is unsafe.
                for n8n_credential_id in set(credential_mapping.values()):
                    cred_result = await session.execute(
                        select(CredentialModel).where(
                            CredentialModel.n8n_credential_id == n8n_credential_id,
                            CredentialModel.status == "active",
                        )
                    )
                    credential = cred_result.scalar_one_or_none()
                    if credential:
                        existing = await session.execute(
                            select(AutomationCredentialModel).where(
                                AutomationCredentialModel.automation_id == automation_id,
                                AutomationCredentialModel.credential_id == credential.id,
                            )
                        )
                        if not existing.scalar_one_or_none():
                            session.add(AutomationCredentialModel(
                                automation_id=automation_id,
                                credential_id=credential.id,
                            ))

                await session.commit()
            
            # 12. Check auto_enable
            auto_enable = manifest.metadata.auto_enable if manifest.metadata else False
            if auto_enable:
                await self.enable_automation(automation_id)
            
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "success", duration)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "n8n_workflow_id": n8n_workflow_id,
                "status": AutomationStatus.INSTALLED,
                "credentials_mapped": list(credential_mapping.keys()),
                "auto_enabled": auto_enable,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "error", duration, str(e))
            
            # Rollback: try to clean up n8n workflow if created
            if 'n8n_workflow_id' in locals() and n8n_workflow_id:
                try:
                    async with self.n8n_client as client:
                        await client.delete_workflow(n8n_workflow_id)
                except Exception:
                    pass
            
            # A missing account/runtime is an actionable blocked state, not a system error.
            message = str(e)
            target_status: Optional[str]
            if isinstance(e, ValueError) and message.startswith("INSTALLATION BLOCKED:"):
                target_status = AutomationStatus.BLOCKED
            elif isinstance(e, ValueError) and message.startswith("Automation already installed:"):
                # A repeat request must not downgrade a healthy installed copy.
                target_status = None
            else:
                target_status = AutomationStatus.ERROR
            # Metadata is updated only after the imported copy and its exact
            # credential mapping are ready. On failure, the imported copy is
            # removed when possible and the local record records a safe state.
            if target_status:
                await self._update_status(automation_id, target_status)
            raise
    
    # ============================================================
    # Explicit execution with optional profile context
    # ============================================================

    async def run_automation(self, automation_id: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Trigger an enabled imported copy and persist non-sensitive execution metadata."""
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        selected_profile_id: Optional[uuid.UUID] = None
        try:
            async with get_session() as session:
                automation = await session.get(AutomationModel, automation_id)
                if not automation:
                    raise ValueError(f"Automation not found: {automation_id}")
                if automation.status != AutomationStatus.ENABLED:
                    raise ValueError("Automation must be enabled before running")
                if not automation.n8n_workflow_id:
                    raise ValueError("Automation has no imported n8n workflow")
                workflow_id = automation.n8n_workflow_id

            preflight = await self.preflight_automation(automation_id)
            if preflight["status"] != "ready":
                reasons = preflight.get("missing_requirements") or ["preflight did not pass"]
                raise ValueError("EXECUTION BLOCKED: " + "; ".join(str(item) for item in reasons))

            selected_profile_id, profile_context = await self._resolve_execution_profile(profile_id, automation_id)
            async with get_session() as session:
                session.add(Execution(
                    id=execution_id,
                    automation_id=automation_id,
                    profile_id=selected_profile_id,
                    workflow_id=workflow_id,
                    status="queued",
                    result_data={"profile_context_applied": bool(profile_context)},
                ))
                await session.commit()

            async with self.n8n_client as client:
                n8n_execution_id = await client.execute_workflow(
                    workflow_id,
                    data={"automation_center": {"profile_id": str(selected_profile_id) if selected_profile_id else None, "context": profile_context}},
                )

            duration_ms = round((time.time() - start_time) * 1000)
            async with get_session() as session:
                execution = await session.get(Execution, execution_id)
                if execution:
                    execution.n8n_execution_id = str(n8n_execution_id)
                    execution.status = "running"
                    execution.duration_ms = duration_ms
                    await session.commit()

            self._log_operation(automation_id, "run", "running", time.time() - start_time)
            return {
                "success": True,
                "automation_id": automation_id,
                "execution_id": execution_id,
                "n8n_execution_id": str(n8n_execution_id),
                "profile_id": str(selected_profile_id) if selected_profile_id else None,
                "status": "running",
            }
        except ValueError:
            raise
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000)
            await self._mark_execution_failed(execution_id, duration_ms)
            self._log_operation(automation_id, "run", "error", time.time() - start_time, self._safe_error(exc))
            raise ValueError("Execution could not be started safely") from None

    async def refresh_execution(self, execution_id: str) -> Dict[str, Any]:
        """Synchronize one tracked execution using only n8n status metadata."""
        async with get_session() as session:
            execution = await session.get(Execution, execution_id)
            if not execution:
                raise ValueError("Execution not found")
            n8n_execution_id = execution.n8n_execution_id
            if not n8n_execution_id:
                return self._serialize_execution(execution)

        async with self.n8n_client as client:
            remote = await client.get_execution(n8n_execution_id)
        remote_status = str(remote.get("status") or remote.get("data", {}).get("status") or "running").lower()
        status_map = {
            "success": "completed", "completed": "completed",
            "error": "failed", "failed": "failed", "crashed": "failed",
            "canceled": "cancelled", "cancelled": "cancelled",
        }
        status = status_map.get(remote_status, "running")
        async with get_session() as session:
            execution = await session.get(Execution, execution_id)
            if not execution:
                raise ValueError("Execution not found")
            execution.status = status
            if status in {"completed", "failed", "cancelled"}:
                execution.completed_at = datetime.utcnow()
                execution.duration_ms = round((execution.completed_at - execution.started_at).total_seconds() * 1000)
            execution.result_data = {"remote_status": remote_status}
            await session.commit()
            return self._serialize_execution(execution)

    async def _resolve_execution_profile(self, profile_id: Optional[str], automation_id: str) -> tuple[Optional[uuid.UUID], Dict[str, Any]]:
        """Return only the automation-specific, non-sensitive context for an optional profile."""
        selected_id: Optional[uuid.UUID] = None
        if profile_id:
            try:
                selected_id = uuid.UUID(profile_id)
            except (ValueError, AttributeError):
                raise ValueError("profile_id must be a valid UUID") from None
        else:
            async with get_session() as session:
                active_profile = await session.scalar(
                    select(Profile).where(Profile.is_active.is_(True), Profile.is_enabled.is_(True)).limit(1)
                )
                selected_id = active_profile.id if active_profile else None

        if not selected_id:
            return None, {}

        profile_context = await ProfileManager().get_context(selected_id)
        defaults = profile_context.automation_defaults or {}
        context_key = {
            "email-assistant": "email",
            "laboral": "jobs",
            "news": "news",
            "personal-brand": "personal_brand",
            "playwright-jobs": "jobs",
        }.get(automation_id, automation_id)
        return selected_id, dict(defaults.get(context_key, {}))

    async def _mark_execution_failed(self, execution_id: str, duration_ms: int) -> None:
        """Safely finalize an existing execution after a trigger failure."""
        async with get_session() as session:
            execution = await session.get(Execution, execution_id)
            if execution:
                execution.status = "failed"
                execution.completed_at = datetime.utcnow()
                execution.duration_ms = duration_ms
                execution.error_message = "Execution trigger failed safely"
                execution.result_data = {"triggered": False}
                await session.commit()

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        """Return a bounded sanitized error summary suitable for logs only."""
        return log_sanitizer.sanitize_string(str(exc))[:300] or type(exc).__name__

    @staticmethod
    def _serialize_execution(execution: Execution) -> Dict[str, Any]:
        """Serialize safe execution metadata and omit runtime payloads."""
        return {
            "id": execution.id,
            "automation_id": execution.automation_id,
            "profile_id": str(execution.profile_id) if execution.profile_id else None,
            "workflow_id": execution.workflow_id,
            "n8n_execution_id": execution.n8n_execution_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "error_message": execution.error_message,
            "result": {"tracked": True},
        }

    # ============================================================
    # Enable/Disable
    # ============================================================

    async def enable_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Enable an automation by activating its n8n workflow.
        
        Flow:
        1. Check installed
        2. n8n activate
        3. Update status = enabled
        
        Args:
            automation_id: Automation ID to enable
            
        Returns:
            Enable result
        """
        start_time = time.time()
        operation = "enable"
        
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == automation_id)
                )
                db_automation = result.scalar_one_or_none()
                
                if not db_automation:
                    raise ValueError(f"Automation not found: {automation_id}")
                
                if db_automation.status not in [AutomationStatus.INSTALLED, AutomationStatus.DISABLED]:
                    raise ValueError(f"Automation must be installed or disabled to enable, current: {db_automation.status}")
                
                n8n_workflow_id = db_automation.n8n_workflow_id
                if not n8n_workflow_id:
                    raise ValueError(f"No n8n workflow ID for automation: {automation_id}")
                
                # Assign credentials before enabling
                manifest = self.manifest_manager.get_manifest(automation_id)
                if manifest:
                    await self._assign_credentials(automation_id, manifest, n8n_workflow_id)
                
                # Activate workflow
                async with self.n8n_client as client:
                    await client.activate_workflow(n8n_workflow_id)
                
                # Update status
                if not AutomationStatus.is_valid_transition(db_automation.status, AutomationStatus.ENABLED):
                    raise ValueError(f"Invalid status transition: {db_automation.status} -> {AutomationStatus.ENABLED}")
                
                db_automation.status = AutomationStatus.ENABLED
                db_automation.updated_at = datetime.utcnow()
                await session.commit()
            
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "success", duration)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "status": AutomationStatus.ENABLED,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "error", duration, str(e))
            
            # Update status to error
            await self._update_status(automation_id, AutomationStatus.ERROR)
            raise
    
    async def disable_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Disable an automation by deactivating its n8n workflow.
        
        Flow:
        1. n8n deactivate
        2. Update status = disabled
        
        Args:
            automation_id: Automation ID to disable
            
        Returns:
            Disable result
        """
        start_time = time.time()
        operation = "disable"
        
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == automation_id)
                )
                db_automation = result.scalar_one_or_none()
                
                if not db_automation:
                    raise ValueError(f"Automation not found: {automation_id}")
                
                if db_automation.status != AutomationStatus.ENABLED:
                    raise ValueError(f"Automation must be enabled to disable, current: {db_automation.status}")
                
                n8n_workflow_id = db_automation.n8n_workflow_id
                if not n8n_workflow_id:
                    raise ValueError(f"No n8n workflow ID for automation: {automation_id}")
                
                # Deactivate workflow
                async with self.n8n_client as client:
                    await client.deactivate_workflow(n8n_workflow_id)
                
                # Update status
                if not AutomationStatus.is_valid_transition(db_automation.status, AutomationStatus.DISABLED):
                    raise ValueError(f"Invalid status transition: {db_automation.status} -> {AutomationStatus.DISABLED}")
                
                db_automation.status = AutomationStatus.DISABLED
                db_automation.updated_at = datetime.utcnow()
                await session.commit()
            
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "success", duration)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "status": AutomationStatus.DISABLED,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "error", duration, str(e))
            raise
    
    # ============================================================
    # Uninstall
    # ============================================================
    
    async def uninstall_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Uninstall an automation.
        
        Flow:
        1. Disable workflow
        2. Delete workflow from n8n
        3. Delete automation_credentials
        4. Delete automation metadata
        5. NO delete global user credentials
        
        Args:
            automation_id: Automation ID to uninstall
            
        Returns:
            Uninstall result
        """
        start_time = time.time()
        operation = "uninstall"
        
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == automation_id)
                )
                db_automation = result.scalar_one_or_none()
                
                if not db_automation:
                    raise ValueError(f"Automation not found: {automation_id}")
                
                n8n_workflow_id = db_automation.n8n_workflow_id
                
                # 1. Disable workflow if enabled
                if db_automation.status == AutomationStatus.ENABLED and n8n_workflow_id:
                    try:
                        async with self.n8n_client as client:
                            await client.deactivate_workflow(n8n_workflow_id)
                    except Exception as e:
                        logger.warning(f"Failed to deactivate workflow before uninstall: {e}")
                
                # 2. Delete workflow from n8n
                if n8n_workflow_id:
                    try:
                        async with self.n8n_client as client:
                            await client.delete_workflow(n8n_workflow_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete workflow from n8n: {e}")
                
                # 3. Delete automation_credentials (but NOT the credentials themselves)
                await session.execute(
                    delete(AutomationCredentialModel).where(
                        AutomationCredentialModel.automation_id == automation_id
                    )
                )
                
                # 4. Delete automation metadata
                await session.execute(
                    delete(AutomationModel).where(AutomationModel.id == automation_id)
                )
                
                await session.commit()
            
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "success", duration)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "message": "Automation uninstalled successfully. Global credentials preserved.",
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(automation_id, operation, "error", duration, str(e))
            raise
    
    # ============================================================
    # Credential Mapping
    # ============================================================
    
    async def _assign_credentials(
        self,
        automation_id: str,
        manifest: Manifest,
        n8n_workflow_id: str
    ) -> Dict[str, str]:
        """Bind active account references to the newly imported n8n workflow only."""
        credential_mapping: Dict[str, str] = {}
        requirements_by_provider = {item.provider: set(item.scopes or []) for item in manifest.requirements}
        async with get_session() as session:
            for n8n_credential_type, provider_name in manifest.n8n.credential_mapping.items():
                result = await session.execute(
                    select(CredentialModel).where(CredentialModel.provider == provider_name)
                )
                required_scopes = requirements_by_provider.get(provider_name, set())
                credential = next(
                    (
                        candidate for candidate in result.scalars().all()
                        if candidate.status == "active"
                        and candidate.n8n_credential_id
                        and set(candidate.scopes or []).issuperset(required_scopes)
                        and (candidate.credential_metadata or {}).get("_n8n_credential_type") == n8n_credential_type
                    ),
                    None,
                )
                if not credential:
                    raise ValueError(
                        "INSTALLATION BLOCKED: "
                        f"{AccountResolver.MISSING_MAPPING_PREFIX}: {provider_name} -> {n8n_credential_type}"
                    )
                credential_mapping[n8n_credential_type] = credential.n8n_credential_id

        if not credential_mapping:
            return credential_mapping

        async with self.n8n_client as client:
            workflow = await client.get_workflow(n8n_workflow_id)
            nodes = workflow.get("nodes", [])
            applied_types: set[str] = set()
            for node in nodes:
                node_credentials = node.get("credentials") or {}
                for credential_type, n8n_credential_id in credential_mapping.items():
                    if credential_type not in node_credentials:
                        continue
                    original = node_credentials.get(credential_type)
                    updated = dict(original) if isinstance(original, dict) else {}
                    updated["id"] = n8n_credential_id
                    node_credentials[credential_type] = updated
                    applied_types.add(credential_type)
                if node_credentials:
                    node["credentials"] = node_credentials

            missing_node_types = sorted(set(credential_mapping) - applied_types)
            if missing_node_types:
                raise ValueError(
                    "INSTALLATION BLOCKED: Credential mapping does not match workflow node type(s): "
                    + ", ".join(missing_node_types)
                )

            workflow["nodes"] = nodes
            await client.update_workflow(n8n_workflow_id, workflow)
            logger.info("Applied %d credential type mapping(s) to imported workflow %s", len(applied_types), automation_id)
        return credential_mapping
    
    # ============================================================
    # Validation Helpers
    # ============================================================
    
    async def _validate_dependencies(self, manifest: Manifest) -> List[str]:
        """Validate dependencies that are other Automation Center automations.

        Manifests also declare infrastructure and provider prerequisites such as
        PostgreSQL, Playwright, or Google OAuth. Those are not automation IDs:
        PostgreSQL availability is already required by this manager's database
        session, Playwright is checked by the consuming workflow, and provider
        readiness is validated separately through ``requirements``. Treating
        them as database automation IDs prevented every real workflow from
        reaching its actual credential validation step.
        """
        external_dependencies = {"postgresql", "playwright", "google-oauth2"}
        missing = []

        for dep in manifest.dependencies:
            if dep in external_dependencies:
                continue

            # Only declared automation-to-automation dependencies must exist
            # as installed Automation Center records.
            async with get_session() as session:
                result = await session.execute(
                    select(AutomationModel).where(AutomationModel.id == dep)
                )
                if not result.scalar_one_or_none():
                    missing.append(dep)

        return missing
    
    async def _resolve_manifest_accounts(self, manifest: Manifest) -> Dict[str, Any]:
        """Resolve account and n8n compatibility from metadata, without secret access."""
        async with get_session() as session:
            result = await session.execute(select(CredentialModel))
            resolution = self.account_resolver.resolve(manifest, result.scalars().all())

        for variable_name in (manifest.metadata.env_vars_required if manifest.metadata else []):
            if not os.getenv(variable_name):
                resolution["missing_requirements"].append(f"environment: {variable_name}")
        resolution["missing_requirements"] = list(dict.fromkeys(resolution["missing_requirements"]))
        resolution["ready"] = not resolution["missing_requirements"]
        return resolution

    async def resolve_automation_accounts(self, automation_id: str) -> Dict[str, Any]:
        """Expose a safe account-resolution report for one automation."""
        manifest = self.manifest_manager.get_manifest(automation_id)
        if not manifest:
            raise ValueError(f"Automation not found: {automation_id}")
        resolution = await self._resolve_manifest_accounts(manifest)
        return {"automation_id": automation_id, **resolution}

    async def _validate_credentials(self, manifest: Manifest) -> List[str]:
        """Return safe, actionable blockers for unresolved accounts and mappings."""
        return (await self._resolve_manifest_accounts(manifest))["missing_requirements"]

    async def _validate_runtime_dependencies(self, manifest: Manifest) -> List[str]:
        """Validate local runtime prerequisites without probing user accounts."""
        missing: List[str] = []
        if "playwright" in manifest.dependencies:
            playwright_url = os.getenv("PLAYWRIGHT_BASE_URL") or getattr(settings, "PLAYWRIGHT_API_URL", None)
            if not playwright_url:
                missing.append("runtime: Playwright service URL is not configured")
            else:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{playwright_url.rstrip('/')}/health")
                    if response.status_code != 200:
                        missing.append("runtime: Playwright service is unavailable")
                except httpx.HTTPError:
                    missing.append("runtime: Playwright service is unavailable")
        return missing
    
    # ============================================================
    # Status Management
    # ============================================================
    
    async def _update_status(self, automation_id: str, status: str) -> None:
        """Update automation status in database."""
        async with get_session() as session:
            result = await session.execute(
                select(AutomationModel).where(AutomationModel.id == automation_id)
            )
            db_automation = result.scalar_one_or_none()
            
            if db_automation:
                db_automation.status = status
                db_automation.updated_at = datetime.utcnow()
                await session.commit()
    
    # ============================================================
    # Version Checking
    # ============================================================
    
    async def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check for available updates for installed automations.
        
        Returns:
            List of automations with update_available flag
        """
        updates = []
        
        async with get_session() as session:
            result = await session.execute(
                select(AutomationModel).where(
                    AutomationModel.status.in_([AutomationStatus.INSTALLED, AutomationStatus.ENABLED, AutomationStatus.DISABLED])
                )
            )
            automations = result.scalars().all()
            
            for auto in automations:
                manifest = self.manifest_manager.get_manifest(auto.id)
                if manifest and manifest.version != auto.version:
                    updates.append({
                        "automation_id": auto.id,
                        "name": auto.name,
                        "current_version": auto.version,
                        "available_version": manifest.version,
                        "update_available": True,
                    })
        
        return updates
    
    # ============================================================
    # Logging
    # ============================================================
    
    def _log_operation(
        self,
        automation_id: str,
        operation: str,
        status: str,
        duration: float,
        error: Optional[str] = None
    ) -> None:
        """Log automation operation (no secrets)."""
        log_data = {
            "automation_id": automation_id,
            "operation": operation,
            "status": status,
            "duration_ms": round(duration * 1000, 2),
        }
        
        if error:
            log_data["error"] = error
            logger.error(f"Automation operation failed: {log_data}")
        else:
            logger.info(f"Automation operation completed: {log_data}")
    
    # ============================================================
    # Workflow Logs
    # ============================================================
    
    async def get_automation_logs(self, automation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for an automation."""
        async with get_session() as session:
            result = await session.execute(
                select(AutomationModel).where(AutomationModel.id == automation_id)
            )
            db_automation = result.scalar_one_or_none()
            
            if not db_automation:
                raise ValueError(f"Automation not found: {automation_id}")
            
            # Get executions from database
            from ...database.models import Execution
            exec_result = await session.execute(
                select(Execution)
                .where(Execution.automation_id == automation_id)
                .order_by(Execution.started_at.desc())
                .limit(limit)
            )
            executions = exec_result.scalars().all()
            
            return [
                {
                    "id": e.id,
                    "automation_id": e.automation_id,
                    "profile_id": str(e.profile_id) if e.profile_id else None,
                    "workflow_id": e.workflow_id,
                    "n8n_execution_id": e.n8n_execution_id,
                    "status": e.status,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "duration_ms": e.duration_ms,
                                        "error_message": e.error_message,
                    "result": {"tracked": True},

                }
                for e in executions
            ]