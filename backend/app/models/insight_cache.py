from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from datetime import datetime
from app.models.database import Base


class InsightCache(Base):
    """Cache de métricas para evitar muitas chamadas à API do Meta."""
    __tablename__ = "insight_cache"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(100), index=True)
    campaign_id = Column(String(100), index=True, nullable=True)
    adset_id = Column(String(100), index=True, nullable=True)
    date_start = Column(String(20))
    date_stop = Column(String(20))
    data = Column(Text)  # JSON com as métricas
    cached_at = Column(DateTime, default=datetime.utcnow)
    # Cache expira em 30 minutos por padrão
    expires_at = Column(DateTime)
