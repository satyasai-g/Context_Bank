import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Context Bank"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "b91a7834e9e0487595db23668a1d7f1d48c0356e7e4362145e14c1962dc213e4"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./context_bank.db"

    # Backend
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://127.0.0.1:8000"

    # Streamlit
    STREAMLIT_SERVER_PORT: int = 8501
    STREAMLIT_SERVER_ADDRESS: str = "127.0.0.1"

    # AI & Embeddings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_PROVIDER: str = "tfidf"  # "tfidf", "gemini", or "sentence_transformers"
    EMBEDDING_DIM: int = 384

    # Seed Admin User
    DEFAULT_USER_EMAIL: str = "dev@contextbank.local"
    DEFAULT_USER_PASSWORD: str = "contextbank_dev_password"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())


settings = Settings()
