"""Regression tests for environment-backed backend settings."""

from app.core.config import Settings


def test_settings_read_n8n_api_key_from_environment(monkeypatch):
    """Docker-injected Public API credentials must reach the n8n client."""
    monkeypatch.setenv("N8N_API_KEY", "test-public-api-key")
    monkeypatch.setenv("N8N_API_URL", "http://test-n8n:5678")

    settings = Settings()

    assert settings.N8N_API_KEY == "test-public-api-key"
    assert settings.N8N_API_URL == "http://test-n8n:5678"
