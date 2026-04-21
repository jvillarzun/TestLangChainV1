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

GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "") if not TEST_MODE else "test"
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")  # reservado para P3 dev-agent
GOOGLE_API_KEY:    str | None = os.environ.get("GOOGLE_API_KEY")     # reservado, no usado actualmente

# Modelos por agente — todos Groq (cambiar aquí, no en los nodos)
MODEL_ORCHESTRATOR = "llama-3.1-8b-instant"       # routing simple, modelo ligero
MODEL_PRD          = "llama-3.3-70b-versatile"
MODEL_UX           = "llama-3.3-70b-versatile"
MODEL_ARCHITECT    = "llama-3.3-70b-versatile"
MODEL_DEV          = "llama-3.3-70b-versatile"
MODEL_QA           = "llama-3.3-70b-versatile"
MODEL_INFRA        = "llama-3.3-70b-versatile"
MODEL_SECURITY     = "llama-3.3-70b-versatile"


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

# ── Feature flags ─────────────────────────────────────────────────────────────
# SHOW_MANUAL_CONTROLS=true → muestra botones Aprobar/Rechazar en el dashboard
SHOW_MANUAL_CONTROLS: bool = os.getenv("SHOW_MANUAL_CONTROLS", "false").lower() == "true"
