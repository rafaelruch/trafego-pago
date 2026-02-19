from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class ApprovalOut(BaseModel):
    id: int
    action_type: str
    payload: str
    account_id: Optional[str]
    campaign_id: Optional[str]
    campaign_name: Optional[str]
    adset_id: Optional[str]
    ai_reasoning: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime]
    executed_at: Optional[datetime]
    execution_result: Optional[str]

    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    notes: Optional[str] = None  # Nota opcional ao aprovar/rejeitar


class AIAnalysisRequest(BaseModel):
    account_ids: Optional[list[str]] = None  # None = todas as contas
    date_preset: str = "last_7d"  # last_7d, last_30d, this_month, last_month
    custom_prompt: Optional[str] = None  # Instrução extra ao Claude


class AIChatMessage(BaseModel):
    message: str
    account_ids: Optional[list[str]] = None
