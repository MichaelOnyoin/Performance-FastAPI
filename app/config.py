from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    app_name: str = "HLB Performance Hub"
    secret_key: str = "dev-only-change-me"
    # database_url: str = "sqlite:///./data/performance.db"
    database_url: str = "postgresql://neondb_owner:npg_KgAM5tzUa4Go@ep-nameless-pine-b5v7srq8-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    access_token_minutes: int = 480
    frontend_url: str = "https://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://performance-react-nine.vercel.app,https://hlb.onyoin.com,https://jrc-performance.vercel.app,https://jrc.onyoin.com,'*',https://scorecard.jimrobertsconsulting.com"
    # smtp_host: str|None = os.environ.get("SMTP_HOST")
    # smtp_port: int = 465
    # smtp_username: str|None = os.environ.get("SMTP_USERNAME")
    # smtp_password: str|None = os.environ.get("SMTP_PASSWORD")
    # smtp_from_email: str|None = os.environ.get("SMTP_FROM_EMAIL")
    smtp_host: str = os.environ.get("SMTP_HOST")
    smtp_port: int = 465
    smtp_username: str = os.environ.get("SMTP_USERNAME")
    smtp_password: str = os.environ.get("SMTP_PASSWORD")
    smtp_from_email: str = os.environ.get("SMTP_FROM_EMAIL")
    smtp_use_tls: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
