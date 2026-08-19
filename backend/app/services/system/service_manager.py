"""Safe host-runtime service management for a production-local installation.

The control plane is disabled by default. When explicitly enabled and provided a
Docker socket by the production deployment, it can only address containers
labelled as the Automation Center production compose project. It never receives
secrets, executes arbitrary shell commands, or manages unrelated containers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from ...core.config import settings

try:  # Docker is an optional host capability, never a startup requirement.
    import docker
    from docker.errors import DockerException, NotFound
except ImportError:  # pragma: no cover - covered through availability response
    docker = None
    DockerException = Exception
    NotFound = Exception


MANAGED_SERVICES = ("backend", "postgres", "n8n", "playwright", "frontend")
SAFE_ACTIONS = ("start", "stop", "restart")


@dataclass(frozen=True)
class ServiceControlResult:
    service: str
    action: str
    success: bool
    status: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "action": self.action,
            "success": self.success,
            "status": self.status,
            "message": self.message,
        }


class LocalServiceManager:
    """Restrictive bridge to an explicitly mounted local Docker Engine."""

    def __init__(self) -> None:
        self.enabled = bool(settings.LOCAL_SERVICE_CONTROL_ENABLED)
        self.project_name = settings.DOCKER_COMPOSE_PROJECT

    def availability(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "enabled": False,
                "available": False,
                "message": "Local service controls are disabled in this deployment",
            }
        if docker is None:
            return {
                "enabled": True,
                "available": False,
                "message": "Docker client support is unavailable",
            }
        try:
            client = docker.from_env()
            client.ping()
            return {"enabled": True, "available": True, "message": "Local Docker runtime is available"}
        except DockerException:
            return {
                "enabled": True,
                "available": False,
                "message": "Docker runtime is unavailable or not authorized",
            }

    def managed_container_statuses(self) -> Dict[str, Dict[str, Any]]:
        statuses = {service: {"status": "not_managed", "container_present": False} for service in MANAGED_SERVICES}
        if not self.enabled or docker is None:
            return statuses
        try:
            client = docker.from_env()
            containers = client.containers.list(
                all=True,
                filters={"label": f"com.docker.compose.project={self.project_name}"},
            )
        except DockerException:
            return statuses
        for container in containers:
            labels = container.labels or {}
            service = labels.get("com.docker.compose.service")
            if service in statuses:
                statuses[service] = {
                    "status": self._normalize_status(container.status, container.attrs.get("State", {})),
                    "container_present": True,
                }
        return statuses

    def control(self, action: str, services: Iterable[str]) -> list[Dict[str, Any]]:
        if action not in SAFE_ACTIONS:
            raise ValueError("Unsupported service action")
        selected = list(services)
        unknown = sorted(set(selected).difference(MANAGED_SERVICES))
        if unknown:
            raise ValueError("Unknown service requested")
        availability = self.availability()
        if not availability["available"]:
            return [
                ServiceControlResult(
                    service=service,
                    action=action,
                    success=False,
                    status="not_managed",
                    message=availability["message"],
                ).to_dict()
                for service in selected
            ]
        client = docker.from_env()
        results = []
        for service in selected:
            results.append(self._control_one(client, action, service).to_dict())
        return results

    def _control_one(self, client: Any, action: str, service: str) -> ServiceControlResult:
        filters = {
            "label": [
                f"com.docker.compose.project={self.project_name}",
                f"com.docker.compose.service={service}",
            ]
        }
        try:
            matches = client.containers.list(all=True, filters=filters)
        except DockerException:
            return ServiceControlResult(service, action, False, "error", "Docker runtime is unavailable")
        if len(matches) != 1:
            return ServiceControlResult(service, action, False, "not_managed", "Managed container was not found")
        container = matches[0]
        try:
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=30)
            else:
                container.restart(timeout=30)
            container.reload()
            return ServiceControlResult(
                service,
                action,
                True,
                self._normalize_status(container.status, container.attrs.get("State", {})),
                "Service action completed",
            )
        except (DockerException, NotFound):
            return ServiceControlResult(service, action, False, "error", "Service action failed safely")

    @staticmethod
    def _normalize_status(status: Optional[str], state: Dict[str, Any]) -> str:
        health = (state.get("Health") or {}).get("Status")
        if health == "healthy":
            return "running"
        if health == "unhealthy":
            return "error"
        if status in {"running", "created", "restarting"}:
            return "starting" if status in {"created", "restarting"} else "running"
        if status in {"exited", "dead", "removing"}:
            return "stopped" if status == "exited" else "error"
        return "unknown"
