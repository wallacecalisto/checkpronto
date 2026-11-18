
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_normalizes_bare_postgres_scheme_to_psycopg_driver() -> None:
    settings = Settings(database_url="postgres://user:pass@host:5432/db", secret_key="x")
    assert settings.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_normalizes_bare_postgresql_scheme_to_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:pass@host:5432/db", secret_key="x")
    assert settings.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_leaves_url_with_explicit_driver_untouched() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pass@host:5432/db", secret_key="x")
    assert settings.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_normalizes_test_database_url_too() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@host:5432/db",
        test_database_url="postgres://user:pass@host:5432/db_test",
        secret_key="x",
    )
    assert settings.test_database_url == "postgresql+psycopg://user:pass@host:5432/db_test"


def test_test_database_url_none_stays_none() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@host:5432/db",
        test_database_url=None,
        secret_key="x",
    )
    assert settings.test_database_url is None


# --- cookie_samesite (correção do bug real de deploy: frontend e backend em
# domínios diferentes, ex.: Cloudflare Pages + Render) ---------------------


def test_cookie_samesite_defaults_to_strict() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pass@host:5432/db", secret_key="x")
    assert settings.cookie_samesite == "strict"


def test_cookie_samesite_none_allowed_when_secure_is_true() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@host:5432/db",
        secret_key="x",
        cookie_samesite="none",
        cookie_secure=True,
    )
    assert settings.cookie_samesite == "none"


def test_cookie_samesite_none_rejected_when_secure_is_false() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SAMESITE=none exige COOKIE_SECURE=true"):
        Settings(
            database_url="postgresql+psycopg://user:pass@host:5432/db",
            secret_key="x",
            cookie_samesite="none",
            cookie_secure=False,
        )


def test_cookie_samesite_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://user:pass@host:5432/db",
            secret_key="x",
            cookie_samesite="banana",
        )
