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

class CycleStart(BaseModel):
    challenge_name: str
    challenge_type: str
    challenge_description: str
    challenge_success_criteria: list[str]
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
