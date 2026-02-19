from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CampaignInsight(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    objective: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    reach: int = 0
    cpm: float = 0.0
    cpc: float = 0.0
    ctr: float = 0.0
    conversions: int = 0
    cost_per_conversion: float = 0.0
    roas: float = 0.0
    frequency: float = 0.0
    date_start: Optional[str] = None
    date_stop: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None


class AdSetInsight(BaseModel):
    adset_id: str
    adset_name: str
    campaign_id: str
    status: str
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    cpm: float = 0.0
    cpc: float = 0.0
    ctr: float = 0.0
    conversions: int = 0
    roas: float = 0.0


class BusinessManagerInfo(BaseModel):
    id: str
    name: str
    ad_accounts: List[str] = []


class AccountSummary(BaseModel):
    account_id: str
    account_name: str
    currency: str = "BRL"
    total_spend: float = 0.0
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    average_cpc: float = 0.0
    average_roas: float = 0.0
    active_campaigns: int = 0
    paused_campaigns: int = 0
