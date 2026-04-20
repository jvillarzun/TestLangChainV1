from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt
from tools.jira_tools import create_task

# ── DEV Agent ─────────────────────────────────────────────────────────────────

def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — invoca a Claude Code. Clona repo, implementa, abre PR."""
    print("\n💻 DEV-AGENT: Implementando código...")

    feedback = _get_last_feedback(state, "dev")
    system_prompt = load_prompt(
        "dev",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        arch_content=state.get("arch_content") or "",
        ux_content=state.get("ux_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

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