"""Regression tests for private runtime configuration in the packaging service manager."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "packaging" / "common" / "service_manager.py"
SPEC = importlib.util.spec_from_file_location("phase217_service_manager", MODULE_PATH)
assert SPEC and SPEC.loader
service_manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service_manager)


def test_runtime_initialization_does_not_invent_n8n_public_api_key(tmp_path):
    """A random runtime value is never treated as an n8n Public API credential."""
    env_file = service_manager.write_runtime_env(tmp_path, 3999)

    assert env_file.is_file()
    assert service_manager._runtime_env_value(tmp_path, "N8N_API_KEY") is None
    assert "N8N_API_KEY=" not in env_file.read_text(encoding="utf-8")


def test_configure_n8n_api_key_uses_hidden_prompt_and_private_runtime_file(tmp_path, monkeypatch):
    """The command stores a supplied key without putting it in its result payload."""
    monkeypatch.setattr(service_manager.getpass, "getpass", lambda _prompt: "test-public-api-key")

    result = service_manager.configure_n8n_api_key(tmp_path)

    assert result == {
        "success": True,
        "message": "n8n Public API key stored in private runtime configuration; restart local services to apply it",
    }
    assert service_manager._runtime_env_value(tmp_path, "N8N_API_KEY") == "test-public-api-key"
    assert "test-public-api-key" not in str(result)
