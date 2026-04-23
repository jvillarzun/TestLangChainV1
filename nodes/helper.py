import time
from pathlib import Path
from typing import Any
from state.cycle_state import CycleState

_OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"

# Groq pricing $/1M tokens (input, output)
_GROQ_PRICING: dict[str, dict[str, float]] = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant":    {"input": 0.05, "output": 0.08},
}
# OpenAI pricing $/1M tokens (input, output)
_OPENAI_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o":      {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1":     {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini":{"input": 0.40, "output": 1.60},
    "gpt-4.1-nano":{"input": 0.10, "output": 0.40},
}
_PRICING_DEFAULT = {"input": 0.59, "output": 0.79}

_OPENAI_MODELS = set(_OPENAI_PRICING.keys())


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = _GROQ_PRICING.get(model) or _OPENAI_PRICING.get(model) or _PRICING_DEFAULT
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


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
    try:
        return template.format_map(_Safe(kwargs))
    except (KeyError, ValueError) as e:
        # Si falla el format, puede ser que kwargs contenga código con llaves no escapadas
        print(f"⚠️  [load_prompt] Error formateando prompt de '{agent}': {e}")
        print(f"   Hint: Verifica que el contenido de kwargs no tenga {{}} sin escapar")
        print(f"   Keys: {list(kwargs.keys())}")
        raise


def create_llm(model: str) -> Any:
    """
    Crea instancia LLM. Soporta Groq, OpenAI y Google Gemini según el modelo.
    Único lugar para cambiar proveedor.
    """
    # OpenAI models
    if model in _OPENAI_MODELS:
        from langchain_openai import ChatOpenAI
        from config.settings import OPENAI_API_KEY
        return ChatOpenAI(model=model, api_key=OPENAI_API_KEY)

    # Google Gemini models
    if "gemini" in model:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config.settings import GOOGLE_API_KEY
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
            convert_system_message_to_human=True,
        )

    # Default: Groq
    from langchain_groq import ChatGroq
    from config.settings import GROQ_API_KEY
    return ChatGroq(model=model, api_key=GROQ_API_KEY)


def llm_invoke(model: str, system_prompt: str, user_message: str, stub_content: str) -> tuple[str, dict]:
    """
    Wrapper de llamada LLM con soporte TEST_MODE.
    Retorna (content, usage_dict). El caller agrega "agent" al usage_dict.

    En TEST_MODE retorna stub_content con usage en ceros.
    Lanza la excepción si el LLM falla (el nodo hace el try/except).
    """
    _zero_usage = {"model": model, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "duration_s": 0.0}

    from config.settings import TEST_MODE
    if TEST_MODE:
        print("   [TEST_MODE] Usando stub — no se llama al LLM")
        return stub_content, _zero_usage

    from langchain_core.messages import SystemMessage, HumanMessage
    llm = create_llm(model)
    t0 = time.time()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])
    duration = round(time.time() - t0, 2)

    meta = response.usage_metadata or {}
    input_tokens  = meta.get("input_tokens", 0)
    output_tokens = meta.get("output_tokens", 0)
    total_tokens  = meta.get("total_tokens", input_tokens + output_tokens)

    usage = {
        "model":         model,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "total_tokens":  total_tokens,
        "cost_usd":      round(_calc_cost(model, input_tokens, output_tokens), 6),
        "duration_s":    duration,
    }
    return response.content, usage


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