import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/research_engine"
    )
    GOOGLE_API_KEY: str = Field(default="")
    TAVILY_API_KEY: str = Field(default="")
    LOG_LEVEL: str = Field(default="INFO")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")

settings = Settings()
