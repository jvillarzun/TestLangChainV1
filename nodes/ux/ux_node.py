from pathlib import Path
from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_UX, REPO_FE_NAME, MOCK_EARLY_AGENTS
from tools.github_tools import get_repo_context


def _extract_component_list(repo_tree: list[str]) -> str:
    """Extrae paths que parecen ser componentes UI del árbol del repo."""
    component_paths = [
        p for p in repo_tree
        if any(seg in p.lower() for seg in [
            "component", "componente", "widget", "screen", "view",
            "page", "layout", "ui/", "/ui", "atoms", "molecules",
        ])
    ]
    if not component_paths:
        return "No se detectaron componentes en el repositorio."
    return "\n".join(f"  {p}" for p in component_paths[:60])


def run_ux_node(state: CycleState) -> dict:
    """Nodo UX — genera UXSPECS.md desde PRD aprobado."""
    print("\n🎨 UX-AGENT: Generando UXSPECS.md...")

    # ── Mock para pruebas rápidas sin gastar tokens ───────────────────────────
    if MOCK_EARLY_AGENTS:
        print("⚡ [UX] Usando mock estático. Saltando LLM.")
        mock_path = Path(__file__).parent.parent.parent / "mocks" / "mock_uxspecs.md"
        if mock_path.exists():
            ux_content = mock_path.read_text(encoding="utf-8")
            output_path = save_output("UXSPECS.md", ux_content)
            print(f"   💾 Mock guardado en {output_path}")
            print(f"   ✅ UXSPECS.md mock ({len(ux_content)} chars)")
            return {
                "ux_content":      ux_content,
                "error_phase":     None,
                "error_message":   None,
                "jira_story_keys": [],
            }
        else:
            print(f"   ⚠️  Mock no encontrado en {mock_path}. Ejecutando LLM normal.")

    feedback = _get_last_feedback(state, "ux")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    print(f"   🗂️  [UX] Leyendo contexto del repositorio {REPO_FE_NAME}...")
    _repo_ctx = get_repo_context(REPO_FE_NAME)
    _repo_tree_list = _repo_ctx.get("tree", [])
    _repo_tree = "\n".join(_repo_tree_list) or "Repositorio vacío o no accesible."
    _components = _extract_component_list(_repo_tree_list)
    print(f"   🗂️  [UX] Árbol: {len(_repo_tree_list)} archivos")

    system_prompt = load_prompt(
        "ux",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        repo_fe_name=REPO_FE_NAME,
        repo_tree=_repo_tree,
        existing_components=_components,
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "ux") or "Sin instrucciones adicionales.",
    )

    try:
        ux_content, _usage = llm_invoke(
            model=MODEL_UX,
            system_prompt=system_prompt,
            user_message="Genera el UXSPECS.md completo según las instrucciones.",
            stub_content="# UXSPECS.md stub — TEST_MODE activo",
        )
        _usage["agent"] = "ux"
    except Exception as e:
        print(f"[UX-AGENT] Error: {e}")
        notify_team(f"❌ UX-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "ux", "error_message": str(e), "ux_content": None, "token_usage": []}

    output_path = save_output("UXSPECS.md", ux_content)
    print(f"   💾 Guardado en {output_path}")

    story_key = create_story(
        phase="ux",
        summary=f"{state['challenge_name']} — UX Specs",
        description=ux_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ UXSPECS.md generado ({len(ux_content)} chars) | tokens: {_usage['total_tokens']} | ${_usage['cost_usd']:.4f}")

    return {
        "ux_content":      ux_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [story_key] if story_key else [],
        "token_usage":     [_usage],
    }
