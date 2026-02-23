"""
Serviço de IA usando Google Gemini com function calling (manual loop).
As ferramentas NÃO executam imediatamente — criam registros de aprovação no DB.
"""
import json
import os
import logging
from typing import List, Dict, Any, Generator, Optional
from sqlalchemy.orm import Session

import google.generativeai as genai
import google.generativeai.protos as protos

from app.core.config import settings
from app.models.approval import Approval, ApprovalStatus

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"


def _get_user_ai_config(db: Session, user_id: int) -> tuple[str, str]:
    """Retorna (api_key, model_name) da config do usuário ou env vars como fallback."""
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()

    api_key = (
        (user.gemini_api_key if user else None)
        or os.environ.get("GEMINI_API_KEY")
        or settings.GEMINI_API_KEY
        or None
    )
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY não configurada. Acesse Configurações → IA para inserir sua chave."
        )

    model_name = (
        (user.ai_model if user and user.ai_model else None)
        or MODEL_NAME
    )
    return api_key, model_name


def _configure_gemini(api_key: str) -> None:
    """Configura o cliente Gemini com a API key."""
    genai.configure(api_key=api_key)


SYSTEM_PROMPT = """Você é um especialista em tráfego pago digital com mais de 10 anos de experiência
em Meta ADS (Facebook e Instagram). Você analisa dados de campanhas e sugere otimizações
com base em métricas como ROAS, CPC, CPM, CTR e taxa de conversão.

IMPORTANTE: Ao sugerir otimizações, você deve SEMPRE usar as ferramentas disponíveis para
criar as ações de otimização. Essas ações passarão por aprovação humana antes de serem
executadas — explique claramente o motivo de cada sugestão.

NOMENCLATURA DE CAMPANHAS:
Sempre nomeie campanhas seguindo o padrão: [TIPO]-[PUBLICO]-[ACAO]
Exemplos práticos:
- CONVERSOES-MULHERES25-44-WHATSAPP
- TRAFEGO-HOMENS30-50-CLIQUE
- LEADS-DONOS-EMPRESA-FORMULARIO
- AWARENESS-JOVENS18-25-VIDEO
- REMARKETING-VISITANTES-SITE-COMPRA
Use apenas letras maiúsculas, hífens e números. Sem espaços ou caracteres especiais.

NOMENCLATURA DE CONJUNTOS DE ANÚNCIOS:
Use o formato: [PUBLICO]-[INTERESSE/COMPORTAMENTO]-[FAIXA-ETARIA]
Exemplos:
- MULHERES-MODA-25-44
- HOMENS-NEGOCIOS-30-55
- LOOKALIKE-COMPRADORES-18-65
- REMARKETING-PAGINA-18-65

CRIAÇÃO DE NOVAS CAMPANHAS E CONJUNTOS:
- Use suggest_new_campaign para criar a estrutura da campanha
- Use suggest_adset para adicionar conjuntos de anúncios com diferentes segmentações
- Uma campanha pode ter MÚLTIPLOS conjuntos — use suggest_adset várias vezes para
  testar diferentes públicos (ex: um conjunto para interesse, outro para lookalike,
  outro para remarketing)
- Quando sugerir uma nova campanha, sugira pelo menos um conjunto de anúncios junto
- Para criar "públicos" específicos, use suggest_adset com targeting_description detalhado
  descrevendo os interesses, comportamentos e dados demográficos do público

REGRAS SOBRE LOCALIZAÇÃO GEOGRÁFICA:
- Cada campanha pode conter o campo "targeting_locations" com as cidades/regiões reais configuradas no Meta.
- Use APENAS esse campo para mencionar localização. NUNCA invente ou suponha uma cidade/região
  que não esteja explicitamente no campo "targeting_locations" ou no nome da campanha/adset.
- Se "targeting_locations" não estiver presente, diga que não há dados de geolocalização disponíveis
  em vez de inferir qualquer localidade.

Fale em português brasileiro. Seja direto e objetivo nas análises.
Forneça benchmarks do setor quando relevante.
Priorize otimizações com maior impacto no ROAS e ROI."""


