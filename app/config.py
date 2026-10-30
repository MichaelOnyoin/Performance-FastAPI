from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HLB Jim Roberts Performance Hub"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./data/performance.db"
    access_token_minutes: int = 480
    frontend_url: str = "https://hlb.onyoin.com"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://performance-react-nine.vercel.app,https://hlb.onyoin.com,https://jrc-performance.vercel.app,https://jrc.onyoin.com"
    smtp_host: str|None = None
    smtp_port: int = 587
    smtp_username: str|None = None
    smtp_password: str|None = None
    smtp_from_email: str|None = None
    smtp_use_tls: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
