"""
Serviço de IA usando Claude claude-opus-4-6 com tool use (manual loop).
As ferramentas NÃO executam imediatamente — criam registros de aprovação no DB.
"""
import json
from typing import List, Dict, Any, Generator, Optional
from datetime import datetime
from sqlalchemy.orm import Session

import anthropic

from app.core.config import settings
from app.models.approval import Approval, ApprovalStatus


SYSTEM_PROMPT = """Você é um especialista em tráfego pago digital com mais de 10 anos de experiência
em Meta ADS (Facebook e Instagram). Você analisa dados de campanhas e sugere otimizações
com base em métricas como ROAS, CPC, CPM, CTR e taxa de conversão.

IMPORTANTE: Ao sugerir otimizações, você deve SEMPRE usar as ferramentas disponíveis para
criar as ações de otimização. Essas ações passarão por aprovação humana antes de serem
executadas — explique claramente o motivo de cada sugestão.

Fale em português brasileiro. Seja direto e objetivo nas análises.
Forneça benchmarks do setor quando relevante.
Priorize otimizações com maior impacto no ROAS e ROI."""


def _build_tools() -> List[Dict]:
    """Define as ferramentas disponíveis para o Claude."""
    return [
        {
            "name": "pause_campaign",
            "description": "Pausa uma campanha que está com performance ruim. Use quando: ROAS < 0.5, CPC muito alto (>3x do benchmark), ou campanha com alto gasto e zero conversões.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "ID da campanha no Meta"},
                    "campaign_name": {"type": "string", "description": "Nome da campanha"},
                    "account_id": {"type": "string", "description": "ID da conta de anúncio"},
                    "reason": {"type": "string", "description": "Justificativa detalhada para pausar a campanha"},
                },
                "required": ["campaign_id", "campaign_name", "account_id", "reason"],
            },
        },
        {
            "name": "enable_campaign",
            "description": "Ativa uma campanha pausada que tem potencial de melhora ou que estava em período de espera.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "ID da campanha"},
                    "campaign_name": {"type": "string", "description": "Nome da campanha"},
                    "account_id": {"type": "string", "description": "ID da conta de anúncio"},
                    "reason": {"type": "string", "description": "Justificativa para ativar a campanha"},
                },
                "required": ["campaign_id", "campaign_name", "account_id", "reason"],
            },
        },
        {
            "name": "adjust_budget",
            "description": "Ajusta o orçamento diário de uma campanha. Aumente o orçamento de campanhas com ROAS alto (>2x) e diminua de campanhas com ROAS baixo.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "ID da campanha"},
                    "campaign_name": {"type": "string", "description": "Nome da campanha"},
                    "account_id": {"type": "string", "description": "ID da conta de anúncio"},
                    "current_budget": {"type": "number", "description": "Orçamento atual em reais"},
                    "new_budget": {"type": "number", "description": "Novo orçamento diário sugerido em reais"},
                    "reason": {"type": "string", "description": "Justificativa com métricas que embasam a mudança"},
                },
                "required": ["campaign_id", "campaign_name", "account_id", "new_budget", "reason"],
            },
        },
        {
            "name": "adjust_bid",
            "description": "Ajusta o lance (bid) de um conjunto de anúncios para melhorar posicionamento ou reduzir custos.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "adset_id": {"type": "string", "description": "ID do conjunto de anúncios"},
                    "campaign_id": {"type": "string", "description": "ID da campanha pai"},
                    "campaign_name": {"type": "string", "description": "Nome da campanha"},
                    "account_id": {"type": "string", "description": "ID da conta de anúncio"},
                    "new_bid": {"type": "number", "description": "Novo valor de lance em reais"},
                    "reason": {"type": "string", "description": "Justificativa para o ajuste de lance"},
                },
                "required": ["adset_id", "campaign_id", "campaign_name", "account_id", "new_bid", "reason"],
            },
        },
    ]


