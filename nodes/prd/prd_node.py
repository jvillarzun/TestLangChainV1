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
from nodes.helper import _get_last_feedback, load_prompt
from tools.jira_tools import create_story


def run_prd_node(state: CycleState) -> dict:
    """
    Nodo PRD — invoca al prd-agent (Claude Sonnet).
    Lee el challenge y genera PRDSPECS.md.
    """
    print("\n📋 PRD-AGENT: Generando PRDSPECS.md...")

    feedback = _get_last_feedback(state, "prd")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    criteria_str = "\n".join(f"  - {c}" for c in state["challenge_success_criteria"])
    system_prompt = load_prompt(
        "prd",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        challenge_success_criteria=criteria_str,
        feedback=feedback or "Sin feedback previo.",
    )

    # ── TODO: Invocar Claude Sonnet con el skill prd-template ──────────────
    # from langchain_anthropic import ChatAnthropic
    # llm = ChatAnthropic(model=MODEL_PRD)
    # content = llm.invoke([...])
    # ────────────────────────────────────────────────────────────────────────

    # STUB: contenido simulado
    prd_content = f"""# PRDSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Problema
{state['challenge_description']}

## Criterios de éxito
{chr(10).join(f'- {c}' for c in state['challenge_success_criteria'])}

## User Stories
- US-01: Como cliente, quiero saber en <2s si mi pago fue aprobado
- US-02: Como cliente, quiero ver por qué fue rechazado
- US-03: Como analista, quiero ver el score de riesgo de cada tx

{'(Re-trabajado con feedback: ' + feedback + ')' if feedback else ''}
"""

    # Crear Story en Jira
    story_key = create_story(
        phase="prd",
        summary=f"{state['challenge_name']} — Product Requirements",
        description=prd_content[:2000],  # Jira tiene límite de caracteres
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ PRDSPECS.md generado ({len(prd_content)} chars)")
    print(f"   🎫 Jira Story: {story_key or 'N/A'}")

    return {
        "prd_content":    prd_content,
        "jira_story_keys": [story_key] if story_key else [],
    }