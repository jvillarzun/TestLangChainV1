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

# ── INFRA + SEC Agents (paralelo) ──────────────────────────────────────────────

def run_infra_node(state: CycleState) -> dict:
    """Nodo INFRA — genera CDK stack y pipeline CI/CD."""
    print("\n⚙️  INFRA-AGENT: Generando CDK stack...")

    infra_content = f"""# INFESPEOS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Stack CDK
Lambda score-engine + DynamoDB + API Gateway + SQS

## CI/CD Pipeline
GitHub Actions → Build → Test → Deploy Lambda

## Runbook
cdk deploy --app 'npx ts-node bin/app.ts'
"""
    task_key = create_task(
        phase="infra",
        summary=f"{state['challenge_name']} — Infrastructure",
        description=infra_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ CDK stack generado")
    return {
        "infra_content":   infra_content,
        "jira_story_keys": [task_key] if task_key else [],
    }