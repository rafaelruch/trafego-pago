from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter()

AVAILABLE_MODELS = [
    {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (padrão — rápido e eficiente)"},
    {"id": "gemini-2.0-flash-thinking-exp", "label": "Gemini 2.0 Flash Thinking (raciocínio avançado)"},
    {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro (contexto longo)"},
    {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash (mais econômico)"},
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
        ai_model=current_user.ai_model or "gemini-2.0-flash",
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
        current_user.ai_model = stripped if stripped else "gemini-2.0-flash"

    db.commit()
    db.refresh(current_user)

    return AISettingsResponse(
        ai_model=current_user.ai_model or "gemini-2.0-flash",
        has_custom_key=bool(current_user.gemini_api_key),
        available_models=AVAILABLE_MODELS,
    )
