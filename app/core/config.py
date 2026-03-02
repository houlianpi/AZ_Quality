# app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "quality_platform"

    # AAD Authentication
    AAD_CLIENT_ID: str = ""
    AAD_TENANT_ID: str = ""

    @property
    def database_url(self) -> str:
        """Return MySQL connection URL for SQLAlchemy."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def aad_issuer(self) -> str:
        """Return AAD token issuer URL."""
        return f"https://login.microsoftonline.com/{self.AAD_TENANT_ID}/v2.0"

    @property
    def aad_jwks_url(self) -> str:
        """Return AAD JWKS (public keys) URL."""
        return f"https://login.microsoftonline.com/{self.AAD_TENANT_ID}/discovery/v2.0/keys"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
