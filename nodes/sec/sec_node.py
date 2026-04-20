from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from config.settings import MODEL_SECURITY


def run_security_node(state: CycleState) -> dict:
    """Nodo SEC — Gemini audita arquitectura e implementación, genera DEVSECOPS.md."""
    print("\n🔐 SECURITY-AGENT: Auditando...")

    feedback = _get_last_feedback(state, "security")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "sec",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        arch_content=state.get("arch_content") or "",
        dev_content=state.get("dev_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    try:
        llm = ChatGoogleGenerativeAI(model=MODEL_SECURITY)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Genera el DEVSECOPS.md completo según las instrucciones."),
        ])
        security_content = response.content
    except Exception as e:
        print(f"[SEC-AGENT] Error: {e}")
        notify_team(f"❌ SECURITY-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "infra_sec", "error_message": str(e), "security_content": None}

    output_path = save_output("DEVSECOPS.md", security_content)
    print(f"   💾 Guardado en {output_path}")

    task_key = create_task(
        phase="security",
        summary=f"{state['challenge_name']} — Security Audit",
        description=security_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ DEVSECOPS.md generado ({len(security_content)} chars)")

    return {
        "security_content": security_content,
        "error_phase":      None,
        "error_message":    None,
        "jira_story_keys":  [task_key] if task_key else [],
    }
