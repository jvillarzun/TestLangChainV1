from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from config.settings import MODEL_DEV


def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — Gemini genera DEVSPECS.md desde PRD + ARQ + UX aprobados."""
    print("\n💻 DEV-AGENT: Generando DEVSPECS.md...")

    feedback = _get_last_feedback(state, "dev")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

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

    try:
        dev_content = llm_invoke(
            model=MODEL_DEV,
            system_prompt=system_prompt,
            user_message="Genera el DEVSPECS.md completo según las instrucciones.",
            stub_content="# DEVSPECS.md stub — TEST_MODE activo",
        )
    except Exception as e:
        print(f"[DEV-AGENT] Error: {e}")
        notify_team(f"❌ DEV-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "dev", "error_message": str(e), "dev_content": None}

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

    pr_url = None  # Dev agent real (P3) abrirá PR en GitHub

    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
        parent_key=state.get("jira_epic_key"),
        pr_url=pr_url,
    )

    print(f"   ✅ DEVSPECS.md generado ({len(dev_content)} chars)")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")

    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_url,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
    }
