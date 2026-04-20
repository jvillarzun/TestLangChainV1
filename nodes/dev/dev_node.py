from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
from tools.jira_tools import create_task
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

    llm = ChatGoogleGenerativeAI(model=MODEL_DEV)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Genera el DEVSPECS.md completo según las instrucciones."),
    ])
    dev_content = response.content

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

    # PR URL stub — el dev agent real (P3) lo reemplazará con un PR real
    pr_url = None

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
        "jira_story_keys": [task_key] if task_key else [],
    }
