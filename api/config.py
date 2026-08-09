"""Application configuration loaded from environment variables.

Supports two database backends:
- SQL Server (development): uses individual DB_* variables
- Postgres/Neon (production): uses DATABASE_URL
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Production database URL (Neon Postgres)
    # If set, this takes priority over SQL Server settings
    database_url: str = ""

    # SQL Server (development)
    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "FantasyFootball"
    db_user: str = "sa"
    db_password: str = ""
    db_driver: str = "ODBC Driver 18 for SQL Server"

    # Google Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # App
    app_env: str = "development"

    @property
    def effective_database_url(self) -> str:
        """Return the appropriate database URL based on environment.

        If DATABASE_URL is set (production/Neon), use it.
        Otherwise, build a SQL Server connection string (development).
        """
        if self.database_url:
            return self.database_url

        import urllib.parse
        params = urllib.parse.quote_plus(
            f"DRIVER={{{self.db_driver}}};"
            f"SERVER={self.db_server},{self.db_port};"
            f"DATABASE={self.db_name};"
            f"UID={self.db_user};"
            f"PWD={self.db_password};"
            f"TrustServerCertificate=yes;"
        )
        return f"mssql+pyodbc:///?odbc_connect={params}"

    @property
    def gemini_url(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.gemini_model}:generateContent"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
