#!/usr/bin/env python3
"""Static package-definition validation for platforms unavailable on the build host."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
REQUIRED = [
    ROOT / "docker-compose.prod.yml",
    ROOT / "frontend" / "nginx.prod.conf",
    ROOT / "packaging" / "common" / "service_manager.py",
    ROOT / "packaging" / "common" / "scan_artifact.py",
    ROOT / "packaging" / "common" / "validate_release_ci.py",
    ROOT / "packaging" / "windows" / "build-windows.ps1",
    ROOT / "packaging" / "windows" / "AutomationCenter.iss",
    ROOT / "packaging" / "linux" / "build-linux.sh",
    ROOT / "packaging" / "macos" / "build-macos.sh",
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    backend = (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    frontend = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    errors = []
    if missing:
        errors.append("missing required packaging definitions")
    backend_version = re.search(r'APP_VERSION: str = "([^"]+)"', backend)
    if not backend_version or backend_version.group(1) != VERSION:
        errors.append("backend version does not match VERSION")
    if frontend.get("version") != VERSION:
        errors.append("frontend version does not match VERSION")
    for expected in ("127.0.0.1:${AUTOMATION_CENTER_UI_PORT", "automation_center_postgres_data", "automation_center_n8n_data", "nginx.prod.conf", "http://127.0.0.1/health"):
        if expected not in compose:
            errors.append(f"production compose is missing {expected}")
    if "http://localhost/health" in compose:
        errors.append("production compose must not use localhost for the frontend healthcheck")
    dist = ROOT / "dist"
    manifest_path = dist / "release-manifest.json"
    unexpected = [
        path.name for path in dist.iterdir()
        if path.is_file() and path.name not in {"release-manifest.json", "SHA256SUMS.txt"}
    ] if dist.exists() else []
    if unexpected:
        errors.append("dist contains unverified files")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest.get("artifacts", [])
            if manifest.get("version") != VERSION or not artifacts or any(
                item.get("status", "").upper() != "BUILT" or not item.get("sha256")
                for item in artifacts
            ):
                errors.append("release manifest is incomplete or inconsistent")
        except (OSError, json.JSONDecodeError):
            errors.append("release manifest is unreadable")
    if errors:
        print("PACKAGE DEFINITION VALIDATION FAILED: " + "; ".join(errors), file=sys.stderr)
        return 1
    print(f"PACKAGE DEFINITIONS VALIDATED: version={VERSION}; Windows x64/ARM64, Linux x64/ARM64 and macOS x64/ARM64 definitions are present.")
    print("ARTIFACT STATUS: no unverified files are present; any release manifest is structurally validated, while hashes require artifact verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
