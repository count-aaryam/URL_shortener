from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    APP_BASE_URL: str = "http://localhost:8000/api"
    APP_ENV: str = "development"
    SHORT_CODE_LENGTH: int = 7

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Future phases
    OPENAI_API_KEY: str = ""


settings = Settings()