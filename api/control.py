"""
api/control.py
──────────────
Router FastAPI para operaciones de control del ciclo ADLC.
Expone endpoints para el micro-frontend Vue.
"""
import os
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["control"])

_NODES_DIR = Path(__file__).parent.parent / "nodes"
_AGENTS = ["prd", "ux", "arch", "dev", "qa", "infra", "sec"]

# ── Prompt endpoints ──────────────────────────────────────────────────────────

@router.get("/prompts")
def list_prompts():
    return [
        {"agent": agent, "label": agent.upper()}
        for agent in _AGENTS
        if (_NODES_DIR / agent / f"{agent}_prompt.md").exists()
    ]


@router.get("/prompts/{agent}")
def get_prompt(agent: str):
    if agent not in _AGENTS:
        raise HTTPException(404, "Agent not found")
    path = _NODES_DIR / agent / f"{agent}_prompt.md"
    if not path.exists():
        raise HTTPException(404, "Prompt file not found")
    return {"agent": agent, "content": path.read_text(encoding="utf-8")}


class PromptUpdate(BaseModel):
    content: str


@router.put("/prompts/{agent}")
def update_prompt(agent: str, body: PromptUpdate):
    if agent not in _AGENTS:
        raise HTTPException(404, "Agent not found")
    path = _NODES_DIR / agent / f"{agent}_prompt.md"
    path.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# ── Cycle endpoints ───────────────────────────────────────────────────────────

class PlanGenerate(BaseModel):
    challenge_name: str
    challenge_type: str
    challenge_description: str
    challenge_success_criteria: list[str]


@router.post("/plan/generate")
def generate_plan(body: PlanGenerate):
    """
    Genera el plan speckit sin arrancar el ciclo.
    El frontend muestra el plan para revisión antes de confirmar.
    """
    import json
    from nodes.helper import llm_invoke
    from nodes.orchestrator_node import ORCHESTRATOR_SYSTEM_PROMPT, PLAN_PROMPT_TEMPLATE
    from config.settings import MODEL_SPECKIT

    criteria_text = "\n".join(f"- {c}" for c in body.challenge_success_criteria)
    user_message = PLAN_PROMPT_TEMPLATE.format(
        name=body.challenge_name,
        type=body.challenge_type,
        description=body.challenge_description,
        criteria=criteria_text,
    )

    _stub = {
        "analysis": {"domain": "test", "complexity": "low", "key_risks": [], "tech_stack": []},
        "phases": [
            {"phase": "prd",      "agent": "prd-agent",       "depends_on": [],              "instructions": "Genera el PRD completo para el challenge.", "key_outputs": ["PRDSPECS.md"]},
            {"phase": "ux",       "agent": "ux-agent",        "depends_on": ["prd"],         "instructions": "Diseña la experiencia de usuario basada en el PRD.", "key_outputs": ["UXSPECS.md"]},
            {"phase": "arch",     "agent": "architect-agent", "depends_on": ["prd"],         "instructions": "Define la arquitectura técnica del sistema.", "key_outputs": ["ARQSPECS.md"]},
            {"phase": "dev",      "agent": "dev-agent",       "depends_on": ["prd", "arch"], "instructions": "Implementa el código según PRD y arquitectura.", "key_outputs": ["DEVSPECS.md"]},
            {"phase": "qa",       "agent": "qa-agent",        "depends_on": ["dev"],         "instructions": "Valida la implementación contra criterios del PRD.", "key_outputs": ["QASCPECS.md"]},
            {"phase": "infra",    "agent": "infra-agent",     "depends_on": ["qa"],          "instructions": "Define infraestructura cloud y CI/CD.", "key_outputs": ["INFESPEOS.md"]},
            {"phase": "security", "agent": "security-agent",  "depends_on": ["qa"],          "instructions": "Audita seguridad OWASP Top 10 y DevSecOps.", "key_outputs": ["DEVSECOPS.md"]},
        ],
        "estimated_cycle_minutes": 1,
    }

    try:
        raw = llm_invoke(MODEL_SPECKIT, ORCHESTRATOR_SYSTEM_PROMPT, user_message, json.dumps(_stub))
        plan = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Plan] Error generando plan: {e} — usando stub")
        plan = _stub

    return {
        "plan_phases": plan["phases"],
        "analysis":    plan.get("analysis", {}),
        "estimated_cycle_minutes": plan.get("estimated_cycle_minutes", 90),
    }


