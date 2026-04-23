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
    Crea instancia LLM. Único lugar para cambiar proveedor.
    
    Actualmente: Google Gemini 1.5 Flash vía LangChain.
    Parámetros optimizados para Gemini:
    - temperature=0.2: Balance entre creatividad y determinismo
    - convert_system_message_to_human=True: Recomendado por Google para mejor compatibilidad
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import GOOGLE_API_KEY
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
        convert_system_message_to_human=True,  # Convierte system messages a formato que Gemini espera
    )


def llm_invoke(model: str, system_prompt: str, user_message: str, stub_content: str, provider: str = "gemini") -> str:
    """
    Wrapper de llamada LLM con soporte TEST_MODE y multi-provider.

    Args:
        model: Nombre del modelo (ej. "gemini-2.5-flash" o "gpt-4o-mini")
        system_prompt: Prompt del sistema
        user_message: Mensaje del usuario
        stub_content: Contenido en TEST_MODE
        provider: "gemini" (default) o "openai"

    En TEST_MODE retorna stub_content directamente sin llamar al LLM.
    En modo normal llama al modelo y retorna response.content.
    Lanza la excepción si el LLM falla (el nodo hace el try/except).
    """
    from config.settings import TEST_MODE
    if TEST_MODE:
        print("   [TEST_MODE] Usando stub — no se llama al LLM")
        return stub_content

    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Seleccionar proveedor
    if provider == "gemini":
        # LÓGICA ORIGINAL DE GEMINI (sin cambios)
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config.settings import GOOGLE_API_KEY
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
            convert_system_message_to_human=True,
        )
    elif provider == "openai":
        # NUEVA OPCIÓN: OpenAI
        from langchain_openai import ChatOpenAI
        from config.settings import OPENAI_API_KEY
        llm = ChatOpenAI(
            model=model,
            api_key=OPENAI_API_KEY,
            temperature=0.2,
        )
    else:
        raise ValueError(f"Proveedor '{provider}' no soportado. Usa 'gemini' u 'openai'.")
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])
    return response.content


def save_output(filename: str, content: str) -> Path:
    """Guarda contenido en outputs/<filename>. Crea la carpeta si no existe."""
    _OUTPUTS_DIR.mkdir(exist_ok=True)
    path = _OUTPUTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path