from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.database import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class ActionType(str, enum.Enum):
    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_CAMPAIGN = "enable_campaign"
    ADJUST_BUDGET = "adjust_budget"
    ADJUST_BID = "adjust_bid"
    DUPLICATE_ADSET = "duplicate_adset"


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Tipo de ação
    action_type = Column(String(50), nullable=False)

    # Dados da ação (JSON serializado como texto)
    payload = Column(Text, nullable=False)  # JSON: {campaign_id, new_budget, ...}

    # Contexto Meta
    account_id = Column(String(100), nullable=True)
    campaign_id = Column(String(100), nullable=True)
    campaign_name = Column(String(200), nullable=True)
    adset_id = Column(String(100), nullable=True)

    # Justificativa da IA
    ai_reasoning = Column(Text, nullable=False)

    # Status e controle
    status = Column(String(20), default=ApprovalStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    decided_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_result = Column(Text, nullable=True)

    user = relationship("User", back_populates="approvals")
