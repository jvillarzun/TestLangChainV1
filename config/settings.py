"""
config/settings.py
──────────────────
Configuración centralizada. Todas las variables de entorno
se leen aquí y se exponen como constantes tipadas.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── LLMs ──────────────────────────────────────────────────────────────────────
# TEST_MODE=true → nodos usan stubs, no llaman al LLM. Ideal para probar HITL/Slack/Jira.
TEST_MODE: bool = os.environ.get("TEST_MODE", "false").lower() == "true"

# MOCK_EARLY_AGENTS=true → PRD y UX usan archivos estáticos en lugar de LLM
# Útil para probar solo DEV/QA/etc sin gastar tokens en fases tempranas
MOCK_EARLY_AGENTS: bool = os.environ.get("MOCK_EARLY_AGENTS", "false").lower() == "true"

GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "") if not TEST_MODE else "test"  # legacy, no usado
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")  # reservado para P3 dev-agent
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "") if not TEST_MODE else "test"  # Motor LLM principal
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "") if not TEST_MODE else "test"  # OpenAI (opcional)

# Modelos por agente
MODEL_ORCHESTRATOR = "llama-3.1-8b-instant"       # routing simple, modelo ligero y rápido
MODEL_PRD          = "llama-3.3-70b-versatile"       # generación de PRD
MODEL_UX           = "llama-3.3-70b-versatile"       # diseño de UX
MODEL_ARCHITECT    = "gemini-2.5-flash"       # arquitectura y engineering plan (Gemini 2.5 Flash)
MODEL_DEV          = "gemini-2.5-flash"       # generación de código (Gemini 2.5 Flash)
MODEL_QA           = "llama-3.3-70b-versatile"       # testing y QA
MODEL_INFRA        = "llama-3.3-70b-versatile"       # infraestructura
MODEL_SECURITY     = "llama-3.3-70b-versatile"       # seguridad

# ── Multi-Provider Support (Arch & Dev) ───────────────────────────────────────
# Permite cambiar entre "gemini" y "openai" sin tocar código
LLM_PROVIDER_ARCH  = os.environ.get("LLM_PROVIDER_ARCH", "gemini")     # "gemini" o "openai"
LLM_MODEL_ARCH     = os.environ.get("LLM_MODEL_ARCH", "gemini-2.5-flash")  # o "gpt-4o-mini", "gpt-4o"

LLM_PROVIDER_DEV   = os.environ.get("LLM_PROVIDER_DEV", "gemini")      # "gemini" o "openai"
LLM_MODEL_DEV      = os.environ.get("LLM_MODEL_DEV", "gemini-2.5-flash")   # o "gpt-4o-mini", "gpt-4o"


# ── Slack ──────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN      = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_TEAM_CHANNEL   = os.environ.get("SLACK_TEAM_CHANNEL", "#mach-race-2026")

# User IDs por rol — el orquestador envía DM directo a la persona correcta
SLACK_USERS = {
    "po":        os.environ.get("SLACK_USER_PO", ""),
    "architect": os.environ.get("SLACK_USER_ARCHITECT", ""),
    "dev_lead":  os.environ.get("SLACK_USER_DEV_LEAD", ""),
    "qa_lead":   os.environ.get("SLACK_USER_QA_LEAD", ""),
    "devops":    os.environ.get("SLACK_USER_DEVOPS", ""),
}


# ── Jira ───────────────────────────────────────────────────────────────────────
JIRA_SERVER      = os.environ["JIRA_SERVER"]
JIRA_EMAIL       = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN   = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "MACH")


# ── Webhook ────────────────────────────────────────────────────────────────────
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "http://localhost:8000")
WEBHOOK_PORT     = int(os.environ.get("WEBHOOK_PORT", "8000"))
DASHBOARD_URL    = os.environ.get("DASHBOARD_URL", "http://localhost:8501")


# ── Checkpointing ──────────────────────────────────────────────────────────────
CHECKPOINTER     = os.environ.get("CHECKPOINTER", "memory")
SQLITE_PATH      = os.environ.get("SQLITE_PATH", "./mach_cycle.db")


# ── GitHub ───────────────────────────────────────────────────────────────
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
REPO_BE_NAME    = os.environ.get("REPO_BE_NAME", "mach-backend-test-hackathon")
REPO_FE_NAME    = os.environ.get("REPO_FE_NAME", "mach-frontend-test-hackathon")