from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
from tools.jira_tools import create_story
from tools.slack_tools import notify_team
from config.settings import MODEL_UX


def run_ux_node(state: CycleState) -> dict:
    """Nodo UX — Gemini genera UXSPECS.md desde PRD aprobado."""
    print("\n🎨 UX-AGENT: Generando UXSPECS.md...")

    feedback = _get_last_feedback(state, "ux")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "ux",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    try:
        llm = ChatGoogleGenerativeAI(model=MODEL_UX)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Genera el UXSPECS.md completo según las instrucciones."),
        ])
        ux_content = response.content
    except Exception as e:
        print(f"[UX-AGENT] Error: {e}")
        notify_team(f"❌ UX-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "ux_arch", "error_message": str(e), "ux_content": None}

    output_path = save_output("UXSPECS.md", ux_content)
    print(f"   💾 Guardado en {output_path}")

    story_key = create_story(
        phase="ux",
        summary=f"{state['challenge_name']} — UX Specs",
        description=ux_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ UXSPECS.md generado ({len(ux_content)} chars)")

    return {
        "ux_content":      ux_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [story_key] if story_key else [],
    }
