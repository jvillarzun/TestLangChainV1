from state.cycle_state import CycleState
from nodes.infra.infra_node import run_infra_node
from nodes.sec.sec_node import run_security_node

def run_infra_sec_parallel_node(state: CycleState) -> dict:
    """Wrapper que ejecuta INFRA y SEC secuencialmente."""
    infra_result = run_infra_node(state)
    # El estado de infra ya incluye infra_content, pasarlo al sec_node
    merged = {**state, **infra_result}
    sec_result = run_security_node(merged)
    return {**infra_result, **sec_result}