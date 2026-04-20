from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output
from tools.jira_tools import create_task
from config.settings import MODEL_QA


def run_qa_node(state: CycleState) -> dict:
    """Nodo QA — Gemini evalúa criterios, genera QASCPECS.md y setea qa_passed."""
    print("\n🧪 QA-AGENT: Validando criterios de aceptación...")

    feedback = _get_last_feedback(state, "qa")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    system_prompt = load_prompt(
        "qa",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        prd_content=state.get("prd_content") or "",
        dev_content=state.get("dev_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    llm = ChatGoogleGenerativeAI(model=MODEL_QA)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Genera el QASCPECS.md completo. Termina con 'qa_passed: true' o 'qa_passed: false'."),
    ])
    qa_content = response.content

    output_path = save_output("QASCPECS.md", qa_content)
    print(f"   💾 Guardado en {output_path}")

    # Determinar resultado leyendo el output del LLM
    content_lower = qa_content.lower()
    qa_passed = (
        "qa_passed: true" in content_lower
        or "qa_approved" in content_lower
    )

    task_key = create_task(
        phase="qa",
        summary=f"{state['challenge_name']} — QA Sign-off",
        description=qa_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )

    result_icon = "✅" if qa_passed else "❌"
    print(f"   {result_icon} QA {'PASS' if qa_passed else 'FAIL'}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")

    return {
        "qa_content":      qa_content,
        "qa_passed":       qa_passed,
        "jira_story_keys": [task_key] if task_key else [],
    }
