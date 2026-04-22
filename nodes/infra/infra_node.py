from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from config.settings import MODEL_INFRA


def run_infra_node(state: CycleState) -> dict:
    """Nodo INFRA — Gemini genera INFESPEOS.md con CDK stack y pipeline CI/CD."""
    print("\n⚙️  INFRA-AGENT: Generando INFESPEOS.md...")

    feedback = _get_last_feedback(state, "infra")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "infra",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        arch_content=state.get("arch_content") or "",
        qa_content=state.get("qa_content") or "",
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "infra") or "Sin instrucciones adicionales.",
    )

    try:
        infra_content, _usage = llm_invoke(
            model=MODEL_INFRA,
            system_prompt=system_prompt,
            user_message="Genera el INFESPEOS.md completo según las instrucciones.",
            stub_content="# INFESPEOS.md stub — TEST_MODE activo",
        )
        _usage["agent"] = "infra"
    except Exception as e:
        print(f"[INFRA-AGENT] Error: {e}")
        notify_team(f"❌ INFRA-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "infra", "error_message": str(e), "infra_content": None, "token_usage": []}

    output_path = save_output("INFESPEOS.md", infra_content)
    print(f"   💾 Guardado en {output_path}")

    task_key = create_task(
        phase="infra",
        summary=f"{state['challenge_name']} — Infrastructure",
        description=infra_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ INFESPEOS.md generado ({len(infra_content)} chars) | tokens: {_usage['total_tokens']} | ${_usage['cost_usd']:.4f}")

    return {
        "infra_content":   infra_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
        "token_usage":     [_usage],
    }
