from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_story
from tools.confluence_tools import create_prd_rationale
from tools.slack_tools import notify_team
from tools.github_tools import get_repo_context
from config.settings import MODEL_PRD, REPO_FE_NAME


def run_prd_node(state: CycleState) -> dict:
    """Nodo PRD — genera PRDSPECS.md desde el challenge."""
    print("\n📋 PRD-AGENT: Generando PRDSPECS.md...")

    feedback = _get_last_feedback(state, "prd")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    print(f"   🗂️  [PRD] Leyendo contexto del repositorio {REPO_FE_NAME}...")
    _repo_ctx = get_repo_context(REPO_FE_NAME)
    _repo_tree = "\n".join(_repo_ctx.get("tree", [])) or "Repositorio vacío o no accesible."
    print(f"   🗂️  [PRD] Árbol: {len(_repo_ctx.get('tree', []))} archivos")

    criteria_str = "\n".join(f"  - {c}" for c in state["challenge_success_criteria"])
    system_prompt = load_prompt(
        "prd",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        challenge_success_criteria=criteria_str,
        repo_fe_name=REPO_FE_NAME,
        repo_tree=_repo_tree,
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "prd") or "Sin instrucciones adicionales.",
    )

    try:
        prd_content, _usage = llm_invoke(
            model=MODEL_PRD,
            system_prompt=system_prompt,
            user_message="Genera el PRDSPECS.md completo según las instrucciones.",
            stub_content="# PRDSPECS.md stub — TEST_MODE activo",
        )
        _usage["agent"] = "prd"
    except Exception as e:
        print(f"[PRD-AGENT] Error: {e}")
        notify_team(f"❌ PRD-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "prd", "error_message": str(e), "prd_content": None, "token_usage": []}

    output_path = save_output("PRDSPECS.md", prd_content)
    print(f"   💾 Guardado en {output_path}")

    story_key = create_story(
        phase="prd",
        summary=f"{state['challenge_name']} — Product Requirements",
        description=prd_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )

    confluence_url = create_prd_rationale(
        challenge_name=state["challenge_name"],
        challenge_description=state["challenge_description"],
        prd_content=prd_content,
        thread_id=state["thread_id"],
        jira_epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ PRDSPECS.md generado ({len(prd_content)} chars) | tokens: {_usage['total_tokens']} | ${_usage['cost_usd']:.4f}")
    print(f"   🎫 Jira Story: {story_key or 'N/A'}")
    print(f"   📄 Confluence Rationale: {confluence_url or 'N/A'}")

    return {
        "prd_content":       prd_content,
        "error_phase":       None,
        "error_message":     None,
        "jira_story_keys":   [story_key] if story_key else [],
        "confluence_prd_url": confluence_url,
        "token_usage":       [_usage],
    }
