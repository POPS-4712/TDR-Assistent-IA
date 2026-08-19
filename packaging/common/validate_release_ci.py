#!/usr/bin/env python3
"""Validate the native release workflow without claiming any build occurred."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "native-release-builds.yml"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
EXPECTED = {
    "windows-x64": {"runner": "windows-latest", "family": "windows", "architecture": "x64", "files": {f"AutomationCenter-{VERSION}-win-x64.exe", f"AutomationCenter-{VERSION}-win-x64.zip"}},
    "windows-arm64": {"runner": "windows-11-arm", "family": "windows", "architecture": "arm64", "files": {f"AutomationCenter-{VERSION}-win-arm64.exe", f"AutomationCenter-{VERSION}-win-arm64.zip"}},
    "linux-x64": {"runner": "ubuntu-24.04", "family": "linux", "architecture": "x64", "files": {f"AutomationCenter-{VERSION}-linux-x64.deb", f"AutomationCenter-{VERSION}-linux-x64.tar.gz"}},
    "linux-arm64": {"runner": "ubuntu-24.04-arm", "family": "linux", "architecture": "arm64", "files": {f"AutomationCenter-{VERSION}-linux-arm64.deb", f"AutomationCenter-{VERSION}-linux-arm64.tar.gz"}},
    "macos-x64": {"runner": "macos-26-intel", "family": "macos", "architecture": "x64", "files": {f"AutomationCenter-{VERSION}-macos-x64.dmg"}},
    "macos-arm64": {"runner": "macos-26", "family": "macos", "architecture": "arm64", "files": {f"AutomationCenter-{VERSION}-macos-arm64.dmg"}},
}
REQUIRED_FILES = (
    ROOT / "packaging" / "windows" / "build-windows.ps1",
    ROOT / "packaging" / "linux" / "build-linux.sh",
    ROOT / "packaging" / "macos" / "build-macos.sh",
    ROOT / "packaging" / "common" / "release_manifest.py",
    ROOT / "packaging" / "common" / "scan_artifact.py",
)


def fail(message: str) -> None:
    print(f"RELEASE CI VALIDATION FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    if VERSION != "1.0.0":
        fail("VERSION must be 1.0.0 for this release definition")
    if any(not path.is_file() for path in REQUIRED_FILES):
        fail("required packaging definitions are missing")
    if not WORKFLOW.is_file():
        fail("native release workflow is missing")
    try:
        document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        fail("native release workflow is not valid YAML")
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        fail("native release workflow has no jobs")
    jobs = document["jobs"]
    build = jobs.get("build")
    if not isinstance(build, dict):
        fail("native matrix build job is missing")
    include = build.get("strategy", {}).get("matrix", {}).get("include")
    if not isinstance(include, list):
        fail("native matrix include list is missing")
    matrix = {item.get("target"): item for item in include if isinstance(item, dict)}
    if set(matrix) != set(EXPECTED):
        fail("native matrix target set does not match required targets")
    if sum(len(item["files"]) for item in EXPECTED.values()) != 10:
        fail("release contract must contain exactly ten artifacts")
    for target, expected in EXPECTED.items():
        entry = matrix[target]
        if entry.get("runner") != expected["runner"]:
            fail(f"{target} runner is not the required native runner")
        if entry.get("family") != expected["family"] or entry.get("architecture") != expected["architecture"]:
            fail(f"{target} matrix metadata is inconsistent")
        if set(str(entry.get("expected_files", "")).split(",")) != expected["files"]:
            fail(f"{target} expected filenames are inconsistent")
    preflight_steps = "\n".join(str(step) for step in jobs.get("preflight", {}).get("steps", []))
    for required_check in ("git status --porcelain", "validate_release_ci.py", "validate_definitions.py", "VERSION"):
        if required_check not in preflight_steps:
            fail("preflight omits a required source-integrity or version check")
    assemble = jobs.get("assemble-release", {})
    assemble_text = str(assemble)
    if "inputs.target == 'all'" not in str(assemble.get("if", "")):
        fail("release assembly is not restricted to the complete target set")
    for required_assembly_gate in ('"10"', "verify --complete --security-scan", "sha256s --complete --security-scan"):
        if required_assembly_gate not in assemble_text:
            fail("release assembly does not enforce the ten-artifact complete gate")
    release_text = str(jobs.get("publish-release", {}))
    for required_gate in ("inputs.create_release", "needs.assemble-release.result == 'success'", "gh release create", "SHA256SUMS.txt", "verify --complete --security-scan"):
        if required_gate not in release_text:
            fail("public release gate is incomplete")
    print("RELEASE CI VALIDATION PASS: six native targets, source-integrity gate, artifact verification, checksums, and complete-release gate are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
