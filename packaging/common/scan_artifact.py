#!/usr/bin/env python3
"""Portable artifact scanner that reports counts only, never matching values."""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

PATTERNS = (
    re.compile(r"-----BEGIN ([A-Z ]+)?PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"\b(?:[0-9]{6,12}:[A-Za-z0-9_-]{30,})\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"),
)
TEXT_EXTENSIONS = {".env", ".txt", ".json", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".py", ".ps1", ".sh", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".md", ".iss", ".xml"}
FORBIDDEN_NAMES = {".env", "runtime.env", "id_rsa", "id_ed25519", ".n8n"}


def is_problem(name: str, content: str | None = None) -> bool:
    normalized = name.replace("\\", "/")
    if Path(normalized).name.lower() in FORBIDDEN_NAMES or "/.n8n/" in f"/{normalized}/":
        return True
    if content is None or Path(normalized).suffix.lower() not in TEXT_EXTENSIONS:
        return False
    return any(pattern.search(content) for pattern in PATTERNS)


def scan_directory(root: Path) -> list[str]:
    findings: list[str] = []
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        name = str(entry.relative_to(root))
        try:
            content = entry.read_text(encoding="utf-8") if entry.suffix.lower() in TEXT_EXTENSIONS else None
        except (OSError, UnicodeDecodeError):
            findings.append(name)
            continue
        if is_problem(name, content):
            findings.append(name)
    return findings


def scan_binary(path: Path) -> list[str]:
    """Check raw bytes of a final executable/archive for high-confidence literal secrets."""
    try:
        content = path.read_bytes().decode("latin-1")
    except OSError:
        return [path.name]
    return [path.name] if (is_problem(path.name, content) or any(pattern.search(content) for pattern in PATTERNS)) else []


def scan_zip(path: Path) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            content = None
            if Path(entry.filename).suffix.lower() in TEXT_EXTENSIONS:
                try:
                    content = archive.read(entry).decode("utf-8")
                except (UnicodeDecodeError, OSError):
                    findings.append(entry.filename)
                    continue
            if is_problem(entry.filename, content):
                findings.append(entry.filename)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a staging directory or ZIP archive for packaged private data")
    parser.add_argument("path", type=Path)
    parser.add_argument("--report-names", action="store_true", help="Print only affected relative paths, never matching values")
    args = parser.parse_args()
    target = args.path.resolve()
    if target.is_dir():
        findings = scan_directory(target)
    elif target.is_file() and target.suffix.lower() == ".zip":
        findings = scan_zip(target)
    elif target.is_file():
        findings = scan_binary(target)
    else:
        print("SECURITY SCAN FAILED: artifact does not exist", file=sys.stderr)
        return 2
    if findings:
        if args.report_names:
            for name in sorted(set(findings)):
                print(f"AFFECTED_PATH: {name}", file=sys.stderr)
        print(f"SECURITY SCAN FAILED: {len(findings)} potential secret or private-data issue(s) detected. No matching values were printed.", file=sys.stderr)
        return 1
    print("SECURITY SCAN PASS: no forbidden private files or high-confidence secret patterns were detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
