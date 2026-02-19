import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.database import create_tables
from app.models import user, approval, insight_cache  # noqa: importa modelos para criar tabelas
from app.api import auth, campaigns, ai, approvals, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria tabelas no banco ao iniciar (idempotente)
create_tables()

# Log de diagnóstico de configuração (sem dados sensíveis)
logger.info("=== CONFIGURAÇÃO DO BACKEND ===")
logger.info(f"ENVIRONMENT: {settings.ENVIRONMENT}")
logger.info(f"META_APP_ID: {'OK (' + settings.META_APP_ID[:4] + '...)' if settings.META_APP_ID else 'NÃO CONFIGURADO!'}")
logger.info(f"META_APP_SECRET: {'OK' if settings.META_APP_SECRET else 'NÃO CONFIGURADO!'}")
logger.info(f"META_REDIRECT_URI: {settings.META_REDIRECT_URI}")
logger.info(f"FRONTEND_URL: {settings.FRONTEND_URL}")
logger.info(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")
logger.info("================================")

app = FastAPI(
    title="Gestor de Tráfego Pago API",
    description="""
## Plataforma de Gestão de Tráfego Pago com IA

### Autenticação
- **Painel**: Login via Meta OAuth → JWT Bearer token
- **N8N/Integrações**: Header `X-API-Key: sua_chave` (gere no painel em Configurações → API Keys)

### Endpoints N8N
- `GET /api/reports/n8n/campaigns` — Dados JSON de campanhas
- `GET /api/reports/n8n/summary` — Resumo de métricas
- `GET /api/reports/n8n/pdf` — PDF do relatório pronto para enviar
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["🔐 Autenticação"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["📊 Campanhas"])
app.include_router(ai.router, prefix="/api/ai", tags=["🤖 IA"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["✅ Aprovações"])
app.include_router(reports.router, prefix="/api/reports", tags=["📄 Relatórios"])


@app.get("/", tags=["Status"])
def root():
    return {
        "service": "Gestor de Tráfego Pago API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Status"])
def health():
    return {"status": "healthy"}
