"""
Wrapper do Meta Marketing API usando o facebook-business SDK.
Gerencia Business Managers, contas de anúncio, campanhas e insights.
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User as FBUser
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

from app.core.config import settings


INSIGHT_FIELDS = [
    "impressions",
    "clicks",
    "spend",
    "reach",
    "cpm",
    "cpc",
    "ctr",
    "conversions",
    "cost_per_conversion",
    "purchase_roas",
    "frequency",
    "actions",
    "action_values",
]

DATE_PRESETS = {
    "last_7d": "last_7_d",
    "last_30d": "last_30_d",
    "this_month": "this_month",
    "last_month": "last_month",
    "last_90d": "last_90_d",
}


class MetaService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        FacebookAdsApi.init(
            app_id=settings.META_APP_ID,
            app_secret=settings.META_APP_SECRET,
            access_token=access_token,
        )

    def get_business_managers(self) -> List[Dict]:
        """Retorna todos os Business Managers acessíveis pelo usuário."""
        try:
            me = FBUser(fbid="me")
            businesses = me.get_businesses(fields=["id", "name"])
            return [{"id": b["id"], "name": b["name"]} for b in businesses]
        except Exception as e:
            raise ValueError(f"Erro ao buscar Business Managers: {str(e)}")

    def get_ad_accounts(self, business_id: Optional[str] = None) -> List[Dict]:
        """Retorna contas de anúncio. Se business_id, filtra pelo BM."""
        try:
            if business_id:
                bm = Business(business_id)
                accounts = bm.get_owned_ad_accounts(
                    fields=["id", "name", "currency", "account_status", "balance"]
                )
            else:
                me = FBUser(fbid="me")
                accounts = me.get_ad_accounts(
                    fields=["id", "name", "currency", "account_status", "balance"]
                )
            return [
                {
                    "account_id": a["id"],
                    "name": a.get("name", ""),
                    "currency": a.get("currency", "BRL"),
                    "status": a.get("account_status", 1),
                    "business_id": business_id,
                }
                for a in accounts
            ]
        except Exception as e:
            raise ValueError(f"Erro ao buscar contas de anúncio: {str(e)}")

    def get_campaigns(self, account_id: str) -> List[Dict]:
        """Retorna campanhas de uma conta de anúncio."""
        try:
            account = AdAccount(f"act_{account_id.replace('act_', '')}")
            campaigns = account.get_campaigns(
                fields=[
                    "id", "name", "status", "objective",
                    "daily_budget", "lifetime_budget",
                    "start_time", "stop_time", "created_time",
                ]
            )
            return [
                {
                    "campaign_id": c["id"],
                    "name": c["name"],
                    "status": c["status"],
                    "objective": c.get("objective", ""),
                    "daily_budget": float(c["daily_budget"]) / 100 if c.get("daily_budget") else None,
                    "lifetime_budget": float(c["lifetime_budget"]) / 100 if c.get("lifetime_budget") else None,
                    "created_time": c.get("created_time"),
                    "account_id": account_id,
                }
                for c in campaigns
            ]
        except Exception as e:
            raise ValueError(f"Erro ao buscar campanhas: {str(e)}")

    def get_campaign_insights(
        self,
        account_id: str,
        date_preset: str = "last_7d",
        campaign_id: Optional[str] = None,
    ) -> List[Dict]:
        """Retorna insights (métricas) de campanhas."""
        try:
            fb_preset = DATE_PRESETS.get(date_preset, "last_7_d")
            account = AdAccount(f"act_{account_id.replace('act_', '')}")

            params = {
                "date_preset": fb_preset,
                "level": "campaign",
            }

            if campaign_id:
                params["filtering"] = [{"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}]

            fields = INSIGHT_FIELDS + ["campaign_id", "campaign_name"]
            insights = account.get_insights(fields=fields, params=params)
            results = []

            for insight in insights:
                roas = 0.0
                if insight.get("purchase_roas"):
                    try:
                        roas = float(insight["purchase_roas"][0].get("value", 0))
                    except (IndexError, TypeError, ValueError):
                        roas = 0.0

                conversions = 0
                cost_per_conversion = 0.0
                if insight.get("conversions"):
                    try:
                        conversions = int(float(insight["conversions"][0].get("value", 0)))
                    except (IndexError, TypeError, ValueError):
                        pass

                if insight.get("cost_per_conversion"):
                    try:
                        cost_per_conversion = float(insight["cost_per_conversion"][0].get("value", 0))
                    except (IndexError, TypeError, ValueError):
                        pass

                results.append({
                    "campaign_id": insight.get("campaign_id", ""),
                    "campaign_name": insight.get("campaign_name", ""),
                    "impressions": int(insight.get("impressions", 0)),
                    "clicks": int(insight.get("clicks", 0)),
                    "spend": float(insight.get("spend", 0)),
                    "reach": int(insight.get("reach", 0)),
                    "cpm": float(insight.get("cpm", 0)),
                    "cpc": float(insight.get("cpc", 0)),
                    "ctr": float(insight.get("ctr", 0)),
                    "conversions": conversions,
                    "cost_per_conversion": cost_per_conversion,
                    "roas": roas,
                    "frequency": float(insight.get("frequency", 0)),
                    "account_id": account_id,
                    "date_start": insight.get("date_start"),
                    "date_stop": insight.get("date_stop"),
                })

            return results
        except Exception as e:
            raise ValueError(f"Erro ao buscar insights: {str(e)}")

    def get_adset_insights(self, account_id: str, campaign_id: str, date_preset: str = "last_7d") -> List[Dict]:
        """Retorna insights de conjuntos de anúncios de uma campanha."""
        try:
            fb_preset = DATE_PRESETS.get(date_preset, "last_7_d")
            account = AdAccount(f"act_{account_id.replace('act_', '')}")

            params = {
                "date_preset": fb_preset,
                "level": "adset",
                "filtering": [{"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}],
            }

            fields = INSIGHT_FIELDS + ["adset_id", "adset_name", "campaign_id", "daily_budget"]
            insights = account.get_insights(fields=fields, params=params)
            return [
                {
                    "adset_id": i.get("adset_id", ""),
                    "adset_name": i.get("adset_name", ""),
                    "campaign_id": i.get("campaign_id", ""),
                    "impressions": int(i.get("impressions", 0)),
                    "clicks": int(i.get("clicks", 0)),
                    "spend": float(i.get("spend", 0)),
                    "cpm": float(i.get("cpm", 0)),
                    "cpc": float(i.get("cpc", 0)),
                    "ctr": float(i.get("ctr", 0)),
                    "roas": 0.0,
                }
                for i in insights
            ]
        except Exception as e:
            raise ValueError(f"Erro ao buscar insights de adsets: {str(e)}")

    # ===== AÇÕES DE OTIMIZAÇÃO (executadas após aprovação) =====

    def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa uma campanha."""
        try:
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"status": Campaign.Status.paused})
            return True
        except Exception as e:
            raise ValueError(f"Erro ao pausar campanha {campaign_id}: {str(e)}")

    def enable_campaign(self, campaign_id: str) -> bool:
        """Ativa uma campanha."""
        try:
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"status": Campaign.Status.active})
            return True
        except Exception as e:
            raise ValueError(f"Erro ao ativar campanha {campaign_id}: {str(e)}")

    def adjust_campaign_budget(self, campaign_id: str, new_daily_budget: float) -> bool:
        """Ajusta o orçamento diário de uma campanha (em reais)."""
        try:
            # Meta usa centavos
            budget_cents = int(new_daily_budget * 100)
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"daily_budget": budget_cents})
            return True
        except Exception as e:
            raise ValueError(f"Erro ao ajustar orçamento da campanha {campaign_id}: {str(e)}")

    def adjust_adset_budget(self, adset_id: str, new_daily_budget: float) -> bool:
        """Ajusta o orçamento diário de um adset (em reais)."""
        try:
            budget_cents = int(new_daily_budget * 100)
            adset = AdSet(adset_id)
            adset.api_update(params={"daily_budget": budget_cents})
            return True
        except Exception as e:
            raise ValueError(f"Erro ao ajustar orçamento do adset {adset_id}: {str(e)}")

    def adjust_adset_bid(self, adset_id: str, new_bid: float) -> bool:
        """Ajusta o lance de um adset (em reais)."""
        try:
            bid_cents = int(new_bid * 100)
            adset = AdSet(adset_id)
            adset.api_update(params={"bid_amount": bid_cents})
            return True
        except Exception as e:
            raise ValueError(f"Erro ao ajustar lance do adset {adset_id}: {str(e)}")

    def get_user_info(self) -> Dict:
        """Retorna informações do usuário Meta."""
        try:
            me = FBUser(fbid="me")
            info = me.api_get(fields=["id", "name", "email"])
            return {"id": info["id"], "name": info["name"], "email": info.get("email")}
        except Exception as e:
            raise ValueError(f"Erro ao buscar info do usuário: {str(e)}")

    def exchange_long_lived_token(self, short_token: str) -> Dict:
        """Troca token curto por token longo (60 dias)."""
        import httpx
        url = "https://graph.facebook.com/v21.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_token,
        }
        response = httpx.get(url, params=params)
        data = response.json()
        if "error" in data:
            raise ValueError(f"Erro ao trocar token: {data['error'].get('message')}")
        return {
            "access_token": data["access_token"],
            "expires_in": data.get("expires_in", 5183944),
        }