class CycleStart(BaseModel):
    challenge_name: str
    challenge_type: str
    challenge_description: str
    challenge_success_criteria: list[str]
    plan_phases: list[dict] = []   # pre-aprobado desde /api/plan/generate
    test_mode: bool = False


@router.post("/cycle/start")
def start_cycle(body: CycleStart):
    if body.test_mode:
        os.environ["TEST_MODE"] = "true"
    else:
        os.environ.pop("TEST_MODE", None)

    thread_id = str(uuid.uuid4())
    challenge = {
        "challenge_name": body.challenge_name,
        "challenge_type": body.challenge_type,
        "challenge_description": body.challenge_description,
        "challenge_success_criteria": body.challenge_success_criteria,
    }

    def _run():
        from state.cycle_state import initial_state
        from graph.singleton import get_graph, get_graph_config
        graph = get_graph()
        state = initial_state(thread_id=thread_id, **challenge)
        if body.plan_phases:
            state["plan_phases"] = body.plan_phases
        config = get_graph_config(thread_id)
        try:
            graph.invoke(state, config=config)
        except Exception as e:
            print(f"[Control] Error en ciclo {thread_id[:8]}: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"thread_id": thread_id, "status": "started", "test_mode": body.test_mode}


@router.get("/cycle/status/{thread_id}")
def get_cycle_status(thread_id: str):
    from graph.singleton import get_graph
    from graph.mach_graph import get_graph_config
    graph = get_graph()
    config = get_graph_config(thread_id)
    try:
        state = graph.get_state(config)
    except Exception as e:
        raise HTTPException(500, str(e))

    if not state or not state.values:
        raise HTTPException(404, "Thread not found")

    vals = state.values
    return {
        "thread_id": thread_id,
        "current_phase": vals.get("current_phase"),
        "challenge_name": vals.get("challenge_name"),
        "challenge_type": vals.get("challenge_type"),
        "hitl_decisions": vals.get("hitl_decisions", []),
        "hitl_pending_phase": vals.get("hitl_pending_phase"),
        "cycle_start_time": vals.get("cycle_start_time"),
        "cycle_end_time": vals.get("cycle_end_time"),
        "jira_epic_key": vals.get("jira_epic_key"),
        "error_phase": vals.get("error_phase"),
        "error_message": vals.get("error_message"),
        "dev_pr_urls": vals.get("dev_pr_urls", []),
        "dev_pr_url": vals.get("dev_pr_url"),
    }


@router.get("/cycle/recent")
def get_recent_cycles():
    """Lista threads activos del checkpointer (solo SQLite)."""
    from graph.singleton import get_graph
    graph = get_graph()
    try:
        checkpointer = graph.checkpointer
        if hasattr(checkpointer, "conn"):
            cursor = checkpointer.conn.execute(
                "SELECT DISTINCT thread_id FROM checkpoints ORDER BY rowid DESC LIMIT 10"
            )
            threads = [row[0] for row in cursor.fetchall()]
            return {"threads": threads}
    except Exception:
        pass
    return {"threads": []}


class CycleResume(BaseModel):
    thread_id: str
    decision: str  # "approve" or "reject"
    feedback: str = ""


@router.post("/cycle/resume")
def resume_cycle(body: CycleResume):
    """
    Reanuda un ciclo pausado en checkpoint HITL.
    
    Usado por el frontend Vue.js para aprobar/rechazar fases sin Slack.
    """
    from datetime import datetime, timezone
    from langgraph.types import Command
    from graph.singleton import get_graph
    from graph.mach_graph import get_graph_config

    thread_id = body.thread_id
    decision = body.decision
    feedback = body.feedback or ""

    if decision not in ["approve", "reject"]:
        raise HTTPException(400, "decision must be 'approve' or 'reject'")

    print(f"\n[Control] Reanudando ciclo {thread_id[:8]}...")
    print(f"  Decisión: {decision}")
    print(f"  Feedback: {feedback or '(ninguno)'}")

    graph = get_graph()
    config = get_graph_config(thread_id)

    resume_payload = {
        "decision": decision,
        "feedback": feedback if decision == "reject" else None,
        "reviewer": "frontend-manual",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Reanudar el grafo con Command(resume=...)
        graph.invoke(
            Command(resume=resume_payload),
            config=config,
        )
        print(f"[Control] Ciclo reanudado exitosamente")
        return {"ok": True, "message": "Ciclo reanudado exitosamente"}
    except Exception as e:
        print(f"[Control] Error al reanudar: {e}")
        raise HTTPException(500, f"Error al reanudar el ciclo: {str(e)}")

