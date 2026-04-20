from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_ARCHITECT


def run_arch_node(state: CycleState) -> dict:
    """Nodo ARQ — Gemini genera ARQSPECS.md desde PRD aprobado."""
    print("\n🏗️  ARCHITECT-AGENT: Generando ARQSPECS.md...")

    feedback = _get_last_feedback(state, "arch")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "arch",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    try:
        arch_content = llm_invoke(
            model=MODEL_ARCHITECT,
            system_prompt=system_prompt,
            user_message="Genera el ARQSPECS.md completo según las instrucciones.",
            stub_content="# ARQSPECS.md stub — TEST_MODE activo",
        )
    except Exception as e:
        print(f"[ARCH-AGENT] Error: {e}")
        notify_team(f"❌ ARCHITECT-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "ux_arch", "error_message": str(e), "arch_content": None}

    output_path = save_output("ARQSPECS.md", arch_content)
    print(f"   💾 Guardado en {output_path}")

    story_key = create_story(
        phase="arch",
        summary=f"{state['challenge_name']} — Architecture Specs",
        description=arch_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ ARQSPECS.md generado ({len(arch_content)} chars)")

    return {
        "arch_content":    arch_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [story_key] if story_key else [],
    }
