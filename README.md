# 📊 Gestor de Tráfego Pago com IA

Plataforma completa para gestão de campanhas Meta ADS com análise e otimização por IA (Claude).

## Funcionalidades

- 🔗 **Conexão com todos os BMs** via Meta OAuth
- 📊 **Dashboard consolidado** com métricas de todas as campanhas
- 🤖 **IA integrada** (Claude claude-opus-4-6) para análise e sugestões de otimização
- ✅ **Aprovação humana** antes de qualquer ação automática
- 🔗 **API REST para N8N** com autenticação por API Key
- 📄 **Exportação PDF** de relatórios profissionais

## Configuração

### 1. Pré-requisitos

- Docker e Docker Compose instalados
- [Conta na Anthropic](https://console.anthropic.com) com API Key
- App no [Meta for Developers](https://developers.facebook.com) com permissões:
  - `business_management`
  - `ads_management`
  - `ads_read`

### 2. Variáveis de ambiente

```bash
cp backend/.env.example backend/.env
```

Edite `backend/.env`:

```env
META_APP_ID=seu_app_id
META_APP_SECRET=seu_app_secret
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Rodar localmente

```bash
docker-compose up -d
```

Acesse: http://localhost:3000

### 4. Deploy no EasyPanel (VPS)

1. No EasyPanel, crie um serviço **PostgreSQL** e copie a `DATABASE_URL`
2. Crie um novo serviço → selecione **Docker Compose**
3. Conecte ao repositório GitHub: `rafaelruch/trafego-pago`
4. Selecione `docker-compose.prod.yml`
5. Configure as variáveis de ambiente:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `postgres://user:pass@host:5432/gestor_trafego` |
| `META_APP_ID` | ID do seu App Meta |
| `META_APP_SECRET` | Secret do seu App Meta |
| `META_REDIRECT_URI` | `https://seudominio.com/api/auth/callback` |
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `SECRET_KEY` | String aleatória longa |
| `CORS_ORIGINS` | `["https://seudominio.com"]` |
| `NEXT_PUBLIC_API_URL` | `https://api.seudominio.com` |

## Uso com N8N

### 1. Gere uma API Key no painel

Vá em **Configurações → API Keys → Criar**

### 2. Configure o header no N8N

```
X-API-Key: sua_chave_aqui
```

### 3. Endpoints disponíveis

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/reports/n8n/campaigns` | Dados JSON das campanhas |
| GET | `/api/reports/n8n/summary` | Resumo de métricas |
| GET | `/api/reports/n8n/pdf` | PDF do relatório |

**Parâmetro opcional:** `?date_preset=last_7d` (opções: `last_7d`, `last_30d`, `this_month`, `last_month`)

### Exemplo de uso no N8N (HTTP Request)

```
URL: https://seudominio.com/api/reports/n8n/campaigns?date_preset=last_30d
Method: GET
Headers: X-API-Key: sua_chave_aqui
```

## Estrutura do Projeto

```
gestor-trafego/
├── backend/          # FastAPI + Python
│   ├── app/
│   │   ├── api/      # Endpoints REST
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Meta, Claude, PDF
│   └── main.py
├── frontend/         # Next.js 14 + TypeScript
│   └── src/
│       ├── app/      # Páginas
│       └── components/
├── docker-compose.yml       # Dev local
└── docker-compose.prod.yml  # VPS/EasyPanel
```

## Documentação da API

Com o servidor rodando, acesse:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
