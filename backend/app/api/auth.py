"""
Autenticação via Meta OAuth 2.0.
Fluxo: /api/auth/meta → usuário autoriza no Meta → /api/auth/callback → JWT gerado.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.models.database import get_db
from app.models.user import User, ApiKey
from app.services.meta_service import MetaService

router = APIRouter()

META_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
META_SCOPES = "business_management,ads_management,ads_read,email"


@router.get("/meta", summary="Iniciar login com Meta")
def start_meta_oauth():
    """Redireciona o usuário para a tela de autorização do Meta."""
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": META_SCOPES,
        "response_type": "code",
        "state": "gestor_trafego",  # Em produção, use CSRF token
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{META_AUTH_URL}?{query}")


@router.get("/callback", summary="Callback OAuth do Meta")
def meta_oauth_callback(code: str, state: str = None, db: Session = Depends(get_db)):
    """Recebe o código do Meta, troca por token e cria/atualiza o usuário."""
    # Troca código por token curto
    async_client = httpx.Client()
    token_response = async_client.get(
        META_TOKEN_URL,
        params={
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.META_REDIRECT_URI,
            "code": code,
        },
    )
    token_data = token_response.json()
    if "error" in token_data:
        raise HTTPException(400, f"Erro OAuth: {token_data['error'].get('message')}")

    short_token = token_data["access_token"]

    # Troca por token longo (60 dias)
    meta = MetaService(access_token=short_token)
    long_token_data = meta.exchange_long_lived_token(short_token)
    long_token = long_token_data["access_token"]
    expires_in = long_token_data.get("expires_in", 5183944)

    # Busca info do usuário no Meta
    meta_long = MetaService(access_token=long_token)
    user_info = meta_long.get_user_info()

    # Cria ou atualiza usuário no banco
    user = db.query(User).filter(User.meta_user_id == user_info["id"]).first()
    if not user:
        user = User(
            meta_user_id=user_info["id"],
            name=user_info["name"],
            email=user_info.get("email"),
        )
        db.add(user)

    user.meta_access_token = long_token
    user.meta_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    user.name = user_info["name"]
    user.email = user_info.get("email")
    db.commit()
    db.refresh(user)

    # Gera JWT da aplicação
    jwt_token = create_access_token(data={"sub": str(user.id)})

    # Redireciona para o frontend com o token
    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    return RedirectResponse(url=f"{frontend_url}/auth/callback?token={jwt_token}")


@router.get("/me", summary="Dados do usuário autenticado")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna dados do usuário logado."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "meta_token_expires_at": current_user.meta_token_expires_at,
        "has_meta_token": bool(current_user.meta_access_token),
    }


# === API KEYS (para N8N) ===

@router.get("/api-keys", summary="Listar API Keys")
def list_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista as API Keys do usuário (para N8N e integrações)."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_preview": k.key[:8] + "...",
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used_at": k.last_used_at,
        }
        for k in keys
    ]


@router.post("/api-keys", summary="Criar API Key")
def create_api_key(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cria uma nova API Key para uso com N8N ou outras integrações."""
    key_value = ApiKey.generate_key()
    api_key = ApiKey(user_id=current_user.id, name=name, key=key_value)
    db.add(api_key)
    db.commit()
    return {
        "id": api_key.id,
        "name": name,
        "key": key_value,  # Mostrado apenas uma vez!
        "message": "Guarde esta chave — ela não será exibida novamente.",
    }


@router.delete("/api-keys/{key_id}", summary="Revogar API Key")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "API Key não encontrada")
    key.is_active = False
    db.commit()
    return {"message": "API Key revogada com sucesso"}