def _build_tools() -> protos.Tool:
    """Define as ferramentas disponíveis para o Gemini."""
    return protos.Tool(
        function_declarations=[
            protos.FunctionDeclaration(
                name="pause_campaign",
                description="Pausa uma campanha que está com performance ruim. Use quando: ROAS < 0.5, CPC muito alto (>3x do benchmark), ou campanha com alto gasto e zero conversões.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "campaign_id": protos.Schema(type=protos.Type.STRING, description="ID da campanha no Meta"),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome da campanha"),
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio"),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Justificativa detalhada para pausar a campanha"),
                    },
                    required=["campaign_id", "campaign_name", "account_id", "reason"],
                ),
            ),
            protos.FunctionDeclaration(
                name="enable_campaign",
                description="Ativa uma campanha pausada que tem potencial de melhora ou que estava em período de espera.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "campaign_id": protos.Schema(type=protos.Type.STRING, description="ID da campanha"),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome da campanha"),
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio"),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Justificativa para ativar a campanha"),
                    },
                    required=["campaign_id", "campaign_name", "account_id", "reason"],
                ),
            ),
            protos.FunctionDeclaration(
                name="adjust_budget",
                description="Ajusta o orçamento diário de uma campanha. Aumente o orçamento de campanhas com ROAS alto (>2x) e diminua de campanhas com ROAS baixo.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "campaign_id": protos.Schema(type=protos.Type.STRING, description="ID da campanha"),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome da campanha"),
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio"),
                        "current_budget": protos.Schema(type=protos.Type.NUMBER, description="Orçamento atual em reais"),
                        "new_budget": protos.Schema(type=protos.Type.NUMBER, description="Novo orçamento diário sugerido em reais"),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Justificativa com métricas que embasam a mudança"),
                    },
                    required=["campaign_id", "campaign_name", "account_id", "new_budget", "reason"],
                ),
            ),
            protos.FunctionDeclaration(
                name="adjust_bid",
                description="Ajusta o lance (bid) de um conjunto de anúncios para melhorar posicionamento ou reduzir custos.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "adset_id": protos.Schema(type=protos.Type.STRING, description="ID do conjunto de anúncios"),
                        "campaign_id": protos.Schema(type=protos.Type.STRING, description="ID da campanha pai"),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome da campanha"),
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio"),
                        "new_bid": protos.Schema(type=protos.Type.NUMBER, description="Novo valor de lance em reais"),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Justificativa para o ajuste de lance"),
                    },
                    required=["adset_id", "campaign_id", "campaign_name", "account_id", "new_bid", "reason"],
                ),
            ),
            protos.FunctionDeclaration(
                name="suggest_new_campaign",
                description="Sugere a criação de uma nova campanha. Use quando identificar oportunidades não exploradas: nichos sem campanha, objetivos ausentes, sazonalidade, ou produtos/serviços sem cobertura de anúncios. Após chamar esta ferramenta, use suggest_adset para adicionar conjuntos de anúncios.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio onde criar a campanha"),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome da campanha no padrão [TIPO]-[PUBLICO]-[ACAO]. Ex: 'CONVERSOES-MULHERES25-44-WHATSAPP', 'TRAFEGO-HOMENS30-CLIQUE', 'LEADS-DONOS-EMPRESA-FORMULARIO'"),
                        "objective": protos.Schema(type=protos.Type.STRING, description="Objetivo da campanha: CONVERSIONS, TRAFFIC, AWARENESS, LEAD_GENERATION, ENGAGEMENT, VIDEO_VIEWS, APP_INSTALLS"),
                        "daily_budget": protos.Schema(type=protos.Type.NUMBER, description="Orçamento diário total sugerido em reais para a campanha"),
                        "geo_locations": protos.Schema(type=protos.Type.STRING, description="Cidades ou regiões alvo da campanha. Use EXATAMENTE os valores do campo 'targeting_locations' das campanhas existentes quando disponíveis. Ex: 'São Paulo, Campinas'. Se não houver dados de localização, use 'Brasil (abrangência nacional)'."),
                        "targeting_description": protos.Schema(type=protos.Type.STRING, description="Descrição do público-alvo principal da campanha (faixa etária, interesses, comportamentos — SEM repetir a localização geográfica que já foi informada em geo_locations)"),
                        "strategy": protos.Schema(type=protos.Type.STRING, description="Estratégia completa: o que testar, tipo de criativo sugerido, CTA, posicionamento, quantos conjuntos serão criados"),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Por que esta campanha pode gerar resultados — oportunidade identificada com base nos dados atuais"),
                    },
                    required=["account_id", "campaign_name", "objective", "daily_budget", "geo_locations", "targeting_description", "strategy", "reason"],
                ),
            ),
            protos.FunctionDeclaration(
                name="suggest_adset",
                description="Sugere a criação de um conjunto de anúncios (AdSet) para uma campanha. Use para: (1) adicionar múltiplos conjuntos com diferentes públicos a uma nova campanha após suggest_new_campaign, (2) adicionar conjuntos a campanhas existentes, (3) criar públicos segmentados por interesse/comportamento/lookalike/remarketing.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "account_id": protos.Schema(type=protos.Type.STRING, description="ID da conta de anúncio"),
                        "campaign_id": protos.Schema(type=protos.Type.STRING, description="ID da campanha existente. Deixe vazio ('') se for para uma nova campanha ainda não criada (referenciada pelo campaign_name)."),
                        "campaign_name": protos.Schema(type=protos.Type.STRING, description="Nome exato da campanha (deve coincidir com o campaign_name usado em suggest_new_campaign para novas campanhas)"),
                        "adset_name": protos.Schema(type=protos.Type.STRING, description="Nome do conjunto no padrão [PUBLICO]-[INTERESSE]-[FAIXA-ETARIA]. Ex: 'MULHERES-MODA-25-44', 'LOOKALIKE-COMPRADORES-18-65', 'REMARKETING-VISITANTES-18-65'"),
                        "daily_budget": protos.Schema(type=protos.Type.NUMBER, description="Orçamento diário em reais para este conjunto específico"),
                        "optimization_goal": protos.Schema(type=protos.Type.STRING, description="Meta de otimização: OFFSITE_CONVERSIONS, LINK_CLICKS, REACH, LEAD_GENERATION, POST_ENGAGEMENT, THRUPLAY, APP_INSTALLS, CONVERSATIONS"),
                        "geo_locations": protos.Schema(type=protos.Type.STRING, description="Cidades ou regiões alvo deste conjunto. Ex: 'São Paulo, Campinas'. Use 'Brasil' para abrangência nacional."),
                        "age_min": protos.Schema(type=protos.Type.INTEGER, description="Idade mínima do público (padrão: 18)"),
                        "age_max": protos.Schema(type=protos.Type.INTEGER, description="Idade máxima do público (padrão: 65)"),
                        "targeting_description": protos.Schema(type=protos.Type.STRING, description="Descrição detalhada do público deste conjunto: gênero (se aplicável), interesses específicos, comportamentos, tipo de audiência (frio/morno/quente/lookalike/remarketing). Este campo é exibido ao usuário na aprovação."),
                        "reason": protos.Schema(type=protos.Type.STRING, description="Justificativa para este conjunto: por que este público, qual diferencial desta segmentação em relação aos outros conjuntos da campanha"),
                    },
                    required=["account_id", "campaign_name", "adset_name", "daily_budget", "optimization_goal", "geo_locations", "targeting_description", "reason"],
                ),
            ),
        ]
    )


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

    elif tool_name == "suggest_new_campaign":
        payload = {
            "campaign_name": tool_input["campaign_name"],
            "objective": tool_input["objective"],
            "daily_budget": tool_input["daily_budget"],
            "geo_locations": tool_input.get("geo_locations", ""),
            "targeting_description": tool_input.get("targeting_description", ""),
            "strategy": tool_input.get("strategy", ""),
        }
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="create_campaign",
            payload=payload,
            ai_reasoning=reasoning,
            campaign_name=tool_input["campaign_name"],
            account_id=tool_input.get("account_id"),
        )
        return f"✅ Sugestão de nova campanha criada (ID #{approval.id}): '{tool_input['campaign_name']}' ({tool_input['objective']}, R$ {tool_input['daily_budget']:.2f}/dia). Agora use suggest_adset para adicionar conjuntos de anúncios a esta campanha."

    elif tool_name == "suggest_adset":
        payload = {
            "campaign_id": tool_input.get("campaign_id", ""),
            "adset_name": tool_input["adset_name"],
            "daily_budget": tool_input["daily_budget"],
            "optimization_goal": tool_input["optimization_goal"],
            "geo_locations": tool_input.get("geo_locations", "Brasil"),
            "age_min": tool_input.get("age_min", 18),
            "age_max": tool_input.get("age_max", 65),
            "targeting_description": tool_input.get("targeting_description", ""),
        }
        campaign_id = tool_input.get("campaign_id") or None
        approval = _create_approval(
            db=db,
            user_id=user_id,
            action_type="create_adset",
            payload=payload,
            ai_reasoning=reasoning,
            campaign_id=campaign_id,
            campaign_name=tool_input.get("campaign_name"),
            account_id=tool_input.get("account_id"),
        )
        campaign_ref = f"campanha '{tool_input['campaign_name']}'"
        return f"✅ Sugestão de conjunto criada (ID #{approval.id}): '{tool_input['adset_name']}' para {campaign_ref}. Aguardando sua aprovação."

    return f"Ferramenta '{tool_name}' não reconhecida."


