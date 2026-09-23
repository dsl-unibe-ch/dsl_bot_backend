# Copyright (c) 2026, University of Bern, Data Science Lab
"""Configuration settings for the application."""

import os

from pydantic import AliasChoices, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings

env = os.environ["ENV"]
if not env and env not in ["dev", "prod"]:
    error_message = "ENV environment variable must be either 'dev' or 'prod'."
    raise RuntimeError(error_message)


class Settings(BaseSettings):
    """Configuration settings for the chatbot and RESTAPI."""

    ENV: str

    BACKEND_URL: str | None = None
    DOCS_URL: str | None = None
    REDOC_URL: str | None = None
    APP_TITLE: str
    APP_DESCRIPTION: str
    ALLOWED_METHODS: list[str]
    ALLOWED_HEADERS: list[str]
    ALLOWED_CREDENTIALS: bool
    AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING: str

    AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY: str
    AZURE_OPENAI_PRIMARY_KEY: str
    AZURE_SEARCH_ENDPOINT: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT: str
    AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION: str
    AZURE_OPENAI_CHAT_DEPLOYMENT: str
    AZURE_OPENAI_CHAT_API_VERSION: str
    AZURE_OPENAI_VECTORIZER_ENDPOINT: str

    AZURE_CONTAINER_REGISTRY_LOGIN_SERVER: str | None = None

    AZURE_CONTAINER_STORAGE_NAME: str | None = None
    AZURE_CONTAINER_STORAGE_SECRETS_NAME: str | None = None

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str

    FALLBACK_CUSTOMER_ID: str = Field(
        validation_alias=AliasChoices("FALLBACK_CUSTOMER_ID")
    )

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str | None = None
    REDIS_SESSION_TTL_SECONDS: int
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: str

    LANGFUSE_API_KEY: str | None = None
    LANGFUSE_PROJECT: str | None = None
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_HOST: str | None = None

    @model_validator(mode="after")
    def normalize_urls(self) -> Settings:
        """Normalize URL fields to be None if they are empty or 'None'."""
        for attr in ["DOCS_URL", "REDOC_URL"]:
            value = getattr(self, attr)
            if value in ["", "None"]:
                setattr(self, attr, None)
        return self

    model_config = ConfigDict(env_file=f".env.{env}", extra="ignore")


settings = Settings()
