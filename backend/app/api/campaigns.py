"""
Endpoints de campanhas — listagem, status e métricas.
Acessíveis via JWT (painel) ou API Key (N8N).
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_n8n_user
from app.models.database import get_db
from app.models.user import User
from app.services.meta_service import MetaService

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_meta_service(user: User) -> MetaService:
    if not user.meta_access_token:
        raise HTTPException(400, "Conta Meta não conectada. Faça login com o Meta primeiro.")
    return MetaService(access_token=user.meta_access_token)


@router.get("/business-managers", summary="Listar Business Managers")
def list_business_managers(current_user: User = Depends(get_current_user)):
    """Retorna todos os Business Managers acessíveis."""
    meta = _get_meta_service(current_user)
    try:
        return meta.get_business_managers()
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/accounts", summary="Listar contas de anúncio")
def list_ad_accounts(
    business_id: Optional[str] = Query(None, description="Filtrar por Business Manager"),
    current_user: User = Depends(get_current_user),
):
    """Retorna contas de anúncio. Filtra por BM se business_id fornecido."""
    meta = _get_meta_service(current_user)
    try:
        return meta.get_ad_accounts(business_id=business_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# IMPORTANTE: rota com sub-path deve vir ANTES de /{account_id}
@router.get("/{account_id}/insights", summary="Insights de campanhas")
def get_campaign_insights(
    account_id: str,
    date_preset: str = Query("last_7d", description="Período: last_7d, last_30d, this_month, last_month"),
    campaign_id: Optional[str] = Query(None, description="Filtrar por campanha específica"),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna métricas de campanhas: impressões, cliques, gasto, ROAS, etc.
    Campanhas ATIVAS sem dados no período aparecem com métricas zeradas.
    """
    meta = _get_meta_service(current_user)
    try:
        # Busca insights do período (pode retornar vazio se não há atividade)
        try:
            insights = meta.get_campaign_insights(
                account_id=account_id,
                date_preset=date_preset,
                campaign_id=campaign_id,
            )
        except Exception as e:
            logger.warning(f"Sem insights para {account_id} em {date_preset}: {e}")
            insights = []

        # Busca todas as campanhas da conta
        try:
            campaigns = meta.get_campaigns(account_id=account_id)
        except Exception as e:
            logger.error(f"Erro ao buscar campanhas de {account_id}: {e}")
            campaigns = []

        # Garante que campanhas ATIVAS aparecem mesmo sem dados no período
        insight_ids = {i["campaign_id"] for i in insights}
        for c in campaigns:
            if c.get("status") == "ACTIVE" and c["campaign_id"] not in insight_ids:
                insights.append({
                    "campaign_id": c["campaign_id"],
                    "campaign_name": c["name"],
                    "status": c["status"],
                    "objective": c.get("objective", ""),
                    "impressions": 0, "clicks": 0, "spend": 0.0, "reach": 0,
                    "cpm": 0.0, "cpc": 0.0, "ctr": 0.0, "conversions": 0,
                    "cost_per_conversion": 0.0, "roas": 0.0, "frequency": 0.0,
                    "account_id": account_id,
                    "date_start": None, "date_stop": None,
                })

        return insights
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{account_id}/{campaign_id}/adsets", summary="Insights de conjuntos de anúncios")
def get_adset_insights(
    account_id: str,
    campaign_id: str,
    date_preset: str = Query("last_7d"),
    current_user: User = Depends(get_current_user),
):
    """Retorna métricas de conjuntos de anúncios de uma campanha."""
    meta = _get_meta_service(current_user)
    try:
        return meta.get_adset_insights(
            account_id=account_id,
            campaign_id=campaign_id,
            date_preset=date_preset,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{account_id}", summary="Listar campanhas de uma conta")
def list_campaigns(
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retorna todas as campanhas de uma conta de anúncio."""
    meta = _get_meta_service(current_user)
    try:
        return meta.get_campaigns(account_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
