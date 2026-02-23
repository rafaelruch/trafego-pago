from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter()

DEFAULT_MODEL = "gemini-2.5-flash"

AVAILABLE_MODELS = [
    # Gemini 3 (mais recentes — fev/2026)
    {"id": "gemini-3.1-pro-preview",  "label": "Gemini 3.1 Pro Preview (mais avançado — raciocínio complexo)"},
    {"id": "gemini-3-pro-preview",    "label": "Gemini 3 Pro Preview (raciocínio + multimodal)"},
    {"id": "gemini-3-flash-preview",  "label": "Gemini 3 Flash Preview (frontier a menor custo)"},
    # Gemini 2.5
    {"id": "gemini-2.5-pro",          "label": "Gemini 2.5 Pro (tarefas complexas + deep reasoning)"},
    {"id": "gemini-2.5-flash",        "label": "Gemini 2.5 Flash (padrão — melhor custo-benefício)"},
    {"id": "gemini-2.5-flash-lite",   "label": "Gemini 2.5 Flash Lite (mais rápido e econômico)"},
    # Gemini 2.0 (descontinuado em 31/03/2026)
    {"id": DEFAULT_MODEL,        "label": "Gemini 2.0 Flash (legado — descontinuado em mar/2026)"},
]


class AISettingsResponse(BaseModel):
    ai_model: str
    has_custom_key: bool
    available_models: list


class AISettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    ai_model: Optional[str] = None


@router.get("/ai")
def get_ai_settings(
    current_user: User = Depends(get_current_user),
):
    return AISettingsResponse(
        ai_model=current_user.ai_model or DEFAULT_MODEL,
        has_custom_key=bool(current_user.gemini_api_key),
        available_models=AVAILABLE_MODELS,
    )


@router.put("/ai")
def update_ai_settings(
    data: AISettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.gemini_api_key is not None:
        stripped = data.gemini_api_key.strip()
        current_user.gemini_api_key = stripped if stripped else None

    if data.ai_model is not None:
        stripped = data.ai_model.strip()
        current_user.ai_model = stripped if stripped else DEFAULT_MODEL

    db.commit()
    db.refresh(current_user)

    return AISettingsResponse(
        ai_model=current_user.ai_model or DEFAULT_MODEL,
        has_custom_key=bool(current_user.gemini_api_key),
        available_models=AVAILABLE_MODELS,
    )
