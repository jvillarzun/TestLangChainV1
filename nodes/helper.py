from pathlib import Path
from state.cycle_state import CycleState


def _get_last_feedback(state: CycleState, phase: str) -> str | None:
    """Extrae feedback del último rechazo HITL para esta fase."""
    decisions = state.get("hitl_decisions", [])
    for decision in reversed(decisions):
        if decision.get("phase") == phase and decision.get("decision") == "reject":
            return decision.get("feedback")
    return None


def load_prompt(agent: str, **kwargs) -> str:
    """
    Carga el prompt de nodes/<agent>/<agent>_prompt.md e interpola variables.

    Uso:
        prompt = load_prompt("prd", challenge_name="FraudShield", ...)

    Las variables en el MD usan sintaxis {variable_name}.
    Llaves literales en código deben escaparse como {{ y }}.
    Si una variable no se pasa, queda sin sustituir (SafeMapping).
    """
    prompt_path = Path(__file__).parent / agent / f"{agent}_prompt.md"
    template = prompt_path.read_text(encoding="utf-8")
    if not kwargs:
        return template
    # SafeMapping: keys faltantes quedan como {key} en vez de lanzar KeyError
    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"
    return template.format_map(_Safe(kwargs))