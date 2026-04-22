from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from config.settings import MODEL_QA


def run_qa_node(state: CycleState) -> dict:
    """Nodo QA — Gemini evalúa criterios, genera QASCPECS.md y setea qa_passed."""
    print("\n🧪 QA-AGENT: Validando criterios de aceptación...")

    feedback = _get_last_feedback(state, "qa")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "qa",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        prd_content=state.get("prd_content") or "",
        dev_content=state.get("dev_content") or "",
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "qa") or "Sin instrucciones adicionales.",
    )

    try:
        qa_content = llm_invoke(
            model=MODEL_QA,
            system_prompt=system_prompt,
            user_message="Genera el QASCPECS.md completo. Termina con 'qa_passed: true' o 'qa_passed: false'.",
            stub_content="# QASCPECS.md stub\nqa_passed: true",
        )
    except Exception as e:
        print(f"[QA-AGENT] Error: {e}")
        notify_team(f"❌ QA-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "qa", "error_message": str(e), "qa_content": None, "qa_passed": None}

    output_path = save_output("QASCPECS.md", qa_content)
    print(f"   💾 Guardado en {output_path}")

    content_lower = qa_content.lower()
    qa_passed = "qa_passed: true" in content_lower or "qa_approved" in content_lower

    task_key = create_task(
        phase="qa",
        summary=f"{state['challenge_name']} — QA Sign-off",
        description=qa_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )

    result_icon = "✅" if qa_passed else "❌"
    print(f"   {result_icon} QA {'PASS' if qa_passed else 'FAIL'}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")

    return {
        "qa_content":      qa_content,
        "qa_passed":       qa_passed,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
    }
