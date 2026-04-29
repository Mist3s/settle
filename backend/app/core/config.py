"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "Settle"
    debug: bool = False

    # --- Database ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "settle"
    postgres_password: str = "settle"
    postgres_db: str = "settle"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- JWT ---
    jwt_private_key_path: str = "keys/jwt-private.pem"
    jwt_public_key_path: str = "keys/jwt-public.pem"
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # --- Seed user ---
    seed_user_email: str = "admin@settle.local"
    seed_user_password: str = "changeme"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
