from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return user


def get_n8n_user(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db),
):
    """Autenticação via API Key para N8N e integrações externas."""
    from app.models.user import ApiKey

    if not api_key:
        raise HTTPException(status_code=401, detail="API Key necessária (X-API-Key header)")

    key_record = (
        db.query(ApiKey)
        .filter(ApiKey.key == api_key, ApiKey.is_active == True)
        .first()
    )
    if not key_record:
        raise HTTPException(status_code=401, detail="API Key inválida")

    key_record.last_used_at = datetime.utcnow()
    db.commit()

    return key_record.user
