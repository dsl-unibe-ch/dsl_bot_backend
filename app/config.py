"""Configuration settings for the application."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the chatbot and RESTAPI."""

    BASE_URL: str
    DOCS_URL: str = None
    REDOC_URL: str = None
    APP_TITLE: str
    APP_DESCRIPTION: str
    ALLOWED_METHODS: str
    ALLOWED_HEADERS: str
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

    class Config:
        """Configuration for the settings."""

        env_file = ".env"


settings = Settings()
