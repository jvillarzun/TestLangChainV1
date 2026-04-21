"""
nodes/orchestrator_node.py
───────────────────────────
El nodo orquestador es el cerebro del ciclo ADLC.

Responsabilidades en este nodo:
  1. Al inicio: leer el challenge, generar el plan de fases con Claude Opus
  2. Por fase:  delegar al agente correcto y monitorear el resultado
  3. Siempre:   sincronizar con Jira y Slack

Este nodo se ejecuta:
  - Una vez al inicio (fase "init") → genera el plan y crea el Epic en Jira
  - Después de cada aprobación HITL → lee la decisión y decide el siguiente paso

IMPORTANTE: Este nodo NO ejecuta los agentes directamente.
Retorna datos que el StateGraph usa para decidir qué nodo ejecutar a continuación.
La ejecución de cada agente ocurre en agent_nodes.py.
"""

from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from state.cycle_state import CycleState
from tools.slack_tools import notify_team
from tools.jira_tools import create_epic, close_epic
from config.settings import MODEL_ORCHESTRATOR


# ── Prompt del orquestador ────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM_PROMPT = """Eres el MACH-ORCHESTRATOR, el agente orquestador del ciclo ADLC de MACHBank.

Tu rol es analizar el challenge recibido y generar un plan de ejecución estructurado
para el ciclo de desarrollo agéntico. Debes:

1. Entender el dominio del challenge (fintech, pagos, fraude, etc.)
2. Identificar las fases necesarias y sus dependencias
3. Generar instrucciones específicas para cada agente especializado
4. Priorizar criterios de éxito medibles

Estándares de la Plataforma Tecnológica de MACHBank:
- Stack backend: AWS Lambda, DynamoDB, API Gateway, SQS
- Stack móvil: Android (Kotlin/Compose) o KMM
- Seguridad: OWASP Top 10, encriptación en tránsito y reposo
- SLAs: Latencia p95 < 200ms para APIs críticas
- Cobertura de tests: mínimo 80%

Responde SIEMPRE en JSON válido, sin markdown ni texto adicional.
"""

PLAN_PROMPT_TEMPLATE = """Analiza el siguiente challenge y genera el plan de ejecución del ciclo ADLC.

CHALLENGE:
Nombre: {name}
Tipo: {type}
Descripción: {description}
Criterios de éxito:
{criteria}

Genera un JSON con esta estructura EXACTA:
{{
  "analysis": {{
    "domain": "string — dominio principal (fraude, pagos, onboarding, etc.)",
    "complexity": "high|medium|low",
    "key_risks": ["riesgo 1", "riesgo 2"],
    "tech_stack": ["tecnología 1", "tecnología 2"]
  }},
  "phases": [
    {{
      "phase": "prd",
      "agent": "prd-agent",
      "model": "claude-sonnet-4-5-20251101",
      "depends_on": [],
      "instructions": "Instrucciones específicas para este agente en el contexto de ESTE challenge",
      "key_outputs": ["output 1", "output 2"]
    }}
  ],
  "success_metrics": {{
    "prd": "Criterio de aprobación del PRD",
    "ux_arch": "Criterio de aprobación de UX + ARQ",
    "dev": "Criterio de aprobación del código",
    "qa": "Criterio de aprobación de QA",
    "infra_sec": "Criterio de aprobación de INFRA + SEC"
  }},
  "estimated_cycle_minutes": 90
}}

