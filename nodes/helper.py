from pathlib import Path
from typing import Any
from state.cycle_state import CycleState

_OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"


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


def create_llm(model: str) -> Any:
    """Crea instancia LLM. Único lugar para cambiar proveedor (actualmente Groq)."""
    from langchain_groq import ChatGroq
    from config.settings import GROQ_API_KEY
    return ChatGroq(model=model, api_key=GROQ_API_KEY)


def llm_invoke(model: str, system_prompt: str, user_message: str, stub_content: str) -> str:
    """
    Wrapper de llamada LLM con soporte TEST_MODE.

    En TEST_MODE retorna stub_content directamente sin llamar al LLM.
    En modo normal llama al modelo y retorna response.content.
    Lanza la excepción si el LLM falla (el nodo hace el try/except).
    """
    from config.settings import TEST_MODE
    if TEST_MODE:
        print("   [TEST_MODE] Usando stub — no se llama al LLM")
        return stub_content

    from langchain_core.messages import SystemMessage, HumanMessage
    llm = create_llm(model)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])
    return response.content


def get_phase_instructions(state: "CycleState", phase: str) -> str:
    """Extrae instrucciones del orquestador para esta fase desde plan_phases."""
    for p in state.get("plan_phases", []):
        if p.get("phase") == phase:
            return p.get("instructions", "")
    return ""


def save_output(filename: str, content: str) -> Path:
    """Guarda contenido en outputs/<filename>. Crea la carpeta si no existe."""
    _OUTPUTS_DIR.mkdir(exist_ok=True)
    path = _OUTPUTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path