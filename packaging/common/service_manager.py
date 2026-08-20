#!/usr/bin/env python3
"""Local-only service manager used by Automation Center launchers and installers.

This program never stores or prints secret values. It orchestrates the production
Docker composition from the host OS, where Docker Desktop or Docker Engine is
available. It is intentionally not imported by the FastAPI container.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path
from typing import Any, Iterable

APP_NAME = "Automation Center"
APP_VERSION = "1.0.0"
PROJECT_NAME = "automation-center"
SERVICES = ("frontend", "backend", "postgres", "n8n", "playwright")
PREFERRED_PORTS = {
    "frontend": 3001,
    "backend": 8000,
    "postgres": 5432,
    "n8n": 5678,
    "playwright": 3000,
}
SENSITIVE_KEYS = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "ENCRYPTION_KEY")


def application_root() -> Path:
    """Locate the distribution root in source, portable and PyInstaller modes."""
    override = os.getenv("AUTOMATION_CENTER_APP_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        macos_resources = executable_dir.parent / "Resources" / "app"
        return macos_resources if macos_resources.exists() else executable_dir
    return Path(__file__).resolve().parents[2]


def normalized_architecture(value: str | None = None) -> str:
    raw = (value or platform.machine()).strip().lower()
    aliases = {
        "amd64": "x64", "x86_64": "x64", "x64": "x64",
        "arm64": "arm64", "aarch64": "arm64",
    }
    return aliases.get(raw, raw or "unknown")


def platform_id() -> str:
    return platform.system().lower()


def default_data_dir() -> Path:
    override = os.getenv("AUTOMATION_CENTER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    system = platform_id()
    if system == "windows":
        return Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AutomationCenter"
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / "AutomationCenter"
    return Path.home() / ".local" / "share" / "automation-center"


def portable_data_dir(root: Path) -> Path:
    return root / "data"


def data_dir(portable: bool = False, root: Path | None = None) -> Path:
    resolved_root = root or application_root()
    return portable_data_dir(resolved_root) if portable else default_data_dir()


def runtime_paths(data_root: Path) -> dict[str, Path]:
    return {
        "root": data_root,
        "config": data_root / "config",
        "runtime": data_root / "runtime",
        "logs": data_root / "logs",
        "backups": data_root / "backups",
        "vault_metadata": data_root / "vault-metadata",
        "state": data_root / "state",
        "env": data_root / "config" / "runtime.env",
        "first_run": data_root / "state" / "first-run-complete.json",
    }


def create_private_directories(data_root: Path) -> dict[str, Path]:
    paths = runtime_paths(data_root)
    for name, path in paths.items():
        if name not in {"env", "first_run"}:
            path.mkdir(parents=True, exist_ok=True)
            if platform_id() != "windows":
                path.chmod(0o700)
    return paths


def write_runtime_env(data_root: Path, ui_port: int = 3001) -> Path:
    paths = create_private_directories(data_root)
    env_file = paths["env"]
    if env_file.exists():
        return env_file
    # Values are generated locally only and are never printed or committed.
    values = {
        "APP_VERSION": APP_VERSION,
        "ENVIRONMENT": "production",
        "AUTOMATION_CENTER_INSTANCE_SUFFIX": "-" + secrets.token_hex(8),
        "AUTOMATION_CENTER_DATA_DIR": str(data_root),
        "AUTOMATION_CENTER_UI_PORT": str(ui_port),
        "POSTGRES_DB": "automation_center",
        "POSTGRES_USER": "automation_center",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "N8N_ENCRYPTION_KEY": secrets.token_urlsafe(32),
        "BACKEND_SECRET_KEY": secrets.token_urlsafe(48),
        "N8N_HOST": "localhost",
        "N8N_PROTOCOL": "http",
        "N8N_SECURE_COOKIE": "false",
        "TZ": time.tzname[0] if time.tzname else "UTC",
    }
    content = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    env_file.write_text(content, encoding="utf-8")
    if platform_id() != "windows":
        env_file.chmod(0o600)
    return env_file


def safe_environment_summary(env_file: Path) -> dict[str, Any]:
    if not env_file.exists():
        return {"configured": False, "fields": []}
    fields = []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key = line.split("=", 1)[0]
        fields.append({"name": key, "sensitive": any(marker in key.upper() for marker in SENSITIVE_KEYS)})
    return {"configured": True, "fields": fields}


def compose_command() -> list[str] | None:
    if shutil.which("docker"):
        probe = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, check=False)
        if probe.returncode == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def execute(command: Iterable[str], timeout: int = 60) -> tuple[int, str]:
    try:
        result = subprocess.run(list(command), capture_output=True, text=True, timeout=timeout, check=False)
        output = (result.stdout or result.stderr or "").strip()
        return result.returncode, output[-1000:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, type(exc).__name__


def compose_project_name(data_root: Path) -> str:
    """Return an isolated project name for new installations and the legacy name otherwise."""
    suffix = _runtime_env_value(data_root, "AUTOMATION_CENTER_INSTANCE_SUFFIX", "") or ""
    return f"{PROJECT_NAME}{suffix}" if re.fullmatch(r"-[0-9a-f]{16}", suffix) else PROJECT_NAME


def compose_args(data_root: Path, compose_file: Path | None = None) -> list[str]:
    command = compose_command()
    if not command:
        raise RuntimeError("Docker runtime is not available")
    chosen = compose_file or application_root() / "docker-compose.prod.yml"
    if not chosen.exists():
        raise RuntimeError(f"Production compose file is missing: {chosen}")
    env_file = write_runtime_env(data_root)
    return [*command, "--project-name", compose_project_name(data_root), "--env-file", str(env_file), "--file", str(chosen)]


def port_state(port: int) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    try:
        occupied = sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()
    return {"port": port, "occupied": occupied}


def docker_available() -> dict[str, Any]:
    command = compose_command()
    if not command:
        return {"available": False, "message": "Docker Desktop or Docker Engine was not detected"}
    code, _ = execute(["docker", "info"], timeout=15)
    return {
        "available": code == 0,
        "command": " ".join(command),
        "message": "ready" if code == 0 else "Docker was found but is not running or inaccessible",
    }


def disk_summary(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {"total_bytes": usage.total, "free_bytes": usage.free}


def compose_service_ids(data_root: Path) -> dict[str, str]:
    try:
        base = compose_args(data_root)
    except RuntimeError:
        return {}
    services: dict[str, str] = {}
    for service in SERVICES:
        code, output = execute([*base, "ps", "-q", service], timeout=15)
        if code == 0 and output:
            services[service] = output.splitlines()[-1].strip()
    return services


def container_health(container_id: str) -> str:
    code, output = execute(["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container_id], timeout=15)
    return output if code == 0 and output else "unknown"


def status(data_root: Path) -> dict[str, Any]:
    runtime = docker_available()
    ids = compose_service_ids(data_root) if runtime["available"] else {}
    services = {}
    for service in SERVICES:
        container_id = ids.get(service)
        state = container_health(container_id) if container_id else "stopped"
        services[service] = {"status": state, "container_present": bool(container_id)}
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "platform": platform_id(),
        "architecture": normalized_architecture(),
        "runtime": runtime,
        "first_run_complete": runtime_paths(data_root)["first_run"].exists(),
        "services": services,
    }


def health(data_root: Path) -> dict[str, Any]:
    result = status(data_root)
    allowed = {"healthy", "running"}
    result["healthy"] = bool(result["runtime"]["available"]) and all(
        service["status"] in allowed for service in result["services"].values()
    )
    return result


def diagnose(data_root: Path) -> dict[str, Any]:
    paths = create_private_directories(data_root)
    result = status(data_root)
    result.update({
        "data_dir": str(data_root),
        "disk": disk_summary(data_root),
        "ports": {name: port_state(port) for name, port in PREFERRED_PORTS.items()},
        "configuration": safe_environment_summary(paths["env"]),
        "time": datetime.now(timezone.utc).isoformat(),
    })
    return result


def run_service_command(action: str, data_root: Path, services: list[str] | None = None) -> dict[str, Any]:
    selected = services or list(SERVICES)
    unknown = sorted(set(selected).difference(SERVICES))
    if unknown:
        raise ValueError(f"Unknown services: {', '.join(unknown)}")
    base = compose_args(data_root)
    if action == "start":
        conflicts = {name: port_state(PREFERRED_PORTS[name]) for name in selected if name in PREFERRED_PORTS}
        # Existing ports are reported but never forcefully released. Compose may own them already.
        command = [*base, "up", "--detach", *selected]
    elif action == "stop":
        conflicts = {}
        command = [*base, "stop", *selected]
    elif action == "restart":
        conflicts = {}
        command = [*base, "restart", *selected]
    else:
        raise ValueError(f"Unsupported action: {action}")
    timeout = 600 if action == "start" else 180
    code, _ = execute(command, timeout=timeout)
    return {
        "success": code == 0,
        "action": action,
        "services": selected,
        "port_observations": conflicts,
        "message": "completed" if code == 0 else "Docker command failed; review local logs",
        "detail": "docker_compose_failed" if code != 0 else None,
    }


def set_runtime_env_value(data_root: Path, name: str, value: str) -> Path:
    """Replace one private runtime setting without displaying its value."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} cannot be empty")
    env_file = write_runtime_env(data_root)
    prefix = f"{name}="
    lines = [line for line in env_file.read_text(encoding="utf-8").splitlines() if not line.startswith(prefix)]
    lines.append(f"{name}={cleaned}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if platform_id() != "windows":
        env_file.chmod(0o600)
    return env_file


def configure_n8n_api_key(data_root: Path) -> dict[str, Any]:
    """Store a user-created n8n Public API key through a terminal prompt without echoing it."""
    api_key = getpass.getpass("n8n Public API key (input hidden): ")
    set_runtime_env_value(data_root, "N8N_API_KEY", api_key)
    return {
        "success": True,
        "message": "n8n Public API key stored in private runtime configuration; restart local services to apply it",
    }


def _runtime_env_value(data_root: Path, name: str, default: str | None = None) -> str | None:
    env_file = runtime_paths(data_root)["env"]
    if not env_file.exists():
        return default
    prefix = f"{name}="
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return default


def _contains_sensitive_metadata(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).upper()
            if any(marker in normalized for marker in SENSITIVE_KEYS):
                return True
            if _contains_sensitive_metadata(child):
                return True
    if isinstance(value, list):
        return any(_contains_sensitive_metadata(item) for item in value)
    return False


def backup_metadata(data_root: Path) -> dict[str, Any]:
    """Persist the existing metadata-only backup, never secret values, before upgrade."""
    paths = create_private_directories(data_root)
    ui_port = _runtime_env_value(data_root, "AUTOMATION_CENTER_UI_PORT", "3001")
    url = f"http://127.0.0.1:{ui_port}/api/v1/backup/export"
    try:
        with urlopen(url, timeout=20) as response:  # nosec B310: local loopback only
            backup = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"success": False, "message": "Metadata backup could not be created", "error_type": type(exc).__name__}
    if _contains_sensitive_metadata(backup):
        return {"success": False, "message": "Metadata backup was rejected by the local secret guard"}
    destination = paths["backups"] / f"metadata-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    destination.write_text(json.dumps(backup, indent=2, sort_keys=True), encoding="utf-8")
    if platform_id() != "windows":
        destination.chmod(0o600)
    return {"success": True, "message": "Metadata backup created", "backup_path": str(destination)}


