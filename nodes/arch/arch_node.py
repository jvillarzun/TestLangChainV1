import json
import re

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_ARCHITECT
from tools.github_tools import get_repo_context
from config.settings import MODEL_ARCHITECT, REPO_BE_NAME, REPO_FE_NAME

def _format_context(ctx: dict) -> str:
    """Serializa el contexto de repo a texto para el prompt."""
    lines = ["=== Árbol de archivos ==="]
    for path in ctx.get("tree", []):
        lines.append(f"  {path}")
    lines.append("\n=== Archivos clave ===")
    for path, content in ctx.get("files", {}).items():
        lines.append(f"\n--- {path} ---")
        lines.append(content[:3000])  # cap para no exceder ventana de contexto
    return "\n".join(lines)


def _extract_engineering_plan(content: str) -> str | None:
    """Extrae el bloque JSON ENGINEERING_PLAN del output del LLM."""
    match = re.search(r"```json\s*(\{.*?\"steps\".*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            json.loads(match.group(1))  # validar JSON
            return match.group(1)
        except json.JSONDecodeError:
            pass
    return None

def run_arch_node(state: CycleState) -> dict:
    """Nodo ARQ — genera ARQSPECS.md con contexto real de repos GitHub."""
    print("\n🏗️  ARCHITECT-AGENT: Generando ARQSPECS.md...")

    feedback = _get_last_feedback(state, "arch")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    # ── Obtener contexto de repos ────────────────────────────────────────────
    print("   🔍 Obteniendo contexto de repositorios GitHub...")
    be_ctx = get_repo_context(REPO_BE_NAME)
    fe_ctx = get_repo_context(REPO_FE_NAME)
    be_context = _format_context(be_ctx)
    fe_context = _format_context(fe_ctx)
    print(f"   ✔ BE: {len(be_ctx['tree'])} archivos | FE: {len(fe_ctx['tree'])} archivos")

    try:
        from rag.rag_helper import get_rag_context
        _rag_query = get_phase_instructions(state, "arch") or f"{state['challenge_name']} {state['challenge_description']}"
        _rag = get_rag_context("arch", _rag_query)
    except Exception:
        _rag = None

    system_prompt = load_prompt(
        "arch",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
        be_context=be_context,
        fe_context=fe_context,
        repo_be_name=REPO_BE_NAME,
        repo_fe_name=REPO_FE_NAME,
        orchestrator_instructions=get_phase_instructions(state, "arch") or "Sin instrucciones adicionales.",
    )
    if _rag:
        system_prompt += f"\n\n## Contexto de Knowledge Base (ARCH):\n{_rag}"
        print(f"   📚 RAG: {len(_rag)} chars de contexto inyectados")

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
        return {"error_phase": "arch", "error_message": str(e), "arch_content": None, "github_plan": None}

    output_path = save_output("ARQSPECS.md", arch_content)
    print(f"   💾 Guardado en {output_path}")

    github_plan = _extract_engineering_plan(arch_content)
    if github_plan:
        print(f"   📋 ENGINEERING_PLAN extraído ({len(github_plan)} chars)")
    else:
        print("   ⚠️  ENGINEERING_PLAN no encontrado en el output")

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
        "github_plan":     _extract_engineering_plan(arch_content),
    }
