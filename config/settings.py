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
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]

# Modelos por agente
MODEL_ORCHESTRATOR = "gemini-2.0-flash-lite"
MODEL_PRD          = "gemini-2.0-flash"
MODEL_UX           = "gemini-2.0-flash"
MODEL_ARCHITECT    = "gemini-2.0-flash"
MODEL_DEV          = "gemini-2.0-flash"   # Claude Code usa su propio runtime
MODEL_QA           = "gemini-2.0-flash"
MODEL_INFRA        = "gemini-2.0-flash"
MODEL_SECURITY     = "gemini-2.0-flash"


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


# ── Checkpointing ──────────────────────────────────────────────────────────────
CHECKPOINTER     = os.environ.get("CHECKPOINTER", "memory")
SQLITE_PATH      = os.environ.get("SQLITE_PATH", "./mach_cycle.db")
