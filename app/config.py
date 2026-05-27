from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    APP_BASE_URL: str = "http://localhost:8000"
    APP_ENV: str = "development"
    SHORT_CODE_LENGTH: int = 7

    # Future phases
    JWT_SECRET: str = ""
    OPENAI_API_KEY: str = ""


settings = Settings()