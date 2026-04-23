"""
nodes/hitl_node.py
───────────────────
Dos nodos por checkpoint HITL:

  hitl_notify_{phase}  → envía DM Slack, guarda ts+channel en state, retorna dict
  hitl_{phase}         → lee ts+channel del state, llama interrupt(), procesa respuesta

Separar en dos nodos evita el problema de LangGraph replay:
cuando se reanuda con Command(resume=...), solo se re-ejecuta hitl_{phase}
(el nodo interrumpido), no hitl_notify_{phase} (ya completado y guardado en checkpoint).
Así no se mandan DMs duplicados en el replay.
"""

from datetime import datetime
from langgraph.types import interrupt, Command

from state.cycle_state import CycleState
from tools.slack_tools import (
    notify_reviewer,
    update_hitl_message,
    PHASE_HITL_CONFIG,
)


def make_hitl_notify_node(phase: str):
    """
    Nodo que envía el DM de Slack y guarda ts+channel en el estado.
    Se ejecuta UNA VEZ — no se repite en el replay del interrupt.
    """

    def hitl_notify_node(state: CycleState) -> dict:
        print(f"\n📩 HITL notify: {phase} — enviando DM a Slack...")

        deliverable_content, extra_context = _get_deliverable_for_phase(state, phase)

        slack_ts, slack_channel = notify_reviewer(
            phase=phase,
            thread_id=state["thread_id"],
            deliverable_content=deliverable_content,
            extra_context=extra_context,
        )
        print(f"   DM enviado (ts={slack_ts}, channel={slack_channel})")

        return {
            "hitl_slack_ts":      slack_ts,
            "hitl_slack_channel": slack_channel,
            "hitl_pending_phase": phase,
        }

    hitl_notify_node.__name__ = f"hitl_notify_{phase}_node"
    return hitl_notify_node


def make_hitl_node(phase: str):
    """
    Nodo HITL que llama interrupt() y procesa la respuesta humana.
    En el replay (Command resume), interrupt() retorna el valor directamente
    sin pausar — y ts+channel ya están en el state desde el notify node.
    """

    def hitl_node(state: CycleState) -> Command:
        print(f"\n⏸️  HITL interrupt: {phase} — esperando decisión...")

        slack_ts      = state.get("hitl_slack_ts")
        slack_channel = state.get("hitl_slack_channel")

        # interrupt() pausa el grafo en la primera ejecución.
        # En el replay (resume), retorna el payload directamente.
        human_response = interrupt({
            "phase":       phase,
            "thread_id":   state["thread_id"],
            "waiting_for": PHASE_HITL_CONFIG.get(phase, {}).get("reviewer_role"),
            "deliverable": PHASE_HITL_CONFIG.get(phase, {}).get("deliverable"),
            "slack_ts":    slack_ts,
            "timestamp":   datetime.now().isoformat(),
        })

        decision = human_response.get("decision", "approve")
        feedback = human_response.get("feedback")
        reviewer = human_response.get("reviewer", "unknown")

        print(f"   {'✅' if decision == 'approve' else '🔄'} Decisión: {'Aprobado' if decision == 'approve' else 'Rehacer fase'}")
        if feedback:
            print(f"   💬 Feedback: {feedback}")

        # Actualizar mensaje Slack — quitar botones, mostrar resultado
        if slack_ts and slack_channel:
            update_hitl_message(
                channel=slack_channel,
                ts=slack_ts,
                phase=phase,
                decision=decision,
                feedback=feedback,
            )

        decision_record = {
            "phase":     phase,
            "reviewer":  reviewer,
            "decision":  decision,
            "feedback":  feedback,
            "timestamp": datetime.now().isoformat(),
        }

        if decision == "approve":
            # current_phase avanza → conditional edge en el grafo rutea al agente siguiente
            return Command(
                update={
                    "hitl_decisions":     [decision_record],
                    "hitl_pending_phase": None,
                    "hitl_slack_ts":      None,
                    "hitl_slack_channel": None,
                    "current_phase":      _next_phase(phase),
                    "retry_count":        0,
                },
            )
        else:
            # current_phase se mantiene → conditional edge rutea de vuelta al mismo agente
            return Command(
                update={
                    "hitl_decisions":     [decision_record],
                    "hitl_pending_phase": phase,
                    "hitl_slack_ts":      None,
                    "hitl_slack_channel": None,
                    "retry_count":        state["retry_count"] + 1,
                },
            )

    hitl_node.__name__ = f"hitl_{phase}_node"
    return hitl_node


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_deliverable_for_phase(state: CycleState, phase: str) -> tuple[str | None, str | None]:
    mapping = {
        "prd":   (state.get("prd_content"),      None),
        "ux":    (state.get("ux_content"),        None),
        "arch":  (state.get("arch_content"),      None),
        "dev":   (state.get("dev_content"),       _format_pr_links(state)),
        "qa":    (state.get("qa_content"),        None),
        "infra": (state.get("infra_content"),     None),
        "sec":   (state.get("security_content"),  None),
    }
    return mapping.get(phase, (None, None))


def _format_pr_links(state: CycleState) -> str:
    pr_urls: list[str] = list(state.get("dev_pr_urls") or [])
    first = state.get("dev_pr_url")
    if first and first not in pr_urls:
        pr_urls.insert(0, first)
    if not pr_urls:
        return "⚠️ *No se abrieron PRs* — revisar logs del ciclo DEV"
    lines = ["*PRs abiertos en GitHub:*"]
    for url in pr_urls:
        lines.append(f"• <{url}|Ver PR>")
    return "\n".join(lines)


def _next_phase(phase: str) -> str:
    return {
        "prd":   "ux",
        "ux":    "arch",
        "arch":  "dev",
        "dev":   "qa",
        "qa":    "infra",
        "infra": "sec",
        "sec":   "done",
    }.get(phase, "done")
