from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Any
import json


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str = "postgresql://postgres:senha@db:5432/gestor_trafego"

    # Meta / Facebook
    META_APP_ID: str = "1008535358112208"
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = "https://apitrafego.ruch.com.br/api/auth/callback"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Segurança
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    # CORS
    CORS_ORIGINS: List[str] = ["https://trafego.ruch.com.br"]

    # URL do frontend (para redirect pós-OAuth)
    FRONTEND_URL: str = "https://trafego.ruch.com.br"

    # Ambiente
    ENVIRONMENT: str = "development"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: Any) -> Any:
        # SQLAlchemy 2.x exige postgresql://, não postgres://
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        if not v:
            return ["https://trafego.ruch.com.br"]
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
