"""
Relatórios — endpoints para N8N, exportação PDF e dados consolidados.
Autenticação: JWT (painel) ou API Key (N8N).
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_n8n_user
from app.models.database import get_db
from app.models.user import User
from app.services.meta_service import MetaService
from app.services.pdf_service import generate_campaign_report
from app.schemas.report import ReportSummary, CampaignReportRow, N8NReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _fetch_report_data(user: User, account_ids: Optional[List[str]], date_preset: str) -> dict:
    """Busca e consolida dados de relatório de múltiplas contas."""
    if not user.meta_access_token:
        raise HTTPException(400, "Conta Meta não conectada")

    meta = MetaService(access_token=user.meta_access_token)

    if not account_ids:
        accounts = meta.get_ad_accounts()
        account_ids = [a["account_id"] for a in accounts]
        account_names = {a["account_id"]: a["name"] for a in accounts}
        logger.info(f"Contas encontradas: {len(account_ids)} — {[a['name'] for a in accounts]}")
    else:
        account_names = {}

    all_insights = []

    for account_id in account_ids:
        try:
            insights = meta.get_campaign_insights(account_id=account_id, date_preset=date_preset)
            campaigns = meta.get_campaigns(account_id=account_id)
            status_map = {c["campaign_id"]: {"status": c["status"], "objective": c.get("objective")} for c in campaigns}

            logger.info(f"Conta {account_id}: {len(insights)} insights, {len(campaigns)} campanhas")

            for insight in insights:
                campaign_info = status_map.get(insight["campaign_id"], {})
                insight["status"] = campaign_info.get("status", "UNKNOWN")
                insight["objective"] = campaign_info.get("objective", "")
                insight["account_name"] = account_names.get(account_id, account_id)
                all_insights.append(insight)
        except Exception as e:
            logger.error(f"Erro na conta {account_id}: {e}")
            continue

    if not all_insights:
        return {"campaigns": [], "summary": _empty_summary(date_preset)}

    # Calcula totais
    total_spend = sum(i.get("spend", 0) for i in all_insights)
    total_impressions = sum(i.get("impressions", 0) for i in all_insights)
    total_clicks = sum(i.get("clicks", 0) for i in all_insights)
    total_conversions = sum(i.get("conversions", 0) for i in all_insights)
    avg_cpc = total_spend / total_clicks if total_clicks > 0 else 0
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    roas_values = [i.get("roas", 0) for i in all_insights if i.get("roas", 0) > 0]
    avg_roas = sum(roas_values) / len(roas_values) if roas_values else 0

    return {
        "campaigns": all_insights,
        "summary": {
            "period": date_preset,
            "total_spend": round(total_spend, 2),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "average_cpc": round(avg_cpc, 2),
            "average_roas": round(avg_roas, 2),
            "average_ctr": round(avg_ctr, 2),
            "generated_at": datetime.utcnow().isoformat(),
        },
    }


def _empty_summary(period: str) -> dict:
    return {
        "period": period,
        "total_spend": 0,
        "total_impressions": 0,
        "total_clicks": 0,
        "total_conversions": 0,
        "average_cpc": 0,
        "average_roas": 0,
        "average_ctr": 0,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ===== ENDPOINTS PAINEL (JWT) =====

@router.get("/summary", summary="Resumo consolidado (painel)")
def get_summary(
    date_preset: str = Query("last_7d"),
    account_ids: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Retorna resumo consolidado de performance para o painel."""
    data = _fetch_report_data(user=current_user, account_ids=account_ids, date_preset=date_preset)
    return data