def remove_user_data(data_root: Path, confirmed: bool) -> dict[str, Any]:
    """Remove only the explicitly named production project and private data root."""
    if not confirmed:
        raise ValueError("Explicit remove-data confirmation is required")
    try:
        base = compose_args(data_root)
    except RuntimeError as exc:
        return {"success": False, "message": str(exc)}
    code, _ = execute([*base, "down", "--volumes", "--remove-orphans"], timeout=180)
    if code != 0:
        return {"success": False, "message": "Local services could not be removed safely; user data was preserved"}
    try:
        shutil.rmtree(data_root)
    except FileNotFoundError:
        pass
    except OSError:
        return {"success": False, "message": "Production volumes were removed but private user data could not be removed"}
    return {"success": True, "message": "Application user data and dedicated production volumes were removed"}


def mark_first_run_complete(data_root: Path) -> Path:
    paths = create_private_directories(data_root)
    payload = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "app_version": APP_VERSION,
        "platform": platform_id(),
        "architecture": normalized_architecture(),
    }
    paths["first_run"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return paths["first_run"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Automation Center local service manager")
    parser.add_argument("command", choices=["init", "start", "stop", "restart", "status", "health", "diagnose", "backup-metadata", "prepare-upgrade", "configure-n8n-api-key", "remove-data", "complete-first-run"])
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--service", action="append", dest="services", choices=SERVICES)
    parser.add_argument("--ui-port", type=int, default=int(os.getenv("AUTOMATION_CENTER_UI_PORT", "3001")))
    parser.add_argument("--confirm-remove-data", action="store_true", help="Required before destructive data removal")
    parser.add_argument("--json", action="store_true", help="Emit non-sensitive JSON only")
    args = parser.parse_args()

    root = data_dir(portable=args.portable) if args.data_dir is None else args.data_dir.expanduser()
    try:
        if args.command == "init":
            paths = runtime_paths(root)
            configuration_existed = paths["env"].exists()
            env_file = write_runtime_env(root, args.ui_port)
            result: dict[str, Any] = {
                "success": True,
                "data_dir": str(root),
                "configuration_created": not configuration_existed,
                "configuration_reused": configuration_existed,
            }
        elif args.command in {"start", "stop", "restart"}:
            if args.command == "start":
                write_runtime_env(root, args.ui_port)
            result = run_service_command(args.command, root, args.services)
        elif args.command == "status":
            result = status(root)
        elif args.command == "health":
            result = health(root)
        elif args.command == "diagnose":
            result = diagnose(root)
        elif args.command in {"backup-metadata", "prepare-upgrade"}:
            result = backup_metadata(root)
        elif args.command == "configure-n8n-api-key":
            result = configure_n8n_api_key(root)
        elif args.command == "remove-data":
            result = remove_user_data(root, args.confirm_remove_data)
        else:
            marker = mark_first_run_complete(root)
            result = {"success": True, "first_run_marker": str(marker)}
    except (RuntimeError, ValueError) as exc:
        result = {"success": False, "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("success", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
