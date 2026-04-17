"""
graph/mach_graph.py
────────────────────
Definición y compilación del grafo LangGraph del ciclo ADLC.

Este módulo define:
  - Los nodos del grafo (orquestador, agentes, HITL)
  - Las edges (fijas y condicionales)
  - La compilación con checkpointer

Estructura del grafo:

  START
    │
    ▼
  [orchestrator_init]          ← Lee challenge, genera plan, crea Epic Jira
    │
    ▼
  [run_prd]                    ← PRD-AGENT (Claude Sonnet)
    │
    ▼
  [hitl_prd]                   ← interrupt() + DM Slack al PO
    │ approve                  reject → vuelve a run_prd
    ▼
  [run_ux_arch_parallel]       ← UX-AGENT (Gemini) + ARCHITECT-AGENT (Opus)
    │
    ▼
  [hitl_ux_arch]               ← interrupt() + DM Slack al Arquitecto
    │ approve                  reject → vuelve a run_ux_arch_parallel
    ▼
  [run_dev]                    ← DEV-AGENT (Claude Code)
    │
    ▼
  [hitl_dev]                   ← interrupt() + DM Slack al Dev Lead
    │ approve                  reject → vuelve a run_dev
    ▼
  [run_qa]                     ← QA-AGENT (Claude Sonnet) — gate
    │
    ▼
  [hitl_qa]                    ← interrupt() + DM Slack al QA Lead
    │ approve                  reject → vuelve a run_qa
    ▼
  [run_infra_sec_parallel]     ← INFRA-AGENT + SECURITY-AGENT
    │
    ▼
  [hitl_infra_sec]             ← interrupt() + DM Slack al DevOps
    │ approve                  reject → vuelve a run_infra_sec_parallel
    ▼
  [finalize]                   ← Cierra Epic Jira, notifica equipo
    │
    ▼
  END

NOTA sobre routing post-HITL:
Los nodos HITL retornan Command(goto=...) con el nodo siguiente.
LangGraph respeta el goto del Command sobre las edges estáticas.
Por eso las edges después de los nodos HITL son al siguiente agente
(el caso "approve") — el "reject" está manejado dentro del nodo HITL.
"""

import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state.cycle_state import CycleState
from nodes.orchestrator_node import (
    orchestrator_init_node,
    orchestrator_finalize_node,
)
from nodes.hitl_node import make_hitl_node
from nodes.agent_nodes import (
    run_prd_node,
    run_ux_arch_parallel_node,
    run_dev_node,
    run_qa_node,
    run_infra_sec_parallel_node,
)
from config.settings import CHECKPOINTER, SQLITE_PATH


def build_graph(checkpointer=None):
    """
    Construye y compila el StateGraph del ciclo ADLC.

    Args:
        checkpointer: Si None, usa el configurado en settings.py.
                      Puedes pasar InMemorySaver() para tests.

    Returns:
        Compiled LangGraph graph listo para invocar.
    """
    builder = StateGraph(CycleState)

    # ── Registrar nodos ───────────────────────────────────────────────────────

    # Orquestador
    builder.add_node("orchestrator_init", orchestrator_init_node)
    builder.add_node("finalize",          orchestrator_finalize_node)

    # Agentes especializados
    builder.add_node("run_prd",                 run_prd_node)
    builder.add_node("run_ux_arch_parallel",    run_ux_arch_parallel_node)
    builder.add_node("run_dev",                 run_dev_node)
    builder.add_node("run_qa",                  run_qa_node)
    builder.add_node("run_infra_sec_parallel",  run_infra_sec_parallel_node)

    # Nodos HITL — uno por checkpoint de aprobación humana
    # make_hitl_node() retorna una función con interrupt() interno
    builder.add_node("hitl_prd",       make_hitl_node("prd"))
    builder.add_node("hitl_ux_arch",   make_hitl_node("ux_arch"))
    builder.add_node("hitl_dev",       make_hitl_node("dev"))
    builder.add_node("hitl_qa",        make_hitl_node("qa"))
    builder.add_node("hitl_infra_sec", make_hitl_node("infra_sec"))

    # ── Definir edges ─────────────────────────────────────────────────────────

    # Inicio del ciclo
    builder.add_edge(START, "orchestrator_init")
    builder.add_edge("orchestrator_init", "run_prd")

    # Flujo principal: agente → HITL → siguiente agente
    # Los nodos HITL usan Command(goto=...) para el routing post-decisión,
    # pero necesitan un edge estático como fallback.
    builder.add_edge("run_prd",                "hitl_prd")
    builder.add_edge("hitl_prd",               "run_ux_arch_parallel")  # caso approve
    builder.add_edge("run_ux_arch_parallel",   "hitl_ux_arch")
    builder.add_edge("hitl_ux_arch",           "run_dev")               # caso approve
    builder.add_edge("run_dev",                "hitl_dev")
    builder.add_edge("hitl_dev",               "run_qa")                # caso approve
    builder.add_edge("run_qa",                 "hitl_qa")
    builder.add_edge("hitl_qa",                "run_infra_sec_parallel") # caso approve
    builder.add_edge("run_infra_sec_parallel", "hitl_infra_sec")
    builder.add_edge("hitl_infra_sec",         "finalize")              # caso approve
    builder.add_edge("finalize",               END)

    # ── Checkpointer ──────────────────────────────────────────────────────────
    if checkpointer is None:
        checkpointer = _build_checkpointer()

    # Compilar el grafo
    # IMPORTANTE: el checkpointer es obligatorio para que interrupt() funcione
    graph = builder.compile(checkpointer=checkpointer)

    return graph


def _build_checkpointer():
    """
    Construye el checkpointer según la configuración.

    Development:  InMemorySaver  — rápido, sin persistencia entre reinicios
    Production:   SqliteSaver    — persiste en disco, sobrevive reinicios
    """
    if CHECKPOINTER == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
            return SqliteSaver(conn)
        except ImportError:
            print("⚠️  langgraph-checkpoint-sqlite no instalado. Usando InMemorySaver.")

    return InMemorySaver()


def get_graph_config(thread_id: str) -> dict:
    """
    Retorna la configuración de ejecución para un thread específico.
    El thread_id identifica de forma única una instancia del ciclo.

    Pasar siempre el mismo thread_id para el mismo ciclo,
    así el checkpointer sabe qué estado restaurar.
    """
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }
