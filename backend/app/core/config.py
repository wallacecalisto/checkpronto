from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — usado para achar o .env independentemente de onde o processo foi
# iniciado (uvicorn, alembic, pytest, etc. podem ter cwd diferentes).
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    test_database_url: str | None = None

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _normalize_postgres_driver(cls, value: str | None) -> str | None:
        if value is None:
            return value
        for bare_scheme in ("postgres://", "postgresql://"):
            if value.startswith(bare_scheme):
                return "postgresql+psycopg://" + value[len(bare_scheme) :]
        return value

    # Lista de origens (separadas por vírgula) autorizadas a chamar a API pelo navegador.
    cors_origins: str = "http://localhost:5173"

    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_public_base_url: str | None = None

    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    operational_refresh_token_expire_days: int = 365
    # Cookie do refresh token só deve ir com "Secure" quando a API estiver atrás
    # de HTTPS. Em desenvolvimento local (http://localhost) fica False.
    cookie_secure: bool = True

    cookie_samesite: Literal["strict", "lax", "none"] = "strict"

    @model_validator(mode="after")
    def _validate_samesite_none_requires_secure(self) -> "Settings":
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SAMESITE=none exige COOKIE_SECURE=true — navegadores recusam "
                "um cookie SameSite=None que não seja Secure."
            )
        return self

    # Usados só pelo script backend/scripts/seed_master_user.py, para criar o
    # primeiro usuário MASTER. Nunca usados pela aplicação em si.
    master_user_name: str = "Administrador Master"
    master_user_email: str | None = None
    master_user_password: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
