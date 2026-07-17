"""Tests for typed ChoreTracker configuration."""

from app.core.config import Settings, get_settings


def test_default_settings_use_non_standard_ports() -> None:
    """Default host ports should avoid common development-service ports."""

    settings = Settings(_env_file=None)

    assert settings.api_port == 8110
    assert settings.postgres_host_port == 55410
    assert settings.frontend_port == 51810


def test_environment_values_override_defaults(monkeypatch) -> None:
    """Environment variables should override configured defaults."""

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("API_PORT", "18110")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.api_port == 18110


def test_database_url_uses_postgresql_psycopg_driver() -> None:
    """The generated connection URL should use PostgreSQL and psycopg."""

    settings = Settings(
        _env_file=None,
        postgres_db="example_db",
        postgres_user="example_user",
        postgres_password="example password",
        postgres_host="localhost",
        postgres_host_port=55410,
    )

    assert settings.database_url == (
        "postgresql+psycopg://example_user:example+password@localhost:55410/example_db"
    )


def test_get_settings_returns_cached_instance() -> None:
    """Application settings should be reused within one process."""

    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
