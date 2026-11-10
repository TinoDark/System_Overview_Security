from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://localhost/soc_mvp"
    mock_auth_enabled: bool = True
    responses_enabled: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate_runtime(self) -> None:
        if self.app_env != "test" and not self.database_url.startswith(
            ("postgresql://", "postgresql+psycopg://")
        ):
            raise RuntimeError("PostgreSQL is required outside tests")
        if self.mock_auth_enabled and self.app_env not in ("development", "test"):
            raise RuntimeError("Mock authentication is only allowed in development")


settings = Settings()
