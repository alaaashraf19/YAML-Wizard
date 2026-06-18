"""
Application configuration — loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GitHub & GitLab
    github_token: str = ""
    gitlab_token: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    default_agent_model: str = "qwen2.5:3b"

    # FastAPI
    app_title: str = "YAML Wizard — Repo Context Agent"
    debug: bool = False

    # Existing fields from the project
    secret_key: str = ""
    access_token_expire_minutes: int = 30
    database_url: str = ""


settings = Settings()