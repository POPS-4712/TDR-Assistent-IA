#!/usr/bin/env python3
"""Record, assemble, and verify genuine Automation Center release artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform as runtime_platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRODUCT = "Automation Center"
ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = (
    "windows-x64", "windows-arm64", "linux-x64", "linux-arm64", "macos-x64", "macos-arm64",
)
FORMATS = ("exe", "zip", "deb", "tar.gz", "dmg")


def required_artifacts(current_version: str) -> dict[tuple[str, str], tuple[str, str]]:
    """Return the only ten artifact identities permitted in a complete v1 release."""
    return {
        ("windows-x64", f"AutomationCenter-{current_version}-win-x64.exe"): ("x64", "exe"),
        ("windows-x64", f"AutomationCenter-{current_version}-win-x64.zip"): ("x64", "zip"),
        ("windows-arm64", f"AutomationCenter-{current_version}-win-arm64.exe"): ("arm64", "exe"),
        ("windows-arm64", f"AutomationCenter-{current_version}-win-arm64.zip"): ("arm64", "zip"),
        ("linux-x64", f"AutomationCenter-{current_version}-linux-x64.deb"): ("x64", "deb"),
        ("linux-x64", f"AutomationCenter-{current_version}-linux-x64.tar.gz"): ("x64", "tar.gz"),
        ("linux-arm64", f"AutomationCenter-{current_version}-linux-arm64.deb"): ("arm64", "deb"),
        ("linux-arm64", f"AutomationCenter-{current_version}-linux-arm64.tar.gz"): ("arm64", "tar.gz"),
        ("macos-x64", f"AutomationCenter-{current_version}-macos-x64.dmg"): ("x64", "dmg"),
        ("macos-arm64", f"AutomationCenter-{current_version}-macos-arm64.dmg"): ("arm64", "dmg"),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def filename(entry: dict[str, Any]) -> str:
    value = entry.get("filename") or entry.get("name")
    if not isinstance(value, str) or not value:
        raise ValueError("Artifact entry has no filename")
    return value


def normalize_entry(entry: dict[str, Any], current_version: str) -> dict[str, Any]:
    """Migrate Phase 2.13 metadata without changing its recorded hash values."""
    normalized = dict(entry)
    normalized["filename"] = filename(normalized)
    normalized.pop("name", None)
    normalized.setdefault("version", current_version)
    normalized["status"] = str(normalized.get("status", "BUILT")).upper()
    normalized.setdefault("validated", normalized["status"] == "BUILT")
    return normalized


def load_manifest(path: Path, current_version: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "product": PRODUCT,
            "version": current_version,
            "generated_at": None,
            "artifacts": [],
            "builds": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("product") != PRODUCT or data.get("version") != current_version:
        raise ValueError("Existing release manifest does not match the current product/version")
    if not isinstance(data.get("artifacts"), list):
        raise ValueError("Existing release manifest has an invalid artifact list")
    data["artifacts"] = [normalize_entry(item, current_version) for item in data["artifacts"]]
    data.setdefault("builds", [])
    if not isinstance(data["builds"], list):
        raise ValueError("Existing release manifest has an invalid build list")
    return data


def manifest_path() -> Path:
    return ROOT / "dist" / "release-manifest.json"


def save_manifest(data: dict[str, Any]) -> None:
    destination = manifest_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    data["generated_at"] = utc_now()
    destination.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_entry(entry: dict[str, Any], current_version: str) -> tuple[Path, list[str]]:
    failures: list[str] = []
    required = ("filename", "version", "platform", "architecture", "format", "sha256", "size", "status", "validated")
    if any(key not in entry for key in required):
        return ROOT / "dist", ["entry is incomplete"]
    if entry["version"] != current_version:
        failures.append("artifact version does not match VERSION")
    if entry["platform"] not in PLATFORMS:
        failures.append("artifact platform is unsupported")
    if entry["architecture"] not in ("x64", "arm64"):
        failures.append("artifact architecture is unsupported")
    if entry["format"] not in FORMATS:
        failures.append("artifact format is unsupported")
    if entry["status"] != "BUILT" or entry["validated"] is not True:
        failures.append("artifact is not marked BUILT and validated")
    expected = required_artifacts(current_version).get((entry["platform"], entry["filename"]))
    if expected is None:
        failures.append("artifact filename is not part of the release contract")
    elif (entry["architecture"], entry["format"]) != expected:
        failures.append("artifact architecture or format does not match the release contract")
    path = ROOT / "dist" / entry["platform"] / entry["filename"]
    if not path.is_file() or path.stat().st_size <= 0:
        failures.append("artifact does not exist or is empty")
    elif path.stat().st_size != entry["size"] or sha256(path) != entry["sha256"]:
        failures.append("artifact size or SHA-256 does not match manifest")
    return path, failures


def record(args: argparse.Namespace) -> int:
    artifact = Path(args.artifact).resolve()
    if not artifact.is_file() or artifact.stat().st_size <= 0:
        print("RELEASE MANIFEST FAILED: artifact does not exist or is empty", file=sys.stderr)
        return 2
    current_version = version()
    data = load_manifest(manifest_path(), current_version)
    entry = {
        "filename": artifact.name,
        "version": current_version,
        "platform": args.platform,
        "architecture": args.architecture,
        "format": args.format,
        "sha256": sha256(artifact),
        "size": artifact.stat().st_size,
        "built_at": utc_now(),
        "status": "BUILT",
        "validated": True,
    }
    data["artifacts"] = [
        item for item in data["artifacts"]
        if not (item.get("platform") == entry["platform"] and filename(item) == entry["filename"])
    ]
    data["artifacts"].append(entry)
    data["artifacts"].sort(key=lambda item: (item["platform"], item["filename"]))
    save_manifest(data)
    print(f"RELEASE MANIFEST RECORDED: {entry['filename']} sha256={entry['sha256']} size={entry['size']}")
    return 0


def provenance(args: argparse.Namespace) -> int:
    if args.platform not in PLATFORMS:
        print("RELEASE PROVENANCE FAILED: unsupported platform", file=sys.stderr)
        return 2
    current_version = version()
    target = ROOT / "dist" / "provenance" / f"{args.platform}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "platform": args.platform,
        "architecture": args.architecture,
        "version": current_version,
        "commit": args.commit,
        "source_integrity": args.source_integrity,
        "architecture_verified": args.architecture_verified,
        "runner_os": args.runner_os or runtime_platform.system(),
        "runner_architecture": args.runner_architecture or runtime_platform.machine(),
        "built_at": utc_now(),
        "toolchains": args.toolchain or [],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    data = load_manifest(manifest_path(), current_version)
    data["builds"] = [item for item in data["builds"] if item.get("platform") != args.platform]
    data["builds"].append(payload)
    data["builds"].sort(key=lambda item: item["platform"])
    save_manifest(data)
    print(f"RELEASE PROVENANCE RECORDED: {args.platform}")
    return 0


def locate_downloaded_artifact(source_root: Path, entry: dict[str, Any]) -> Path:
    expected_hash = entry.get("sha256")
    candidates = [path for path in source_root.rglob(filename(entry)) if path.is_file()]
    matching = [path for path in candidates if sha256(path) == expected_hash]
    if len(matching) != 1:
        raise ValueError(f"Downloaded artifact could not be uniquely matched: {filename(entry)}")
    return matching[0]


def assemble(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).resolve()
    if not source_root.is_dir():
        print("RELEASE ASSEMBLY FAILED: source root does not exist", file=sys.stderr)
        return 2
    current_version = version()
    target_manifest_paths = sorted(source_root.rglob("release-manifest.json"))
    if not target_manifest_paths:
        print("RELEASE ASSEMBLY FAILED: no target manifests were downloaded", file=sys.stderr)
        return 2
    data: dict[str, Any] = {
        "product": PRODUCT,
        "version": current_version,
        "generated_at": None,
        "artifacts": [],
        "builds": [],
    }
    destination_keys: set[tuple[str, str]] = set()
    for source_manifest in target_manifest_paths:
        source = load_manifest(source_manifest, current_version)
        for entry in source["artifacts"]:
            artifact = locate_downloaded_artifact(source_root, entry)
            key = (entry["platform"], filename(entry))
            if key in destination_keys:
                continue
            destination = ROOT / "dist" / entry["platform"] / filename(entry)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact, destination)
            copied = dict(entry)
            copied["filename"] = filename(copied)
            copied.pop("name", None)
            copied["version"] = current_version
            copied["size"] = destination.stat().st_size
            copied["sha256"] = sha256(destination)
            copied["status"] = "BUILT"
            copied["validated"] = True
            data["artifacts"].append(copied)
            destination_keys.add(key)
        for build in source.get("builds", []):
            if isinstance(build, dict) and build.get("platform") and build not in data["builds"]:
                data["builds"].append(build)
    data["artifacts"].sort(key=lambda item: (item["platform"], item["filename"]))
    data["builds"].sort(key=lambda item: item.get("platform", ""))
    save_manifest(data)
    return verify(argparse.Namespace(complete=True, security_scan=True))


def scan_entry(path: Path) -> bool:
    scanner = ROOT / "packaging" / "common" / "scan_artifact.py"
    result = subprocess.run(
        [sys.executable, str(scanner), str(path), "--report-names"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def complete_release_failures(data: dict[str, Any], current_version: str, security_scan: bool) -> list[str]:
    failures: list[str] = []
    expected = required_artifacts(current_version)
    actual = {(item.get("platform"), item.get("filename")) for item in data["artifacts"]}
    if actual != set(expected):
        failures.append("complete release does not contain exactly the required ten artifacts")
    builds = {item.get("platform"): item for item in data.get("builds", []) if isinstance(item, dict)}
    if set(builds) != set(PLATFORMS):
        failures.append("complete release does not have provenance for all six native targets")
    for platform_name in PLATFORMS:
        build = builds.get(platform_name, {})
        if build.get("version") != current_version or build.get("source_integrity") != "clean":
            failures.append(f"{platform_name} provenance is not source-clean")
        if build.get("architecture_verified") is not True:
            failures.append(f"{platform_name} provenance does not confirm architecture validation")
    if security_scan:
        for entry in data["artifacts"]:
            path = ROOT / "dist" / entry["platform"] / entry["filename"]
            if not scan_entry(path):
                failures.append(f"security scan failed for {entry['filename']}")
    return failures


def verify(args: argparse.Namespace) -> int:
    path = manifest_path()
    if not path.is_file():
        print("RELEASE MANIFEST FAILED: manifest does not exist", file=sys.stderr)
        return 2
    try:
        data = load_manifest(path, version())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"RELEASE MANIFEST FAILED: {type(exc).__name__}", file=sys.stderr)
        return 2
    failures = 0
    keys: set[tuple[str, str]] = set()
    for entry in data["artifacts"]:
        key = (entry.get("platform", ""), entry.get("filename", entry.get("name", "")))
        _, entry_failures = validate_entry(entry, version())
        if key in keys:
            entry_failures.append("duplicate artifact entry")
        keys.add(key)
        failures += len(entry_failures)
    if not data["artifacts"]:
        failures += 1
    if getattr(args, "complete", False):
        failures += len(complete_release_failures(data, version(), getattr(args, "security_scan", False)))
    if failures:
        print(f"RELEASE MANIFEST FAILED: {failures} validation issue(s) detected", file=sys.stderr)
        return 1
    print(f"RELEASE MANIFEST PASS: {len(data['artifacts'])} artifact(s) verified")
    return 0


def sha256s(args: argparse.Namespace) -> int:
    if verify(argparse.Namespace(complete=args.complete, security_scan=args.security_scan)) != 0:
        return 1
    data = load_manifest(manifest_path(), version())
    lines = [f"{entry['sha256']}  {entry['platform']}/{entry['filename']}" for entry in data["artifacts"]]
    destination = ROOT / "dist" / "SHA256SUMS.txt"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SHA256SUMS PASS: {len(lines)} artifact(s) recorded")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage genuine Automation Center release artifacts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    add = subcommands.add_parser("record")
    add.add_argument("--artifact", required=True)
    add.add_argument("--platform", required=True, choices=PLATFORMS)
    add.add_argument("--architecture", required=True, choices=("x64", "arm64"))
    add.add_argument("--format", required=True, choices=FORMATS)
    provenance_command = subcommands.add_parser("provenance")
    provenance_command.add_argument("--platform", required=True, choices=PLATFORMS)
    provenance_command.add_argument("--architecture", required=True, choices=("x64", "arm64"))
    provenance_command.add_argument("--commit", required=True)
    provenance_command.add_argument("--source-integrity", choices=("clean", "dirty"), default="clean")
    provenance_command.add_argument("--architecture-verified", action="store_true")
    provenance_command.add_argument("--runner-os")
    provenance_command.add_argument("--runner-architecture")
    provenance_command.add_argument("--toolchain", action="append")
    assemble_command = subcommands.add_parser("assemble")
    assemble_command.add_argument("--source-root", required=True)
    verify_command = subcommands.add_parser("verify")
    verify_command.add_argument("--complete", action="store_true")
    verify_command.add_argument("--security-scan", action="store_true")
    sums_command = subcommands.add_parser("sha256s")
    sums_command.add_argument("--complete", action="store_true")
    sums_command.add_argument("--security-scan", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "record":
            return record(args)
        if args.command == "provenance":
            return provenance(args)
        if args.command == "assemble":
            return assemble(args)
        if args.command == "sha256s":
            return sha256s(args)
        return verify(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"RELEASE MANIFEST FAILED: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
