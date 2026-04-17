from state.cycle_state import CycleState
from nodes.arch.arch_node import run_arch_node
from nodes.ux.ux_node import run_ux_node

# ── Nodo wrapper para ejecución paralela ──────────────────────────────────────

def run_ux_arch_parallel_node(state: CycleState) -> dict:
    """
    Wrapper que ejecuta UX y ARQ secuencialmente dentro del mismo nodo.
    En producción esto sería un subgrafo paralelo con Send() API de LangGraph.
    Para la hackathon, ejecución secuencial es suficiente.
    """
    ux_result = run_ux_node(state)
    arch_result = run_arch_node(state)
    return {**ux_result, **arch_result}