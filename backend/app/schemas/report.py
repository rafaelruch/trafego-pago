from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ReportFilter(BaseModel):
    account_ids: Optional[List[str]] = None
    campaign_ids: Optional[List[str]] = None
    date_start: Optional[str] = None
    date_stop: Optional[str] = None
    date_preset: str = "last_7d"


class CampaignReportRow(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    objective: Optional[str]
    impressions: int
    clicks: int
    spend: float
    reach: int
    cpm: float
    cpc: float
    ctr: float
    conversions: int
    cost_per_conversion: float
    roas: float
    account_name: str


class ReportSummary(BaseModel):
    period: str
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    average_cpc: float
    average_roas: float
    average_ctr: float
    campaigns: List[CampaignReportRow]
    generated_at: datetime


class N8NReportResponse(BaseModel):
    """Resposta formatada para N8N."""
    success: bool
    data: ReportSummary
    metadata: dict
