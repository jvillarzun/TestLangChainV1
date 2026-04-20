from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
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
    )

    try:
        llm = ChatGoogleGenerativeAI(model=MODEL_INFRA)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Genera el INFESPEOS.md completo según las instrucciones."),
        ])
        infra_content = response.content
    except Exception as e:
        print(f"[INFRA-AGENT] Error: {e}")
        notify_team(f"❌ INFRA-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "infra_sec", "error_message": str(e), "infra_content": None}

    output_path = save_output("INFESPEOS.md", infra_content)
    print(f"   💾 Guardado en {output_path}")

    task_key = create_task(
        phase="infra",
        summary=f"{state['challenge_name']} — Infrastructure",
        description=infra_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ INFESPEOS.md generado ({len(infra_content)} chars)")

    return {
        "infra_content":   infra_content,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
    }