def _create_approval(
    db: Session,
    user_id: int,
    action_type: str,
    payload: Dict,
    ai_reasoning: str,
    campaign_id: Optional[str] = None,
    campaign_name: Optional[str] = None,
    adset_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Approval:
    """Cria um registro de aprovação pendente no banco de dados."""
    approval = Approval(
        user_id=user_id,
        action_type=action_type,
        payload=json.dumps(payload, ensure_ascii=False),
        ai_reasoning=ai_reasoning,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        adset_id=adset_id,
        account_id=account_id,
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def _execute_tool(
    tool_name: str,
    tool_input: Dict,
    db: Session,
    user_id: int,
) -> str:
    """Executa uma ferramenta — cria aprovação pendente em vez de executar imediatamente."""
    reasoning = tool_input.get("reason", "Sem justificativa fornecida")

    if tool_name == "pause_campaign":
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="pause_campaign",
            payload={"campaign_id": tool_input["campaign_id"]},
            ai_reasoning=reasoning,
            campaign_id=tool_input["campaign_id"],
            campaign_name=tool_input.get("campaign_name"),
            account_id=tool_input.get("account_id"),
        )
        return f"✅ Sugestão criada (ID #{approval.id}): Pausar campanha '{tool_input['campaign_name']}'. Aguardando sua aprovação."

    elif tool_name == "enable_campaign":
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="enable_campaign",
            payload={"campaign_id": tool_input["campaign_id"]},
            ai_reasoning=reasoning,
            campaign_id=tool_input["campaign_id"],
            campaign_name=tool_input.get("campaign_name"),
            account_id=tool_input.get("account_id"),
        )
        return f"✅ Sugestão criada (ID #{approval.id}): Ativar campanha '{tool_input['campaign_name']}'. Aguardando sua aprovação."

    elif tool_name == "adjust_budget":
        payload = {
            "campaign_id": tool_input["campaign_id"],
            "new_budget": tool_input["new_budget"],
            "current_budget": tool_input.get("current_budget"),
        }
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="adjust_budget",
            payload=payload,
            ai_reasoning=reasoning,
            campaign_id=tool_input["campaign_id"],
            campaign_name=tool_input.get("campaign_name"),
            account_id=tool_input.get("account_id"),
        )
        return f"✅ Sugestão criada (ID #{approval.id}): Ajustar orçamento de '{tool_input['campaign_name']}' para R$ {tool_input['new_budget']:.2f}/dia. Aguardando aprovação."

    elif tool_name == "adjust_bid":
        payload = {
            "adset_id": tool_input["adset_id"],
            "campaign_id": tool_input["campaign_id"],
            "new_bid": tool_input["new_bid"],
        }
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="adjust_bid",
            payload=payload,
            ai_reasoning=reasoning,
            campaign_id=tool_input["campaign_id"],
            campaign_name=tool_input.get("campaign_name"),
            adset_id=tool_input["adset_id"],
            account_id=tool_input.get("account_id"),
        )
        return f"✅ Sugestão criada (ID #{approval.id}): Ajustar lance para R$ {tool_input['new_bid']:.2f}. Aguardando aprovação."

    return f"Ferramenta '{tool_name}' não reconhecida."


def analyze_campaigns(
    campaigns_data: List[Dict],
    db: Session,
    user_id: int,
    custom_prompt: Optional[str] = None,
) -> str:
    """
    Analisa dados de campanhas com Claude e cria sugestões de otimização.
    Usa manual agentic loop com human-in-the-loop.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    tools = _build_tools()

    # Prepara contexto com dados das campanhas
    campaigns_json = json.dumps(campaigns_data, ensure_ascii=False, indent=2)
    user_message = f"""Analise as seguintes campanhas do Meta ADS e crie sugestões de otimização:

```json
{campaigns_json}
```

{f'Instrução adicional: {custom_prompt}' if custom_prompt else ''}

Por favor:
1. Identifique as campanhas com melhor e pior performance
2. Calcule benchmarks e compare com as métricas apresentadas
3. Use as ferramentas disponíveis para criar sugestões de otimização concretas
4. Forneça um resumo executivo com as principais conclusões e próximos passos"""

    messages = [{"role": "user", "content": user_message}]

    # Loop do agente até parar de chamar ferramentas
    while True:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        # Se parou (sem mais ferramentas para chamar), retorna
        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        # Processa chamadas de ferramentas
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _execute_tool(
                        tool_name=block.name,
                        tool_input=block.input,
                        db=db,
                        user_id=user_id,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Outro stop reason (max_tokens, etc.)
            break

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks) if text_blocks else "Análise concluída."


def chat_with_ai(
    message: str,
    campaigns_data: List[Dict],
    db: Session,
    user_id: int,
    conversation_history: Optional[List[Dict]] = None,
) -> Generator[str, None, None]:
    """
    Chat com IA via streaming. Suporta histórico de conversa.
    Retorna generator de chunks de texto.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    tools = _build_tools()

    messages = list(conversation_history or [])

    # Adiciona contexto de campanhas se não tiver histórico
    if not messages and campaigns_data:
        campaigns_json = json.dumps(campaigns_data[:10], ensure_ascii=False, indent=2)
        context_msg = f"Contexto atual das campanhas:\n```json\n{campaigns_json}\n```\n\n{message}"
        messages.append({"role": "user", "content": context_msg})
    else:
        messages.append({"role": "user", "content": message})

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            yield text

        final = stream.get_final_message()

    # Se chamou ferramentas, processa em segundo plano
    if final.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": final.content})
        tool_results = []
        for block in final.content:
            if block.type == "tool_use":
                result = _execute_tool(
                    tool_name=block.name,
                    tool_input=block.input,
                    db=db,
                    user_id=user_id,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})

        # Segunda rodada para o Claude responder após as ferramentas
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        ) as stream2:
            yield "\n\n"
            for text in stream2.text_stream:
                yield text
