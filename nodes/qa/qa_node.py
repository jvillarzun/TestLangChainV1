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
from tools.jira_tools import create_task
from nodes.helper import _get_last_feedback, load_prompt

# ── QA Agent ──────────────────────────────────────────────────────────────────

def run_qa_node(state: CycleState) -> dict:
    """Nodo QA — gate de calidad. Valida criterios del PRD."""
    print("\n🧪 QA-AGENT: Validando criterios de aceptación...")

    feedback = _get_last_feedback(state, "qa")
    system_prompt = load_prompt(
        "qa",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        prd_content=state.get("prd_content") or "",
        dev_content=state.get("dev_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    # STUB — en producción lee el PR y ejecuta los tests
    qa_content = f"""# QASCPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Resultados
US-01 ✅ Latencia p95: 145ms (req: <200ms) — PASS
US-02 ✅ Explicación presente en rechazos — PASS
US-03 ✅ Dashboard refresh: 2.1s (req: <5s) — PASS

## Sign-off
3/3 criterios críticos PASS
Aprobado para deploy
"""
    task_key = create_task(
        phase="qa",
        summary=f"{state['challenge_name']} — QA Sign-off",
        description=qa_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ QA PASS — 3/3 criterios")
    return {
        "qa_content":      qa_content,
        "qa_passed":       True,
        "jira_story_keys": [task_key] if task_key else [],
    }