from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
from tools.jira_tools import create_story
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

    llm = ChatGoogleGenerativeAI(model=MODEL_ARCHITECT)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Genera el ARQSPECS.md completo según las instrucciones."),
    ])
    arch_content = response.content

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
        "jira_story_keys": [story_key] if story_key else [],
    }