def _get_fn_calls(response) -> list:
    """Extrai chamadas de função de uma resposta do Gemini."""
    fn_calls = []
    try:
        for candidate in response.candidates:
            for part in candidate.content.parts:
                try:
                    if part.function_call.name:
                        fn_calls.append(part.function_call)
                except AttributeError:
                    pass
    except Exception:
        pass
    return fn_calls


def _get_text(response) -> str:
    """Extrai texto de uma resposta do Gemini."""
    texts = []
    try:
        for candidate in response.candidates:
            for part in candidate.content.parts:
                try:
                    if part.text:
                        texts.append(part.text)
                except AttributeError:
                    pass
    except Exception:
        pass
    return "".join(texts)


def analyze_campaigns(
    campaigns_data: List[Dict],
    db: Session,
    user_id: int,
    custom_prompt: Optional[str] = None,
) -> str:
    """
    Analisa dados de campanhas com Gemini e cria sugestões de otimização.
    Usa manual agentic loop com human-in-the-loop.
    """
    api_key, model_name = _get_user_ai_config(db, user_id)
    _configure_gemini(api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=[_build_tools()],
        system_instruction=SYSTEM_PROMPT,
    )

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

    chat = model.start_chat()
    response = chat.send_message(user_message)

    # Loop do agente até parar de chamar ferramentas
    for _ in range(10):
        fn_calls = _get_fn_calls(response)
        if not fn_calls:
            break

        result_parts = []
        for fc in fn_calls:
            result = _execute_tool(
                tool_name=fc.name,
                tool_input=dict(fc.args),
                db=db,
                user_id=user_id,
            )
            result_parts.append(protos.Part(
                function_response=protos.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            ))

        response = chat.send_message(result_parts)

    return _get_text(response) or "Análise concluída."


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
    api_key, model_name = _get_user_ai_config(db, user_id)
    _configure_gemini(api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=[_build_tools()],
        system_instruction=SYSTEM_PROMPT,
    )

    # Converte histórico do formato Anthropic para Gemini
    gemini_history = []
    for msg in (conversation_history or []):
        role = "model" if msg.get("role") == "assistant" else "user"
        content = msg.get("content", "")
        if isinstance(content, str) and content:
            gemini_history.append({"role": role, "parts": [content]})
        elif isinstance(content, list):
            texts = [
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text" and p.get("text")
            ]
            if texts:
                gemini_history.append({"role": role, "parts": [" ".join(texts)]})

    chat = model.start_chat(history=gemini_history)

    # Monta mensagem com contexto de campanhas se for primeira mensagem
    if not conversation_history and campaigns_data:
        campaigns_json = json.dumps(campaigns_data[:10], ensure_ascii=False, indent=2)
        current_message = f"Contexto atual das campanhas:\n```json\n{campaigns_json}\n```\n\n{message}"
    else:
        current_message = message

    # Primeira chamada — detecta function calls
    response = chat.send_message(current_message)

    # Yield texto da primeira resposta
    text = _get_text(response)
    if text:
        yield text

    # Processa function calls
    fn_calls = _get_fn_calls(response)
    if fn_calls:
        result_parts = []
        for fc in fn_calls:
            result = _execute_tool(
                tool_name=fc.name,
                tool_input=dict(fc.args),
                db=db,
                user_id=user_id,
            )
            result_parts.append(protos.Part(
                function_response=protos.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            ))

        yield "\n\n"

        # Segunda rodada — streaming para resposta final
        response2 = chat.send_message(result_parts, stream=True)
        for chunk in response2:
            chunk_text = ""
            try:
                for candidate in chunk.candidates:
                    for part in candidate.content.parts:
                        try:
                            if part.text:
                                chunk_text += part.text
                        except AttributeError:
                            pass
            except Exception:
                pass
            if chunk_text:
                yield chunk_text
