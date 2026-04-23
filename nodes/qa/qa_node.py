from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import get_pr_ci_status
from config.settings import MODEL_QA, REPO_FE_NAME


def _get_ci_summary(state: CycleState) -> str:
    """Obtiene el CI status del PR más reciente. No-fatal si falla."""
    pr_urls: list[str] = list(state.get("dev_pr_urls") or [])
    first = state.get("dev_pr_url")
    if first and first not in pr_urls:
        pr_urls.insert(0, first)

    if not pr_urls:
        return "No hay PRs abiertos — CI no verificable."

    try:
        result = get_pr_ci_status(REPO_FE_NAME, pr_urls[0])
        return result["summary"]
    except Exception as e:
        print(f"   ⚠️  [QA] No se pudo obtener CI status: {e}")
        return f"CI status no disponible: {e}"


def run_qa_node(state: CycleState) -> dict:
    """Nodo QA — evalúa criterios, verifica CI real, genera QASPECS.md."""
    print("\n🧪 QA-AGENT: Validando criterios de aceptación...")

    feedback = _get_last_feedback(state, "qa")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    ci_summary = _get_ci_summary(state)
    print(f"   🔬 CI: {ci_summary[:80]}...")

    system_prompt = load_prompt(
        "qa",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        prd_content=state.get("prd_content") or "",
        dev_content=state.get("dev_content") or "",
        ci_status=ci_summary,
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "qa") or "Sin instrucciones adicionales.",
    )

    try:
        qa_content, _usage = llm_invoke(
            model=MODEL_QA,
            system_prompt=system_prompt,
            user_message="Genera el QASCPECS.md completo. Termina con 'qa_passed: true' o 'qa_passed: false'.",
            stub_content="# QASCPECS.md stub\nqa_passed: true",
        )
        _usage["agent"] = "qa"
    except Exception as e:
        print(f"[QA-AGENT] Error: {e}")
        notify_team(f"❌ QA-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "qa", "error_message": str(e), "qa_content": None, "qa_passed": None, "token_usage": []}

    output_path = save_output("QASPECS.md", qa_content)
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
    print(f"   {result_icon} QA {'PASS' if qa_passed else 'FAIL'} | tokens: {_usage['total_tokens']} | ${_usage['cost_usd']:.4f}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")

    return {
        "qa_content":      qa_content,
        "qa_passed":       qa_passed,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
        "token_usage":     [_usage],
    }