@router.get("/pdf", summary="Exportar relatório em PDF (painel)")
def export_pdf(
    date_preset: str = Query("last_7d"),
    account_ids: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Gera e baixa o relatório em PDF.
    """
    data = _fetch_report_data(user=current_user, account_ids=account_ids, date_preset=date_preset)

    preset_labels = {
        "last_7d": "Últimos 7 Dias",
        "last_30d": "Últimos 30 Dias",
        "this_month": "Este Mês",
        "last_month": "Mês Passado",
    }

    pdf_bytes = generate_campaign_report(
        campaigns=data["campaigns"],
        period=preset_labels.get(date_preset, date_preset),
        summary=data["summary"],
    )

    filename = f"relatorio-campanhas-{date_preset}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===== ENDPOINTS N8N (API Key) =====

@router.get("/n8n/campaigns", summary="[N8N] Dados de campanhas via API Key")
def n8n_get_campaigns(
    date_preset: str = Query("last_7d", description="Período: last_7d, last_30d, this_month, last_month"),
    account_ids: Optional[List[str]] = Query(None),
    n8n_user: User = Depends(get_n8n_user),
):
    """
    Endpoint para N8N buscar dados de campanhas.
    Autenticação: Header `X-API-Key: sua_chave`.

    Retorna dados JSON prontos para processar no N8N.
    """
    data = _fetch_report_data(user=n8n_user, account_ids=account_ids, date_preset=date_preset)
    return N8NReportResponse(
        success=True,
        data=ReportSummary(
            period=data["summary"]["period"],
            total_spend=data["summary"]["total_spend"],
            total_impressions=data["summary"]["total_impressions"],
            total_clicks=data["summary"]["total_clicks"],
            total_conversions=data["summary"]["total_conversions"],
            average_cpc=data["summary"]["average_cpc"],
            average_roas=data["summary"]["average_roas"],
            average_ctr=data["summary"]["average_ctr"],
            campaigns=[
                CampaignReportRow(
                    campaign_id=c["campaign_id"],
                    campaign_name=c["campaign_name"],
                    status=c.get("status", "UNKNOWN"),
                    objective=c.get("objective"),
                    impressions=c.get("impressions", 0),
                    clicks=c.get("clicks", 0),
                    spend=c.get("spend", 0),
                    reach=c.get("reach", 0),
                    cpm=c.get("cpm", 0),
                    cpc=c.get("cpc", 0),
                    ctr=c.get("ctr", 0),
                    conversions=c.get("conversions", 0),
                    cost_per_conversion=c.get("cost_per_conversion", 0),
                    roas=c.get("roas", 0),
                    account_name=c.get("account_name", ""),
                )
                for c in data["campaigns"]
            ],
            generated_at=datetime.utcnow(),
        ),
        metadata={
            "api_version": "1.0",
            "date_preset": date_preset,
            "accounts_queried": len(account_ids) if account_ids else "all",
        },
    )


@router.get("/n8n/pdf", summary="[N8N] Gerar e retornar PDF via API Key")
def n8n_get_pdf(
    date_preset: str = Query("last_7d"),
    account_ids: Optional[List[str]] = Query(None),
    n8n_user: User = Depends(get_n8n_user),
):
    """
    Gera PDF do relatório para uso no N8N (ex: enviar por email ao cliente).
    Autenticação: Header `X-API-Key: sua_chave`.
    """
    data = _fetch_report_data(user=n8n_user, account_ids=account_ids, date_preset=date_preset)
    preset_labels = {
        "last_7d": "Últimos 7 Dias",
        "last_30d": "Últimos 30 Dias",
        "this_month": "Este Mês",
        "last_month": "Mês Passado",
    }
    pdf_bytes = generate_campaign_report(
        campaigns=data["campaigns"],
        period=preset_labels.get(date_preset, date_preset),
        summary=data["summary"],
    )
    filename = f"relatorio-{date_preset}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/n8n/summary", summary="[N8N] Resumo rápido via API Key")
def n8n_summary(
    date_preset: str = Query("last_7d"),
    n8n_user: User = Depends(get_n8n_user),
):
    """Resumo de métricas em JSON para processar no N8N."""
    data = _fetch_report_data(user=n8n_user, account_ids=None, date_preset=date_preset)
    return {"success": True, "summary": data["summary"], "campaign_count": len(data["campaigns"])}
