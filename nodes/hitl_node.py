"""
nodes/hitl_node.py
───────────────────
Nodo Human-in-the-Loop usando el mecanismo nativo de LangGraph.

Flujo completo de un checkpoint HITL:

  1. El agente anterior terminó y guardó su output en el estado
  2. El orquestador llama a este nodo
  3. Este nodo envía un DM a Slack con botones Aprobar/Rechazar
  4. interrupt() pausa el grafo — el estado queda guardado en el checkpointer
  5. El revisor hace click en el botón en Slack
  6. El webhook de FastAPI (api/slack_webhook.py) recibe el payload
  7. El webhook llama a graph.invoke(Command(resume=payload), config)
  8. LangGraph reanuda la ejecución desde AQUÍ — el return value de interrupt()
     es el payload enviado por el webhook
  9. Se registra la decisión en hitl_decisions
  10. Se actualiza el mensaje de Slack con el resultado
  11. El grafo avanza a la siguiente fase o re-ejecuta el agente

NOTA sobre interrupt() vs interrupt_before:
  - interrupt_before: pausa ANTES de que el nodo empiece (estático, en compile())
  - interrupt():      pausa DENTRO del nodo (dinámico, más flexible)
  Usamos interrupt() porque necesitamos enviar el DM de Slack ANTES de pausar.
"""

from datetime import datetime
from langgraph.types import interrupt, Command

from state.cycle_state import CycleState
from tools.slack_tools import (
    notify_reviewer,
    update_hitl_message,
    PHASE_HITL_CONFIG,
)


def make_hitl_node(phase: str):
    """
    Factory que crea un nodo HITL para una fase específica.
    Usar así en el grafo:
        builder.add_node("hitl_prd", make_hitl_node("prd"))

    Retorna una función que LangGraph ejecutará como nodo.
    """

    def hitl_node(state: CycleState) -> Command:
        """
        Nodo HITL para la fase '{phase}'.

        1. Determina qué contenido mostrar al revisor
        2. Envía DM en Slack con botones
        3. Pausa con interrupt() — espera la respuesta
        4. Procesa la respuesta (approve/reject + feedback)
        5. Actualiza el mensaje de Slack
        6. Retorna Command(goto=...) para el routing
        """
        print(f"\n⏸️  HITL checkpoint: {phase} — enviando DM a Slack...")

        # ── 1. Obtener el contenido del entregable según la fase ──────────────
        deliverable_content, extra_context = _get_deliverable_for_phase(state, phase)

        # ── 2. Enviar DM en Slack con botones Aprobar/Rechazar ────────────────
        slack_ts = notify_reviewer(
            phase=phase,
            thread_id=state["thread_id"],
            deliverable_content=deliverable_content,
            extra_context=extra_context,
        )
        print(f"   📩 DM enviado (ts={slack_ts})")

        # ── 3. PAUSAR — interrupt() suspende el grafo aquí ───────────────────
        # El value del interrupt es lo que se muestra en la interfaz
        # (útil si tienes un dashboard que monitorea el estado del ciclo)
        human_response = interrupt({
            "phase":         phase,
            "thread_id":     state["thread_id"],
            "waiting_for":   PHASE_HITL_CONFIG.get(phase, {}).get("reviewer_role"),
            "deliverable":   PHASE_HITL_CONFIG.get(phase, {}).get("deliverable"),
            "slack_ts":      slack_ts,
            "timestamp":     datetime.now().isoformat(),
        })

        # ── TODO: hasta aquí llega la primera ejecución
        # ── El código de abajo se ejecuta DESPUÉS de que el webhook
        # ── llame a graph.invoke(Command(resume=human_response), config)
        # ─────────────────────────────────────────────────────────────────────

        # ── 4. Procesar la respuesta del humano ───────────────────────────────
        # human_response es el dict que envía el webhook de Slack:
        # {
        #   "decision": "approve" | "reject",
        #   "feedback": "texto opcional del revisor",
        #   "reviewer": "slack_user_id",
        #   "timestamp": "ISO string"
        # }
        decision = human_response.get("decision", "approve")
        feedback = human_response.get("feedback")
        reviewer = human_response.get("reviewer", "unknown")

        print(f"   {'✅' if decision == 'approve' else '🔄'} Decisión: {'Aprobado' if decision == 'approve' else 'Rehacer fase'}")
        if feedback:
            print(f"   💬 Feedback: {feedback}")

        # ── 5. Actualizar el mensaje de Slack (quitar botones, mostrar resultado)
        if slack_ts:
            # El canal del DM es el user_id del revisor
            from config.settings import SLACK_USERS
            from tools.slack_tools import PHASE_HITL_CONFIG as cfg
            reviewer_role = cfg.get(phase, {}).get("reviewer_role", "")
            reviewer_channel = SLACK_USERS.get(reviewer_role, "")
            if reviewer_channel:
                update_hitl_message(
                    channel=reviewer_channel,
                    ts=slack_ts,
                    phase=phase,
                    decision=decision,
                    feedback=feedback,
                )

        # ── 6. Registrar la decisión en el historial ──────────────────────────
        decision_record = {
            "phase":     phase,
            "reviewer":  reviewer,
            "decision":  decision,
            "feedback":  feedback,
            "timestamp": datetime.now().isoformat(),
        }

        # ── 7. Routing: ¿aprobado o rechazado? ───────────────────────────────
        if decision == "approve":
            next_node = _next_node_after_approval(phase)
            return Command(
                update={
                    "hitl_decisions":    [decision_record],
                    "hitl_pending_phase": None,
                    "hitl_slack_ts":     None,
                    "current_phase":     _next_phase(phase),
                    "retry_count":       0,
                },
                goto=next_node,
            )
        else:
            # Rechazo: volver a ejecutar el agente de la fase con el feedback
            agent_node = _agent_node_for_phase(phase)
            return Command(
                update={
                    "hitl_decisions":    [decision_record],
                    "hitl_pending_phase": phase,
                    "hitl_slack_ts":     None,
                    "retry_count":       state["retry_count"] + 1,
                    # Inyectar el feedback en las instrucciones del agente
                    # (el agente node lo leerá de hitl_decisions[-1].feedback)
                },
                goto=agent_node,
            )

    hitl_node.__name__ = f"hitl_{phase}_node"
    return hitl_node


