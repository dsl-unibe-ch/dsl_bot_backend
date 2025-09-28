"""Configuration settings for the application."""

import os

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

env = os.environ["ENV"]
if not env and env not in ["dev", "prod"]:
    error_message = "ENV environment variable must be either 'dev' or 'prod'."
    raise RuntimeError(error_message)


class Settings(BaseSettings):
    """Configuration settings for the chatbot and RESTAPI."""

    ENV: str

    FRONTEND_URL: str | None = None
    BACKEND_URL: str | None = None
    DOCS_URL: str | None = None
    REDOC_URL: str | None = None
    APP_TITLE: str
    APP_DESCRIPTION: str
    ALLOWED_METHODS: list[str]
    ALLOWED_HEADERS: list[str]
    ALLOWED_CREDENTIALS: bool
    AZURE_STORAGE_CONNECTION_STRING: str
    CHAT_HISTORY_TABLE_NAME: str
    FEEDBACK_TABLE_NAME: str

    AZURE_AI_SEARCH_API_KEY: str
    AZURE_SEARCH_ENDPOINT: str
    AZURE_AI_SEARCH_INDEX_NAME: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT: str
    AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION: str
    AZURE_OPENAI_CHAT_DEPLOYMENT: str
    AZURE_OPENAI_CHAT_API_VERSION: str

    LANGSMITH_TRACING: str
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    AZURE_OPENAI_CHAT_KEY: str

    AZURE_CLIENT_SECRET: str
    AZURE_CLIENT_ID: str
    AZURE_TENANT_ID: str

    @model_validator(mode="after")
    def normalize_urls(self) -> "Settings":
        """Normalize URL fields to be None if they are empty or 'None'."""
        for attr in ["DOCS_URL", "REDOC_URL"]:
            value = getattr(self, attr)
            if value in ["", "None"]:
                setattr(self, attr, None)
        return self

    model_config = ConfigDict(env_file=f".env.{env}")


settings = Settings()
