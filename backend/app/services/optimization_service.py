"""
Executa ações de otimização aprovadas pelo usuário via Meta API.
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalStatus
from app.models.user import User
from app.services.meta_service import MetaService

logger = logging.getLogger(__name__)


def _objective_to_optimization_goal(objective: str) -> str:
    """Mapeia objetivo de campanha para optimization_goal do AdSet."""
    mapping = {
        "CONVERSIONS": "OFFSITE_CONVERSIONS",
        "OUTCOME_SALES": "OFFSITE_CONVERSIONS",
        "TRAFFIC": "LINK_CLICKS",
        "OUTCOME_TRAFFIC": "LINK_CLICKS",
        "AWARENESS": "REACH",
        "OUTCOME_AWARENESS": "REACH",
        "REACH": "REACH",
        "LEAD_GENERATION": "LEAD_GENERATION",
        "OUTCOME_LEADS": "LEAD_GENERATION",
        "ENGAGEMENT": "POST_ENGAGEMENT",
        "OUTCOME_ENGAGEMENT": "POST_ENGAGEMENT",
        "VIDEO_VIEWS": "THRUPLAY",
        "APP_INSTALLS": "APP_INSTALLS",
        "OUTCOME_APP_PROMOTION": "APP_INSTALLS",
        "MESSAGES": "CONVERSATIONS",
    }
    return mapping.get(objective.upper(), "LINK_CLICKS")


def _parse_geo_locations(geo_str: str) -> dict:
    """
    Converte string de localização (ex: 'São Paulo, Campinas') para
    o formato geo_locations da Meta API com targeting por país.
    Nota: Meta exige keys específicas para cidades — sem elas, usa Brasil.
    """
    if not geo_str or geo_str.strip().lower() in ("brasil", "brazil", "br", "brasil (abrangência nacional)"):
        return {"countries": ["BR"]}
    # Usa Brasil como targeting base com a nota das cidades sugeridas
    # O usuário deve refinar as cidades específicas no Gerenciador da Meta
    return {"countries": ["BR"]}


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

        elif approval.action_type == "create_campaign":
            campaign_id = meta.create_campaign(
                account_id=approval.account_id,
                name=payload["campaign_name"],
                objective=payload["objective"],
                daily_budget=float(payload["daily_budget"]),
            )
            geo_hint = f" | Localização: {payload['geo_locations']}" if payload.get("geo_locations") else ""
            result_msg = f"Campanha '{payload['campaign_name']}' criada e ATIVA (ID: {campaign_id}).{geo_hint}"

            # Gera automaticamente a aprovação do conjunto de anúncios
            optimization_goal = _objective_to_optimization_goal(payload.get("objective", ""))
            adset_payload = json.dumps({
                "campaign_id": campaign_id,
                "adset_name": f"Conjunto - {payload['campaign_name']}",
                "daily_budget": payload["daily_budget"],
                "optimization_goal": optimization_goal,
                "geo_locations": payload.get("geo_locations", "Brasil"),
                "age_min": 18,
                "age_max": 65,
            }, ensure_ascii=False)
            adset_approval = Approval(
                user_id=approval.user_id,
                action_type="create_adset",
                payload=adset_payload,
                ai_reasoning=(
                    f"Conjunto de anúncios gerado automaticamente para a campanha '{payload['campaign_name']}' "
                    f"(ID: {campaign_id}). Objetivo de otimização: {optimization_goal}. "
                    f"Localização: {payload.get('geo_locations', 'Brasil')}. "
                    "Revise e aprove para criar o AdSet na Meta."
                ),
                campaign_id=campaign_id,
                campaign_name=payload["campaign_name"],
                account_id=approval.account_id,
                status=ApprovalStatus.PENDING,
            )
            db.add(adset_approval)
            db.flush()
            result_msg += f" | Aprovação do AdSet criada (#{ adset_approval.id}) — aguarda sua confirmação."

        elif approval.action_type == "create_adset":
            adset_geo = _parse_geo_locations(payload.get("geo_locations", ""))
            adset_id = meta.create_adset(
                account_id=approval.account_id,
                campaign_id=payload["campaign_id"],
                name=payload["adset_name"],
                daily_budget=float(payload["daily_budget"]),
                optimization_goal=payload["optimization_goal"],
                geo_locations=adset_geo,
                age_min=int(payload.get("age_min", 18)),
                age_max=int(payload.get("age_max", 65)),
            )
            result_msg = (
                f"Conjunto de Anúncios '{payload['adset_name']}' criado e ATIVO (ID: {adset_id}). "
                "Adicione os anúncios com criativos no Gerenciador de Anúncios da Meta."
            )

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
        logger.error(f"Falha ao executar approval #{approval.id} ({approval.action_type}): {error_msg}", exc_info=True)
        approval.status = ApprovalStatus.FAILED
        approval.execution_result = f"ERRO: {error_msg}"
        db.commit()
        return {"success": False, "error": error_msg}
