"""
nodes/agent_nodes.py
─────────────────────
Nodos placeholder para los 7 agentes especializados.

En esta primera versión (Paso 1 del ADLC) estos nodos son stubs
que simulan el trabajo del agente. En las siguientes iteraciones
cada nodo invocará al LLM correspondiente con las skills inyectadas.

Cada nodo:
  1. Lee el contexto necesario del estado (outputs de fases previas)
  2. Obtiene el feedback del último HITL si la fase fue rechazada
  3. Invoca al agente (stub por ahora)
  4. Guarda el resultado en el estado
  5. Crea el ticket en Jira
"""

from state.cycle_state import CycleState
from tools.jira_tools import create_story
from nodes.helper import _get_last_feedback, load_prompt

# ── UX + ARQ Agents (paralelo) ─────────────────────────────────────────────────

def run_ux_node(state: CycleState) -> dict:
    """Nodo UX — invoca al ux-agent (Gemini Pro). Genera UXSPECS.md."""
    print("\n🎨 UX-AGENT: Generando UXSPECS.md...")

    feedback = _get_last_feedback(state, "ux")
    system_prompt = load_prompt(
        "ux",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    # STUB
    ux_content = f"""# UXSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Flujos principales
1. Flujo de pago → scoring → resultado (aprobado/rechazado)
2. Pantalla de rechazo con explicación en lenguaje natural
3. Dashboard del analista de riesgo

## Wireframes
[Wireframes en ASCII omitidos en este stub]
"""
    story_key = create_story(
        phase="ux",
        summary=f"{state['challenge_name']} — UX Specs",
        description=ux_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ UXSPECS.md generado")
    return {
        "ux_content":      ux_content,
        "jira_story_keys": [story_key] if story_key else [],
    }