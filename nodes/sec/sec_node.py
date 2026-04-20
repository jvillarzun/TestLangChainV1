"""
nodes/agent_nodes.py
─────────────────────
Nodos placeholder para los 7 agentes especializados.

En esta primera versión (Paso 1 del ADLC) estos nodos son stubs
que simulan el trabajo del agente. En las siguientes iteraciones
cada nodo invocará al LLM correspondiente con las skills inyectadas.

Cada nodo:
  1. Lee el contexto necesario del estado (outputs de fases previas)
  2. Obtiene el feedback del último HITL si la fase fue rechazada
  3. Invoca al agente (stub por ahora)
  4. Guarda el resultado en el estado
  5. Crea el ticket en Jira
"""

from state.cycle_state import CycleState
from tools.jira_tools import create_task
from nodes.helper import _get_last_feedback, load_prompt

def run_security_node(state: CycleState) -> dict:
    """Nodo SEC — audita código y arquitectura."""
    print("\n🔐 SECURITY-AGENT: Auditando...")

    feedback = _get_last_feedback(state, "security")
    system_prompt = load_prompt(
        "sec",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        arch_content=state.get("arch_content") or "",
        dev_content=state.get("dev_content") or "",
        feedback=feedback or "Sin feedback previo.",
    )

    security_content = f"""# DEVSECOPS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Threat Model
Flujo de scoring como attack surface principal

## Findings
HIGH:   0
MEDIUM: 1 — Rate limiting no configurado en API GW (mitigado)
LOW:    2 — Headers de seguridad opcionales

## Controles implementados
- Rate limiting: 1000 req/min por card_id
- Input validation: Zod schema en handler
- Audit log: todas las decisiones de fraude logeadas
- Encriptación en tránsito: TLS 1.3
"""
    task_key = create_task(
        phase="security",
        summary=f"{state['challenge_name']} — Security Audit",
        description=security_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ Auditoría completada — 0 HIGH findings")
    return {
        "security_content": security_content,
        "jira_story_keys":  [task_key] if task_key else [],
    }