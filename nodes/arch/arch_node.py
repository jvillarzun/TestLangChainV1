import json
import re

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_ARCHITECT, LLM_PROVIDER_ARCH, LLM_MODEL_ARCH, REPO_BE_NAME, REPO_FE_NAME
from tools.github_tools import get_repo_context

def _format_context(ctx: dict) -> str:
    """Serializa el contexto de repo a texto para el prompt."""
    lines = ["=== Árbol de archivos ==="]
    for path in ctx.get("tree", []):
        lines.append("  " + path)
    lines.append("\n=== Archivos clave (CONTENIDO COMPLETO PARA LLD) ===")
    
    files_dict = ctx.get("files", {})
    if not files_dict:
        lines.append("\n⚠️ ADVERTENCIA: No se pudo obtener el contenido de los archivos.")
        
    for path, content in files_dict.items():
        lines.append(f"\n--- {path} ---")
        # Subimos el límite a 12000 para asegurar que vea el final de los componentes React
        # Los modelos modernos aguantan este contexto sin problema.
        lines.append(content[:12000]) 
        
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
    
    # Mostrar configuración de LLM
    print("\n" + "="*80)
    print(f"🤖 CONFIGURACIÓN LLM ARCHITECT")
    print(f"   Proveedor: {LLM_PROVIDER_ARCH}")
    print(f"   Modelo: {LLM_MODEL_ARCH}")
    print("="*80 + "\n")

    feedback = _get_last_feedback(state, "arch")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    # ── Obtener contexto de repos (FRONTEND-ONLY) ────────────────────────────
    print("   🔍 Obteniendo contexto del repositorio Frontend...")
    fe_ctx = get_repo_context(REPO_FE_NAME)
    fe_context = _format_context(fe_ctx)
    print(f"   ✔ FE: {len(fe_ctx['tree'])} archivos (Frontend-Only Architecture)")

    system_prompt = load_prompt(
        "arch",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
        fe_context=fe_context,
        repo_fe_name=REPO_FE_NAME,
    )

    try:
        # Usar proveedor configurado o fallback a Gemini con MODEL_ARCHITECT
        provider = LLM_PROVIDER_ARCH
        model = LLM_MODEL_ARCH if LLM_PROVIDER_ARCH in ["gemini", "openai"] else MODEL_ARCHITECT
        print(f"   🤖 LLM: {provider} | Modelo: {model}")
        
        arch_content = llm_invoke(
            model=model,
            system_prompt=system_prompt,
            user_message="Genera el ARQSPECS.md completo según las instrucciones.",
            stub_content="# ARQSPECS.md stub — TEST_MODE activo",
            provider=provider,
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