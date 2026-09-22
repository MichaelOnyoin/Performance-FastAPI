from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HLB Jim Roberts Performance Hub"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./data/performance.db"
    access_token_minutes: int = 480
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
