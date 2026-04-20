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
from tools.jira_tools import create_story, create_task
from nodes.helper import _get_last_feedback, load_prompt


def run_arch_node(state: CycleState) -> dict:
    """Nodo ARQ — invoca al architect-agent (Claude Opus). Genera ARQSPECS.md."""
    print("\n🏗️  ARCHITECT-AGENT: Generando ARQSPECS.md...")

    feedback = _get_last_feedback(state, "arch")
    system_prompt = load_prompt(
        "arch",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    # STUB
    arch_content = f"""# ARQSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Arquitectura C4
Cliente → API Gateway → Lambda ScoreEngine → DynamoDB
                                           → Bedrock ML Scorer

## API Contract
POST /v1/transactions/score
Body: {{ amount, merchant_id, card_id, location, device_fp }}
Response: {{ decision, score, reason_codes[], explanation }}

## ADR-001: Lambda vs ECS
Decisión: Lambda. Justificación: cold start <50ms, costo por invocación.
"""
    story_key = create_story(
        phase="arch",
        summary=f"{state['challenge_name']} — Architecture Specs",
        description=arch_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ ARQSPECS.md generado")
    return {
        "arch_content":    arch_content,
        "jira_story_keys": [story_key] if story_key else [],
    }


# ── DEV Agent ─────────────────────────────────────────────────────────────────

def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — invoca a Claude Code. Clona repo, implementa, abre PR."""
    print("\n💻 DEV-AGENT: Implementando código...")

    feedback = _get_last_feedback(state, "dev")

    # STUB — en producción Claude Code clona el repo y trabaja sobre él
    dev_content = f"""# DEVSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Setup
npm install && npm run build

## Estructura
src/score-engine/handler.ts — Lambda principal
src/rules-engine.ts         — Reglas síncronas
src/ml-scorer.ts            — Integración Bedrock

## Tests
npm test → 12/12 PASS, coverage 87%
{'(Re-trabajado con feedback: ' + feedback + ')' if feedback else ''}
"""
    pr_url = f"https://github.com/machbank/fraudshield/pull/42"  # STUB

    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
        parent_key=state.get("jira_epic_key"),
        pr_url=pr_url,
    )
    print(f"   ✅ Código implementado")
    print(f"   🐙 PR abierto: {pr_url}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")
    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_url,
        "jira_story_keys": [task_key] if task_key else [],
    }