Las fases deben ser EXACTAMENTE: prd, ux, arch, dev, qa, infra, security
(en ese orden, con ux y arch en paralelo, e infra y security en paralelo al final).
"""


# ── Nodo principal ────────────────────────────────────────────────────────────

def orchestrator_init_node(state: CycleState) -> dict:
    """
    Nodo de inicialización — se ejecuta UNA VEZ al arrancar el ciclo.

    Acciones:
    1. Llama a Claude Opus para analizar el challenge y generar el plan
    2. Crea el Epic en Jira
    3. Notifica al canal de Slack que el ciclo arrancó
    4. Actualiza el estado con el plan y metadata de inicio
    """
    print(f"\n{'='*60}")
    print(f"🎯 MACH-ORCHESTRATOR: Inicializando ciclo")
    print(f"   Challenge: {state['challenge_name']}")
    print(f"   Thread ID: {state['thread_id']}")
    print(f"{'='*60}\n")

    # ── 1. Generar plan con Claude Opus ───────────────────────────────────────
    # llm = ChatAnthropic(model=MODEL_ORCHESTRATOR, max_tokens=2000)
    # llm = ChatGoogleGenerativeAI(model=MODEL_ORCHESTRATOR, max_tokens=2000)

    # criteria_text = "\n".join(f"- {c}" for c in state["challenge_success_criteria"])

    # prompt = PLAN_PROMPT_TEMPLATE.format(
    #     name=state["challenge_name"],
    #     type=state["challenge_type"],
    #     description=state["challenge_description"],
    #     criteria=criteria_text,
    # )

    # print("🧠 Generando plan con Claude Opus...")
    # response = llm.invoke([
    #     SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
    #     HumanMessage(content=prompt),
    # ])

    # import json
    # plan_data = json.loads(response.content)

    # ── STUB — plan hardcodeado para probar Jira/Slack sin LLM ───────────────
    print("🧠 [STUB] Usando plan hardcodeado — LLM desactivado")
    plan_data = {
        "analysis": {
            "domain": "test",
            "complexity": "low",
            "key_risks": [],
            "tech_stack": [],
        },
        "phases": [
            {"phase": "prd",      "agent": "prd-agent",       "model": "stub", "depends_on": [],              "instructions": "stub", "key_outputs": []},
            {"phase": "ux",       "agent": "ux-agent",        "model": "stub", "depends_on": ["prd"],         "instructions": "stub", "key_outputs": []},
            {"phase": "arch",     "agent": "architect-agent", "model": "stub", "depends_on": ["prd"],         "instructions": "stub", "key_outputs": []},
            {"phase": "dev",      "agent": "dev-agent",       "model": "stub", "depends_on": ["prd", "arch"], "instructions": "stub", "key_outputs": []},
            {"phase": "qa",       "agent": "qa-agent",        "model": "stub", "depends_on": ["dev"],         "instructions": "stub", "key_outputs": []},
            {"phase": "infra",    "agent": "infra-agent",     "model": "stub", "depends_on": ["qa"],          "instructions": "stub", "key_outputs": []},
            {"phase": "security", "agent": "security-agent",  "model": "stub", "depends_on": ["qa"],          "instructions": "stub", "key_outputs": []},
        ],
        "success_metrics": {
            "prd":      "stub",
            "ux_arch":  "stub",
            "dev":      "stub",
            "qa":       "stub",
            "infra_sec":"stub",
        },
        "estimated_cycle_minutes": 1,
    }
    phases = plan_data["phases"]

    print(f"✅ Plan generado: {len(phases)} fases")
    for phase in phases:
        deps = phase.get("depends_on", [])
        dep_str = f" (depende de: {', '.join(deps)})" if deps else " (primera fase)"
        print(f"   → {phase['phase']}: {phase['agent']}{dep_str}")

    # ── 2. Crear Epic en Jira ─────────────────────────────────────────────────
    print("\n🎫 Creando Epic en Jira...")
    epic_key = create_epic(
        challenge_name=state["challenge_name"],
        challenge_description=state["challenge_description"],
        thread_id=state["thread_id"],
    )
    if epic_key:
        print(f"✅ Epic creado: {epic_key}")
    else:
        print("⚠️  Epic no creado (Jira no disponible) — el ciclo continúa")

    # ── 3. Notificar a Slack ──────────────────────────────────────────────────
    notify_team(
        message=(
            f"🚀 *Ciclo ADLC iniciado* — `{state['challenge_name']}`\n"
            f"Tipo: {state['challenge_type'].upper()} · "
            f"Complejidad: {plan_data['analysis']['complexity'].upper()}\n"
            f"Dominio: {plan_data['analysis']['domain']}\n"
            f"Fases: {len(phases)} · Estimado: ~{plan_data['estimated_cycle_minutes']} min\n"
            f"Jira: {epic_key or 'N/A'}"
        ),
        thread_id=state["thread_id"],
    )

    # ── 4. Retornar actualizaciones al estado ─────────────────────────────────
    return {
        "plan_phases":       phases,
        "current_phase":     "prd",  # La primera fase siempre es PRD
        "jira_epic_key":     epic_key,
        "cycle_start_time":  datetime.now().isoformat(),
    }


def orchestrator_route_node(state: CycleState) -> dict:
    """
    Nodo de routing — decide qué hacer después de cada aprobación HITL.

    Se ejecuta después de cada checkpoint HITL para:
    1. Registrar la decisión del revisor
    2. Si fue rechazo: preparar el re-trabajo del agente
    3. Si fue aprobación: avanzar a la siguiente fase
    4. Si es la última fase: cerrar el ciclo

    Este nodo retorna un dict vacío porque el routing real
    se hace mediante las edges condicionales del StateGraph (ver mach_graph.py).
    """
    last_decision = state["hitl_decisions"][-1] if state["hitl_decisions"] else None
    current = state["current_phase"]

    if last_decision and last_decision["decision"] == "reject":
        print(f"\n❌ Fase '{current}' rechazada. Feedback: {last_decision.get('feedback', 'Sin feedback')}")
        # Reiniciar retry_count para la re-ejecución
        return {"retry_count": state["retry_count"] + 1}

    print(f"\n✅ Fase '{current}' aprobada. Avanzando al siguiente paso.")
    return {"retry_count": 0}


def orchestrator_finalize_node(state: CycleState) -> dict:
    """
    Nodo final — se ejecuta cuando todas las fases están aprobadas.

    Acciones:
    1. Genera REPORT.md consolidado con todos los entregables
    2. Cierra el Epic en Jira
    3. Notifica al equipo con link al reporte
    """
    print(f"\n{'='*60}")
    print(f"🏁 CICLO COMPLETO — {state['challenge_name']}")
    print(f"{'='*60}\n")

    decisions = state["hitl_decisions"]
    approvals  = sum(1 for d in decisions if d["decision"] == "approve")
    rejections = sum(1 for d in decisions if d["decision"] == "reject")

    start    = state.get("cycle_start_time")
    end_time = datetime.now()
    duration_str = ""
    if start:
        elapsed      = end_time - datetime.fromisoformat(start)
        minutes      = int(elapsed.total_seconds() / 60)
        duration_str = f"{minutes} min"

    report_content = _build_report(state, approvals, rejections, duration_str)

    from nodes.helper import save_output
    report_path = save_output("REPORT.md", report_content)
    print(f"📄 Reporte consolidado guardado en {report_path}")

    summary = (
        f"✅ 7/7 entregables completados · "
        f"{duration_str or 'N/A'} · "
        f"{approvals} aprobados / {rejections} rechazados\n"
        f"Epic Jira: {state.get('jira_epic_key', 'N/A')}"
    )

    if state.get("jira_epic_key"):
        close_epic(state["jira_epic_key"], summary)
        print(f"✅ Epic {state['jira_epic_key']} cerrado en Jira")

    from config.settings import WEBHOOK_BASE_URL
    report_url = f"{WEBHOOK_BASE_URL}/view/REPORT.md"
    notify_team(
        message=(
            f"🏁 *Ciclo ADLC completado* — `{state['challenge_name']}`\n\n"
            f"{summary}\n\n"
            f"📋 <{report_url}|Ver reporte consolidado>"
        ),
        thread_id=state["thread_id"],
    )

    return {
        "current_phase":  "done",
        "cycle_end_time": end_time.isoformat(),
    }


def _build_report(state: CycleState, approvals: int, rejections: int, duration: str) -> str:
    """Genera el contenido de REPORT.md consolidando todos los entregables."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    deliverables = [
        ("PRD",   "PRDSPECS.md",   state.get("prd_content")),
        ("UX",    "UXSPECS.md",    state.get("ux_content")),
        ("ARQ",   "ARQSPECS.md",   state.get("arch_content")),
        ("DEV",   "DEVSPECS.md",   state.get("dev_content")),
        ("QA",    "QASCPECS.md",   state.get("qa_content")),
        ("INFRA", "INFESPEOS.md",  state.get("infra_content")),
        ("SEC",   "DEVSECOPS.md",  state.get("security_content")),
    ]

    completed = sum(1 for _, _, c in deliverables if c)

    lines: list[str] = []

    # ── Encabezado ──────────────────────────────────────────────────────────────
    lines += [
        f"# Reporte Consolidado ADLC — {state['challenge_name']}",
        "",
        f"> Generado: {now}  ",
        f"> Tipo: {state['challenge_type'].upper()}  ",
        f"> Thread ID: `{state['thread_id']}`",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Entregables completados | {completed}/7 |",
        f"| Duración total | {duration or 'N/A'} |",
        f"| Checkpoints HITL aprobados | {approvals} |",
        f"| Rechazos/retrabajos | {rejections} |",
        f"| QA pasó | {'✅ Sí' if state.get('qa_passed') else '❌ No'} |",
        f"| Epic Jira | {state.get('jira_epic_key') or 'N/A'} |",
        f"| PR GitHub | {state.get('dev_pr_url') or 'N/A'} |",
        "",
        "### Descripción del challenge",
        "",
        state.get("challenge_description", ""),
        "",
    ]

    if state.get("challenge_success_criteria"):
        lines += ["### Criterios de éxito", ""]
        for c in state["challenge_success_criteria"]:
            lines.append(f"- {c}")
        lines.append("")

    # ── Tabla de entregables ─────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Entregables",
        "",
        "| Fase | Archivo | Estado |",
        "|------|---------|--------|",
    ]
    for label, filename, content in deliverables:
        status = "✅ Completado" if content else "⏳ Pendiente"
        lines.append(f"| {label} | `{filename}` | {status} |")
    lines.append("")

    # ── Contenido por fase ───────────────────────────────────────────────────
    lines += ["---", ""]
    for label, filename, content in deliverables:
        lines += [f"## {label} — {filename}", ""]
        if content:
            lines.append(content)
        else:
            lines.append("_Entregable no generado._")
        lines += ["", "---", ""]

    # ── Historial HITL ───────────────────────────────────────────────────────
    lines += ["## Historial de decisiones HITL", ""]
    decisions = state.get("hitl_decisions", [])
    if decisions:
        lines += [
            "| # | Fase | Decisión | Reviewer | Feedback | Timestamp |",
            "|---|------|----------|----------|----------|-----------|",
        ]
        for i, d in enumerate(decisions, 1):
            icon     = {"approve": "✅", "reject": "🔄", "backtrack": "⏪"}.get(d.get("decision", ""), "?")
            feedback = (d.get("feedback") or "—").replace("|", "∣")[:60]
            ts       = (d.get("timestamp") or "")[:16]
            lines.append(
                f"| {i} | {d.get('phase','?')} | {icon} {d.get('decision','?')} "
                f"| {d.get('reviewer','?')} | {feedback} | {ts} |"
            )
        lines.append("")
    else:
        lines += ["_Sin decisiones registradas._", ""]

    lines += ["---", "", "_Reporte generado automáticamente por MACH-ORCHESTRATOR._"]

    return "\n".join(lines)
