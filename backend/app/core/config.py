from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str = "postgresql://postgres:senha@db:5432/gestor_trafego"

    # Meta / Facebook
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Segurança
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3002"]

    # URL do frontend (para redirect pós-OAuth)
    FRONTEND_URL: str = "http://localhost:3002"

    # Ambiente
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