# ── Helpers de routing ────────────────────────────────────────────────────────

def _get_deliverable_for_phase(
    state: CycleState,
    phase: str,
) -> tuple[str | None, str | None]:
    """
    Retorna (contenido_del_entregable, contexto_extra) para el DM de Slack.
    """
    mapping = {
        "prd":      (state.get("prd_content"), None),
        "ux_arch":  (state.get("arch_content"), f"*UXSPECS también disponible en /deliverables/UXSPECS.md*"),
        "dev":      (state.get("dev_content"), f"*PR GitHub:* {state.get('dev_pr_url', 'N/A')}"),
        "qa":       (state.get("qa_content"), None),
        "infra_sec":(state.get("infra_content"), f"*Security report también disponible en /deliverables/DEVSECOPS.md*"),
    }
    return mapping.get(phase, (None, None))


def _next_node_after_approval(phase: str) -> str:
    """Nodo siguiente al aprobar cada fase."""
    routing = {
        "prd":       "run_ux_arch_parallel",   # UX + ARQ en paralelo
        "ux_arch":   "run_dev",
        "dev":       "run_qa",
        "qa":        "run_infra_sec_parallel",  # INFRA + SEC en paralelo
        "infra_sec": "finalize",
    }
    return routing.get(phase, "finalize")


def _agent_node_for_phase(phase: str) -> str:
    """Nodo de agente a re-ejecutar si se rechaza la fase."""
    routing = {
        "prd":       "run_prd",
        "ux_arch":   "run_ux_arch_parallel",
        "dev":       "run_dev",
        "qa":        "run_qa",
        "infra_sec": "run_infra_sec_parallel",
    }
    return routing.get(phase, "run_prd")


def _next_phase(phase: str) -> str:
    """Nombre de la fase siguiente (para actualizar current_phase en el estado)."""
    routing = {
        "prd":       "ux_arch",
        "ux_arch":   "dev",
        "dev":       "qa",
        "qa":        "infra_sec",
        "infra_sec": "done",
    }
    return routing.get(phase, "done")
