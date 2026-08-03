"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "FantasyFootball"
    db_user: str = "sa"
    db_password: str = ""
    db_driver: str = "ODBC Driver 18 for SQL Server"

    # Google Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-preview"

    # App
    app_env: str = "development"

    @property
    def database_url(self) -> str:
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
