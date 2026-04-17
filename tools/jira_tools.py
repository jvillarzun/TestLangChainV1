"""
tools/jira_tools.py
────────────────────
Herramientas de Jira para el ciclo ADLC.

Cada fase del ciclo crea automáticamente los tickets correspondientes:
  - Inicio del ciclo → Epic
  - PRD             → Story con el PRDSPECS como descripción
  - UX + ARQ        → 2 Stories en paralelo
  - DEV             → Task con link al PR de GitHub
  - QA              → Task con el resultado del sign-off
  - INFRA + SEC     → 2 Tasks en paralelo
  - Fin del ciclo   → Epic cerrado

Se usa la librería `jira` (python-jira) que conecta al REST API de Jira Cloud.
"""

from datetime import datetime
from jira import JIRA, JIRAError

from config.settings import JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY


# Singleton del cliente Jira
def _get_client() -> JIRA:
    return JIRA(
        server=JIRA_SERVER,
        basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN),
    )


# ── Tipos de issues ───────────────────────────────────────────────────────────
# Ajustar según la configuración del proyecto Jira de MACHBank
ISSUE_TYPES = {
    "epic":  "Epic",
    "story": "Story",
    "task":  "Task",
    "bug":   "Bug",
}


def create_epic(
    challenge_name: str,
    challenge_description: str,
    thread_id: str,
) -> str | None:
    """
    Crea el Epic principal del challenge al inicio del ciclo.
    Retorna el key del Epic (ej: 'MACH-42') o None si falla.
    """
    try:
        jira = _get_client()
        issue = jira.create_issue(fields={
            "project":     {"key": JIRA_PROJECT_KEY},
            "issuetype":   {"name": ISSUE_TYPES["epic"]},
            "summary":     f"[MACH Race] {challenge_name}",
            "description": _build_description(
                f"{challenge_description}\n\nCiclo ID: {thread_id}\nIniciado: {_now()}"
            ),
        })
        print(f"[Jira] Epic creado: {issue.key}")
        return issue.key
    except JIRAError as e:
        print(f"[Jira] Error al crear Epic: {e.text}")
        return None


def create_story(
    phase: str,
    summary: str,
    description: str,
    epic_key: str | None = None,
    labels: list[str] | None = None,
) -> str | None:
    """
    Crea una Story para una fase del ciclo.
    La vincula al Epic si se proporciona epic_key.

    phase: nombre de la fase ('prd', 'ux', 'arch', 'dev', 'qa', 'infra', 'sec')
    """
    try:
        jira = _get_client()
        fields: dict = {
            "project":     {"key": JIRA_PROJECT_KEY},
            "issuetype":   {"name": ISSUE_TYPES["story"]},
            "summary":     f"[{phase.upper()}] {summary}",
            "description": _build_description(description),
        }

        # Vincular al Epic si existe
        if epic_key:
            fields["parent"] = {"key": epic_key}

        issue = jira.create_issue(fields=fields)
        print(f"[Jira] Story creada: {issue.key} ({phase})")
        return issue.key
    except JIRAError as e:
        print(f"[Jira] Error al crear Story para {phase}: {e.text}")
        return None


def create_task(
    phase: str,
    summary: str,
    description: str,
    parent_key: str | None = None,
    pr_url: str | None = None,
) -> str | None:
    """
    Crea una Task para operaciones más específicas (DEV, QA, INFRA, SEC).
    Opcionalmente incluye el link al PR de GitHub.
    """
    try:
        jira = _get_client()

        # Agregar link al PR si existe
        full_description = description
        if pr_url:
            full_description += f"\n\nPull Request: {pr_url}"

        fields: dict = {
            "project":     {"key": JIRA_PROJECT_KEY},
            "issuetype":   {"name": ISSUE_TYPES["task"]},
            "summary":     f"[{phase.upper()}] {summary}",
            "description": _build_description(full_description),
        }

        if parent_key:
            fields["parent"] = {"key": parent_key}

        issue = jira.create_issue(fields=fields)
        print(f"[Jira] Task creada: {issue.key} ({phase})")
        return issue.key
    except JIRAError as e:
        print(f"[Jira] Error al crear Task para {phase}: {e.text}")
        return None


def update_issue_status(issue_key: str, transition_name: str) -> bool:
    """
    Transiciona un issue al estado indicado.
    transition_name: 'In Progress', 'Done', 'Failed', etc.
    (Los nombres exactos dependen del workflow del proyecto Jira)
    """
    try:
        jira = _get_client()
        transitions = jira.transitions(issue_key)
        transition_id = next(
            (t["id"] for t in transitions if t["name"] == transition_name),
            None
        )
        if not transition_id:
            print(f"[Jira] Transición '{transition_name}' no encontrada para {issue_key}")
            return False
        jira.transition_issue(issue_key, transition_id)
        print(f"[Jira] {issue_key} → {transition_name}")
        return True
    except JIRAError as e:
        print(f"[Jira] Error al transicionar {issue_key}: {e.text}")
        return False


def add_comment(issue_key: str, comment: str) -> bool:
    """Agrega un comentario a un issue existente."""
    try:
        jira = _get_client()
        jira.add_comment(issue_key, comment)
        return True
    except JIRAError as e:
        print(f"[Jira] Error al comentar {issue_key}: {e.text}")
        return False


def close_epic(epic_key: str, summary: str) -> bool:
    """Cierra el Epic al finalizar el ciclo."""
    comment = f"Ciclo ADLC completado. {summary}\n{_now()}"
    add_comment(epic_key, comment)
    return update_issue_status(epic_key, "Done")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_description(text: str) -> str:
    return text


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
