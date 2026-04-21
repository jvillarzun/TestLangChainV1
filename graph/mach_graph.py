"""
graph/mach_graph.py
────────────────────
Grafo LangGraph del ciclo ADLC — flujo secuencial completo.

  START
    │
    ▼
  [orchestrator_init]
    │
    ▼
  [run_prd] → [hitl_notify_prd] → [hitl_prd]
    │ approve                      reject → run_prd
    ▼
  [run_ux] → [hitl_notify_ux] → [hitl_ux]
    │ approve                    reject → run_ux
    ▼
  [run_arch] → [hitl_notify_arch] → [hitl_arch]
    │ approve                        reject → run_arch
    ▼
  [run_dev] → [hitl_notify_dev] → [hitl_dev]
    │ approve                      reject → run_dev
    ▼
  [run_qa] → [hitl_notify_qa] → [hitl_qa]
    │ approve                    reject → run_qa
    ▼
  [run_infra] → [hitl_notify_infra] → [hitl_infra]
    │ approve                          reject → run_infra
    ▼
  [run_sec] → [hitl_notify_sec] → [hitl_sec]
    │ approve                      reject → run_sec
    ▼
  [finalize]
    │
    ▼
  END

Routing post-HITL via conditional edges sobre current_phase:
  approve → phase avanzó → conditional edge va al siguiente agente
  reject  → phase se mantuvo → conditional edge vuelve al mismo agente
"""

import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state.cycle_state import CycleState
from nodes.orchestrator_node import orchestrator_init_node, orchestrator_finalize_node
from nodes.hitl_node import make_hitl_node, make_hitl_notify_node
from nodes.prd.prd_node import run_prd_node
from nodes.ux.ux_node import run_ux_node
from nodes.arch.arch_node import run_arch_node
from nodes.dev.dev_node import run_dev_node
from nodes.qa.qa_node import run_qa_node
from nodes.infra.infra_node import run_infra_node
from nodes.sec.sec_node import run_security_node
from config.settings import CHECKPOINTER, SQLITE_PATH


def _route_hitl(state) -> str:
    """Lee current_phase para rutear post-HITL."""
    return state.get("current_phase", "prd")


def build_graph(checkpointer=None):
    """
    Construye y compila el StateGraph del ciclo ADLC secuencial.

    Args:
        checkpointer: Si None, usa el configurado en settings.py.
                      Puedes pasar InMemorySaver() para tests.
    Returns:
        Compiled LangGraph graph listo para invocar.
    """
    builder = StateGraph(CycleState)

    # ── Nodos ─────────────────────────────────────────────────────────────────
    builder.add_node("orchestrator_init", orchestrator_init_node)
    builder.add_node("finalize",          orchestrator_finalize_node)

    builder.add_node("run_prd",   run_prd_node)
    builder.add_node("run_ux",    run_ux_node)
    builder.add_node("run_arch",  run_arch_node)
    builder.add_node("run_dev",   run_dev_node)
    builder.add_node("run_qa",    run_qa_node)
    builder.add_node("run_infra", run_infra_node)
    builder.add_node("run_sec",   run_security_node)

    # HITL: notify (envía DM, guarda ts+channel) + interrupt (espera decisión)
    # Separados para evitar DMs duplicados en el replay de LangGraph
    for phase in ("prd", "ux", "arch", "dev", "qa", "infra", "sec"):
        builder.add_node(f"hitl_notify_{phase}", make_hitl_notify_node(phase))
        builder.add_node(f"hitl_{phase}",        make_hitl_node(phase))

    # ── Edges estáticas ───────────────────────────────────────────────────────
    builder.add_edge(START, "orchestrator_init")
    builder.add_edge("orchestrator_init", "run_prd")
    builder.add_edge("finalize", END)

    # agente → notify → interrupt
    for phase, agent in [
        ("prd",   "run_prd"),
        ("ux",    "run_ux"),
        ("arch",  "run_arch"),
        ("dev",   "run_dev"),
        ("qa",    "run_qa"),
        ("infra", "run_infra"),
        ("sec",   "run_sec"),
    ]:
        builder.add_edge(agent,                  f"hitl_notify_{phase}")
        builder.add_edge(f"hitl_notify_{phase}", f"hitl_{phase}")

    # ── Conditional edges post-HITL ───────────────────────────────────────────
    # current_phase se mantiene en reject → vuelve al mismo agente
    # current_phase avanza en approve   → va al siguiente agente
    builder.add_conditional_edges("hitl_prd",   _route_hitl, {"prd":   "run_prd",   "ux":    "run_ux"})
    builder.add_conditional_edges("hitl_ux",    _route_hitl, {"ux":    "run_ux",    "arch":  "run_arch"})
    builder.add_conditional_edges("hitl_arch",  _route_hitl, {"arch":  "run_arch",  "dev":   "run_dev"})
    builder.add_conditional_edges("hitl_dev",   _route_hitl, {"dev":   "run_dev",   "qa":    "run_qa"})
    builder.add_conditional_edges("hitl_qa",    _route_hitl, {"qa":    "run_qa",    "infra": "run_infra"})
    builder.add_conditional_edges("hitl_infra", _route_hitl, {"infra": "run_infra", "sec":   "run_sec"})
    builder.add_conditional_edges("hitl_sec",   _route_hitl, {"sec":   "run_sec",   "done":  "finalize"})

    # ── Checkpointer ──────────────────────────────────────────────────────────
    if checkpointer is None:
        checkpointer = _build_checkpointer()

    return builder.compile(checkpointer=checkpointer)


def _build_checkpointer():
    if CHECKPOINTER == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
            return SqliteSaver(conn)
        except ImportError:
            print("⚠️  langgraph-checkpoint-sqlite no instalado. Usando InMemorySaver.")
    return InMemorySaver()


def get_graph_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}
