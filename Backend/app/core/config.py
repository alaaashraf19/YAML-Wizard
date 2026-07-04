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
    app_title: str = "YAML Wizard"
    debug: bool = False

    # Existing fields from the project
    secret_key: str = ""
    access_token_expire_minutes: int = 604800 #60*60*24*7 => 7days
    database_url: str = ""

    ###############cloudinary config for avatar uploading########################
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Finetuned CI/CD YAML model
    finetuned_base_url: str = "http://localhost:11434/v1"
    finetuned_model_name: str = "yaml-wizard-ci"
    finetuned_api_key: str = "ollama"
    finetuned_timeout_sec: float = 120.0

settings = Settings()