"""
state/cycle_state.py
────────────────────
CycleState es el estado compartido de todo el grafo LangGraph.
Cada nodo lee y escribe sobre este objeto.

LangGraph persiste este estado en el checkpointer entre interrupciones,
lo que permite que el ciclo sobreviva a reinicios y espere aprobación
humana por horas o días sin perder contexto.

Convención de campos:
  - challenge_*   → datos del desafío ingresado por el PO
  - plan_*        → plan generado por el orquestador
  - <fase>_*      → outputs de cada agente
  - hitl_*        → control del flujo Human-in-the-Loop
  - jira_*        → IDs de tickets creados en Jira
  - error_*       → manejo de errores y reintentos
"""

from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
import operator


# Tipo de fase del ciclo — controla qué checkpoint HITL está activo
PhaseName = Literal[
    "init",
    "prd",
    "ux_arch",
    "dev",
    "qa",
    "infra_sec",
    "done",
]


class CycleState(TypedDict):
    # ──────────────────────────────────────────────────────────────────────────
    # CHALLENGE — input del PO
    # ──────────────────────────────────────────────────────────────────────────
    challenge_name: str
    """Nombre corto del challenge, ej: 'FraudShield'"""

    challenge_type: Literal["greenfield", "brownfield"]
    """Tipo de challenge elegido por el equipo."""

    challenge_description: str
    """Descripción completa del problema a resolver."""

    challenge_success_criteria: list[str]
    """Lista de criterios de éxito medibles."""

    # ──────────────────────────────────────────────────────────────────────────
    # PLAN — generado por el orquestador
    # ──────────────────────────────────────────────────────────────────────────
    plan_phases: list[dict[str, Any]]
    """
    Plan de fases generado por el orquestador al arrancar.
    Ejemplo:
    [
        {"phase": "prd",      "agent": "prd-agent",       "depends_on": []},
        {"phase": "ux",       "agent": "ux-agent",        "depends_on": ["prd"]},
        {"phase": "arch",     "agent": "architect-agent", "depends_on": ["prd"]},
        {"phase": "dev",      "agent": "dev-agent",       "depends_on": ["prd", "arch"]},
        {"phase": "qa",       "agent": "qa-agent",        "depends_on": ["dev"]},
        {"phase": "infra",    "agent": "infra-agent",     "depends_on": ["qa"]},
        {"phase": "security", "agent": "security-agent",  "depends_on": ["qa"]},
    ]
    """

    current_phase: PhaseName
    """Fase actualmente en ejecución."""

    # ──────────────────────────────────────────────────────────────────────────
    # DELIVERABLES — outputs de cada agente
    # Cada campo es None hasta que el agente correspondiente termina.
    # ──────────────────────────────────────────────────────────────────────────
    prd_content: Optional[str]
    """Contenido completo del PRDSPECS.md generado."""

    ux_content: Optional[str]
    """Contenido completo del UXSPECS.md generado."""

    arch_content: Optional[str]
    """Contenido completo del ARQSPECS.md generado."""

    dev_content: Optional[str]
    """Contenido completo del DEVSPECS.md generado."""

    dev_pr_url: Optional[str]
    """URL del Pull Request abierto en GitHub por el dev-agent."""

    qa_content: Optional[str]
    """Contenido completo del QASCPECS.md generado."""

    qa_passed: Optional[bool]
    """True si QA aprobó todos los criterios, False si encontró blockers."""

    infra_content: Optional[str]
    """Contenido completo del INFESPEOS.md generado."""

    security_content: Optional[str]
    """Contenido completo del DEVSECOPS.md generado."""

    # ──────────────────────────────────────────────────────────────────────────
    # HITL — Human-in-the-Loop control
    # ──────────────────────────────────────────────────────────────────────────
    hitl_pending_phase: Optional[PhaseName]
    """
    Fase que está esperando aprobación humana.
    Cuando el webhook de Slack recibe la aprobación, lee este campo
    para saber qué thread_id reanudar.
    """

    hitl_decisions: Annotated[list[dict[str, Any]], operator.add]
    """
    Historial de decisiones HITL. Cada entrada:
    {
        "phase":     "prd",
        "reviewer":  "po",
        "decision":  "approve" | "reject",
        "feedback":  "Agregar criterio de latencia",
        "timestamp": "2026-04-22T10:30:00Z"
    }
    Usa operator.add para que múltiples nodos puedan appender sin conflicto.
    """

    hitl_slack_ts: Optional[str]
    """
    Timestamp del mensaje de Slack enviado para HITL.
    Se usa para actualizar el mensaje cuando el humano aprueba/rechaza
    (reemplaza los botones con un indicador de decisión).
    """

    # ──────────────────────────────────────────────────────────────────────────
    # JIRA — tracking de tickets
    # ──────────────────────────────────────────────────────────────────────────
    jira_epic_key: Optional[str]
    """Key del Epic creado al inicio, ej: 'MACH-42'"""

    jira_story_keys: Annotated[list[str], operator.add]
    """Keys de las Stories/Tasks creadas por cada agente."""

    # ──────────────────────────────────────────────────────────────────────────
    # ERRORES Y REINTENTOS
    # ──────────────────────────────────────────────────────────────────────────
    error_phase: Optional[PhaseName]
    """Fase donde ocurrió el último error."""

    error_message: Optional[str]
    """Mensaje del último error."""

    retry_count: int
    """Número de reintentos del nodo actual. El orquestador limita a 3."""

    # ──────────────────────────────────────────────────────────────────────────
    # METADATA
    # ──────────────────────────────────────────────────────────────────────────
    thread_id: str
    """
    ID del thread de LangGraph. Persiste el estado del ciclo completo.
    Se genera al arrancar y se comparte con el webhook de Slack para
    que los botones de aprobación sepan qué ciclo reanudar.
    """

    cycle_start_time: Optional[str]
    """ISO timestamp del inicio del ciclo."""

    cycle_end_time: Optional[str]
    """ISO timestamp del fin del ciclo (solo cuando current_phase == 'done')."""


def initial_state(
    thread_id: str,
    challenge_name: str,
    challenge_type: Literal["greenfield", "brownfield"],
    challenge_description: str,
    challenge_success_criteria: list[str],
) -> CycleState:
    """
    Crea el estado inicial del ciclo con todos los campos requeridos.
    Llamar esto antes de invocar el grafo por primera vez.
    """
    return CycleState(
        # Challenge
        challenge_name=challenge_name,
        challenge_type=challenge_type,
        challenge_description=challenge_description,
        challenge_success_criteria=challenge_success_criteria,
        # Plan (el orquestador lo llenará en su primer nodo)
        plan_phases=[],
        current_phase="init",
        # Deliverables — vacíos hasta que cada agente corra
        prd_content=None,
        ux_content=None,
        arch_content=None,
        dev_content=None,
        dev_pr_url=None,
        qa_content=None,
        qa_passed=None,
        infra_content=None,
        security_content=None,
        # HITL
        hitl_pending_phase=None,
        hitl_decisions=[],
        hitl_slack_ts=None,
        # Jira
        jira_epic_key=None,
        jira_story_keys=[],
        # Errores
        error_phase=None,
        error_message=None,
        retry_count=0,
        # Metadata
        thread_id=thread_id,
        cycle_start_time=None,
        cycle_end_time=None,
    )
