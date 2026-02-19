"""
Endpoints de IA — análise de campanhas e chat interativo com streaming.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user import User
from app.services.meta_service import MetaService
from app.services.ai_service import analyze_campaigns, chat_with_ai
from app.schemas.approval import AIAnalysisRequest, AIChatMessage

router = APIRouter()


def _get_campaigns_data(user: User, account_ids: Optional[List[str]], date_preset: str) -> List[dict]:
    """Busca dados de campanhas de todas as contas ou das contas especificadas."""
    if not user.meta_access_token:
        raise HTTPException(400, "Conta Meta não conectada.")

    meta = MetaService(access_token=user.meta_access_token)

    if not account_ids:
        accounts = meta.get_ad_accounts()
        account_ids = [a["account_id"] for a in accounts[:5]]  # Limita a 5 contas por análise

    all_campaigns = []
    for account_id in account_ids:
        try:
            insights = meta.get_campaign_insights(account_id=account_id, date_preset=date_preset)
            campaigns = meta.get_campaigns(account_id=account_id)

            # Enriquece insights com status da campanha
            status_map = {c["campaign_id"]: c["status"] for c in campaigns}
            for insight in insights:
                insight["status"] = status_map.get(insight["campaign_id"], "UNKNOWN")
                all_campaigns.append(insight)
        except Exception:
            continue

    return all_campaigns


@router.post("/analyze", summary="Análise completa de campanhas com IA")
def analyze_with_ai(
    request: AIAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Solicita ao Claude uma análise completa das campanhas.
    O Claude cria sugestões de otimização que aparecem na fila de aprovações.
    """
    try:
        campaigns_data = _get_campaigns_data(
            user=current_user,
            account_ids=request.account_ids,
            date_preset=request.date_preset,
        )

        if not campaigns_data:
            return {"analysis": "Nenhuma campanha encontrada para o período selecionado.", "suggestions_created": 0}

        analysis_text = analyze_campaigns(
            campaigns_data=campaigns_data,
            db=db,
            user_id=current_user.id,
            custom_prompt=request.custom_prompt,
        )

        # Conta sugestões criadas
        from app.models.approval import Approval, ApprovalStatus
        from datetime import datetime, timedelta
        recent_count = (
            db.query(Approval)
            .filter(
                Approval.user_id == current_user.id,
                Approval.status == ApprovalStatus.PENDING,
                Approval.created_at >= datetime.utcnow() - timedelta(minutes=5),
            )
            .count()
        )

        return {
            "analysis": analysis_text,
            "suggestions_created": recent_count,
        }

    except Exception as e:
        raise HTTPException(500, f"Erro na análise: {str(e)}")


@router.post("/chat", summary="Chat com IA (streaming)")
def chat_stream(
    request: AIChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Chat interativo com a IA via Server-Sent Events (streaming).
    O Claude pode sugerir otimizações durante o chat.
    """
    try:
        campaigns_data = _get_campaigns_data(
            user=current_user,
            account_ids=request.account_ids,
            date_preset="last_7d",
        )

        def generate():
            try:
                for chunk in chat_with_ai(
                    message=request.message,
                    campaigns_data=campaigns_data,
                    db=db,
                    user_id=current_user.id,
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: Erro: {str(e)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        raise HTTPException(500, f"Erro no chat: {str(e)}")
