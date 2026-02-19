from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets
from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    meta_user_id = Column(String(100), unique=True, index=True)
    name = Column(String(200))
    email = Column(String(200), nullable=True)
    # Token de acesso longo do Meta (60 dias)
    meta_access_token = Column(Text, nullable=True)
    meta_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approvals = relationship("Approval", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    business_managers = relationship("BusinessManager", back_populates="user")


class BusinessManager(Base):
    __tablename__ = "business_managers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bm_id = Column(String(100), index=True)
    name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="business_managers")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100))  # ex: "N8N Producao"
    key = Column(String(64), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_key() -> str:
        return secrets.token_urlsafe(48)
