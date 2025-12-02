"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture
def clean_env(monkeypatch):
    """Fixture to provide a clean environment for config testing."""
    # Clear relevant environment variables
    env_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "APP_ENV",
        "DEBUG",
        "CORS_ORIGINS",
        "TRUSTED_HOSTS",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch
