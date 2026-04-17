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
from tools.jira_tools import create_story, create_task


# ── PRD Agent ─────────────────────────────────────────────────────────────────

def run_prd_node(state: CycleState) -> dict:
    """
    Nodo PRD — invoca al prd-agent (Claude Sonnet).
    Lee el challenge y genera PRDSPECS.md.
    """
    print("\n📋 PRD-AGENT: Generando PRDSPECS.md...")

    # Obtener feedback de rechazo previo si existe
    feedback = _get_last_feedback(state, "prd")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    # ── TODO: Invocar Claude Sonnet con el skill prd-template ──────────────
    # from langchain_anthropic import ChatAnthropic
    # llm = ChatAnthropic(model=MODEL_PRD)
    # content = llm.invoke([...])
    # ────────────────────────────────────────────────────────────────────────

    # STUB: contenido simulado
    prd_content = f"""# PRDSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Problema
{state['challenge_description']}

## Criterios de éxito
{chr(10).join(f'- {c}' for c in state['challenge_success_criteria'])}

## User Stories
- US-01: Como cliente, quiero saber en <2s si mi pago fue aprobado
- US-02: Como cliente, quiero ver por qué fue rechazado
- US-03: Como analista, quiero ver el score de riesgo de cada tx

{'(Re-trabajado con feedback: ' + feedback + ')' if feedback else ''}
"""

    # Crear Story en Jira
    story_key = create_story(
        phase="prd",
        summary=f"{state['challenge_name']} — Product Requirements",
        description=prd_content[:2000],  # Jira tiene límite de caracteres
        epic_key=state.get("jira_epic_key"),
    )

    print(f"   ✅ PRDSPECS.md generado ({len(prd_content)} chars)")
    print(f"   🎫 Jira Story: {story_key or 'N/A'}")

    return {
        "prd_content":    prd_content,
        "jira_story_keys": [story_key] if story_key else [],
    }


# ── UX + ARQ Agents (paralelo) ─────────────────────────────────────────────────

def run_ux_node(state: CycleState) -> dict:
    """Nodo UX — invoca al ux-agent (Gemini Pro). Genera UXSPECS.md."""
    print("\n🎨 UX-AGENT: Generando UXSPECS.md...")

    # STUB
    ux_content = f"""# UXSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Flujos principales
1. Flujo de pago → scoring → resultado (aprobado/rechazado)
2. Pantalla de rechazo con explicación en lenguaje natural
3. Dashboard del analista de riesgo

## Wireframes
[Wireframes en ASCII omitidos en este stub]
"""
    story_key = create_story(
        phase="ux",
        summary=f"{state['challenge_name']} — UX Specs",
        description=ux_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ UXSPECS.md generado")
    return {
        "ux_content":      ux_content,
        "jira_story_keys": [story_key] if story_key else [],
    }


def run_arch_node(state: CycleState) -> dict:
    """Nodo ARQ — invoca al architect-agent (Claude Opus). Genera ARQSPECS.md."""
    print("\n🏗️  ARCHITECT-AGENT: Generando ARQSPECS.md...")

    # STUB
    arch_content = f"""# ARQSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Arquitectura C4
Cliente → API Gateway → Lambda ScoreEngine → DynamoDB
                                           → Bedrock ML Scorer

## API Contract
POST /v1/transactions/score
Body: {{ amount, merchant_id, card_id, location, device_fp }}
Response: {{ decision, score, reason_codes[], explanation }}

## ADR-001: Lambda vs ECS
Decisión: Lambda. Justificación: cold start <50ms, costo por invocación.
"""
    story_key = create_story(
        phase="arch",
        summary=f"{state['challenge_name']} — Architecture Specs",
        description=arch_content[:2000],
        epic_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ ARQSPECS.md generado")
    return {
        "arch_content":    arch_content,
        "jira_story_keys": [story_key] if story_key else [],
    }


# ── DEV Agent ─────────────────────────────────────────────────────────────────

def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — invoca a Claude Code. Clona repo, implementa, abre PR."""
    print("\n💻 DEV-AGENT: Implementando código...")

    feedback = _get_last_feedback(state, "dev")

    # STUB — en producción Claude Code clona el repo y trabaja sobre él
    dev_content = f"""# DEVSPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Setup
npm install && npm run build

## Estructura
src/score-engine/handler.ts — Lambda principal
src/rules-engine.ts         — Reglas síncronas
src/ml-scorer.ts            — Integración Bedrock

## Tests
npm test → 12/12 PASS, coverage 87%
{'(Re-trabajado con feedback: ' + feedback + ')' if feedback else ''}
"""
    pr_url = f"https://github.com/machbank/fraudshield/pull/42"  # STUB

    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
        parent_key=state.get("jira_epic_key"),
        pr_url=pr_url,
    )
    print(f"   ✅ Código implementado")
    print(f"   🐙 PR abierto: {pr_url}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")
    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_url,
        "jira_story_keys": [task_key] if task_key else [],
    }


# ── QA Agent ──────────────────────────────────────────────────────────────────

def run_qa_node(state: CycleState) -> dict:
    """Nodo QA — gate de calidad. Valida criterios del PRD."""
    print("\n🧪 QA-AGENT: Validando criterios de aceptación...")

    # STUB — en producción lee el PR y ejecuta los tests
    qa_content = f"""# QASCPECS — {state['challenge_name']}
status: READY_FOR_REVIEW

## Resultados
US-01 ✅ Latencia p95: 145ms (req: <200ms) — PASS
US-02 ✅ Explicación presente en rechazos — PASS
US-03 ✅ Dashboard refresh: 2.1s (req: <5s) — PASS

## Sign-off
3/3 criterios críticos PASS
Aprobado para deploy
"""
    task_key = create_task(
        phase="qa",
        summary=f"{state['challenge_name']} — QA Sign-off",
        description=qa_content[:2000],
        parent_key=state.get("jira_epic_key"),
    )
    print(f"   ✅ QA PASS — 3/3 criterios")
    return {
        "qa_content":      qa_content,
        "qa_passed":       True,
        "jira_story_keys": [task_key] if task_key else [],
    }


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


def run_security_node(state: CycleState) -> dict:
    """Nodo SEC — audita código y arquitectura."""
    print("\n🔐 SECURITY-AGENT: Auditando...")

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


def run_infra_sec_parallel_node(state: CycleState) -> dict:
    """Wrapper que ejecuta INFRA y SEC secuencialmente."""
    infra_result = run_infra_node(state)
    # El estado de infra ya incluye infra_content, pasarlo al sec_node
    merged = {**state, **infra_result}
    sec_result = run_security_node(merged)
    return {**infra_result, **sec_result}


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_last_feedback(state: CycleState, phase: str) -> str | None:
    """
    Extrae el feedback del último rechazo HITL para esta fase.
    Permite que el agente incorpore las correcciones solicitadas.
    """
    decisions = state.get("hitl_decisions", [])
    for decision in reversed(decisions):
        if decision.get("phase") == phase and decision.get("decision") == "reject":
            return decision.get("feedback")
    return None
