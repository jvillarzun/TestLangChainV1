from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_PRD


def run_prd_node(state: CycleState) -> dict:
    """Nodo PRD — Gemini genera PRDSPECS.md desde el challenge."""
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

    try:
        prd_content = llm_invoke(
            model=MODEL_PRD,
            system_prompt=system_prompt,
            user_message="Genera el PRDSPECS.md completo según las instrucciones.",
            stub_content="# PRDSPECS.md stub — TEST_MODE activo",
        )
    except Exception as e:
        print(f"[PRD-AGENT] Error: {e}")
        notify_team(f"❌ PRD-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "prd", "error_message": str(e), "prd_content": None}

    output_path = save_output("PRDSPECS.md", prd_content)
    print(f"   💾 Guardado en {output_path}")

    story_key = create_story(
        phase="prd",
        summary=f"{state['challenge_name']} — Product Requirements",
        description=prd_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ PRDSPECS.md generado ({len(prd_content)} chars)")
    print(f"   🎫 Jira Story: {story_key or 'N/A'}")

    return {
        "prd_content":     prd_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [story_key] if story_key else [],
    }
