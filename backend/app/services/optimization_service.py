"""
Executa ações de otimização aprovadas pelo usuário via Meta API.
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalStatus
from app.models.user import User
from app.services.meta_service import MetaService


def execute_approved_action(approval: Approval, db: Session) -> dict:
    """
    Executa uma ação aprovada pelo usuário.
    Retorna dict com status e resultado.
    """
    user: User = approval.user
    if not user.meta_access_token:
        return {"success": False, "error": "Token Meta não encontrado para este usuário"}

    meta = MetaService(access_token=user.meta_access_token)
    payload = json.loads(approval.payload)

    try:
        result_msg = ""

        if approval.action_type == "pause_campaign":
            meta.pause_campaign(payload["campaign_id"])
            result_msg = f"Campanha pausada com sucesso em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"

        elif approval.action_type == "enable_campaign":
            meta.enable_campaign(payload["campaign_id"])
            result_msg = f"Campanha ativada com sucesso em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"

        elif approval.action_type == "adjust_budget":
            meta.adjust_campaign_budget(
                campaign_id=payload["campaign_id"],
                new_daily_budget=float(payload["new_budget"]),
            )
            result_msg = f"Orçamento ajustado para R$ {payload['new_budget']:.2f}/dia com sucesso"

        elif approval.action_type == "adjust_bid":
            meta.adjust_adset_bid(
                adset_id=payload["adset_id"],
                new_bid=float(payload["new_bid"]),
            )
            result_msg = f"Lance ajustado para R$ {payload['new_bid']:.2f} com sucesso"

        else:
            return {"success": False, "error": f"Tipo de ação desconhecido: {approval.action_type}"}

        # Atualiza status no banco
        approval.status = ApprovalStatus.EXECUTED
        approval.executed_at = datetime.utcnow()
        approval.execution_result = result_msg
        db.commit()

        return {"success": True, "message": result_msg}

    except Exception as e:
        error_msg = str(e)
        approval.status = ApprovalStatus.FAILED
        approval.execution_result = f"ERRO: {error_msg}"
        db.commit()
        return {"success": False, "error": error_msg}
