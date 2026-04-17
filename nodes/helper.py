from state.cycle_state import CycleState

# ── Helper ────────────────────────────────────────────────────────────────────

def _get_last_feedback(state: CycleState, phase: str) -> str | None:
    """
    Extrae el feedback del último rechazo HITL para esta fase.
    Permite que el agente incorpore las correcciones solicitadas.
    """
    decisions = state.get("hitl_decisions", [])
    for decision in reversed(decisions):
        if decision.get("phase") == phase and decision.get("decision") == "reject":
            return decision.get("feedback")
    return None