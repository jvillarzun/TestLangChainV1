"""
scripts/test_agent.py
─────────────────────
Prueba un agente en aislamiento — sin grafo, sin Slack, sin Jira.
Útil para validar que Groq responde correctamente con tokens reales.

Uso:
    # Un agente específico (max 400 tokens por respuesta)
    GROQ_MAX_TOKENS=400 python scripts/test_agent.py prd

    # Todos los agentes en secuencia
    GROQ_MAX_TOKENS=400 python scripts/test_agent.py all

    # Con modelo más barato
    GROQ_MAX_TOKENS=300 TEST_MODEL=llama-3.1-8b-instant python scripts/test_agent.py ux

Agentes disponibles: prd, ux, arch, dev, qa, infra, sec
"""

import sys
import os
import time

# Asegura imports desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Modelo override para pruebas (sin tocar settings.py)
_test_model = os.environ.get("TEST_MODEL")
if _test_model:
    os.environ["MODEL_PRD"]       = _test_model
    os.environ["MODEL_UX"]        = _test_model
    os.environ["MODEL_ARCHITECT"] = _test_model
    os.environ["MODEL_DEV"]       = _test_model
    os.environ["MODEL_QA"]        = _test_model
    os.environ["MODEL_INFRA"]     = _test_model
    os.environ["MODEL_SECURITY"]  = _test_model
    os.environ["MODEL_SPECKIT"]   = _test_model

from state.cycle_state import initial_state, CycleState

# ── Estado mínimo de prueba ───────────────────────────────────────────────────

_STUB_PRD     = "# PRD stub\n## Problema\nApp de pagos P2P.\n## Criterios\n- Latencia < 200ms"
_STUB_UX      = "# UX stub\n## Flujo\n1. Login\n2. Transferir\n3. Confirmar"
_STUB_ARCH    = "# ARCH stub\n## Stack\nAWS Lambda + DynamoDB + API Gateway"
_STUB_DEV     = "# DEV stub\n## Implementación\nEndpoints REST básicos"
_STUB_QA      = "# QA stub\nqa_passed: true"

_PLAN_PHASES = [
    {"phase": "prd",      "instructions": "Genera PRD breve para app de pagos P2P."},
    {"phase": "ux",       "instructions": "Diseña flujo UX mínimo para transferencias."},
    {"phase": "arch",     "instructions": "Define arquitectura serverless en AWS."},
    {"phase": "dev",      "instructions": "Implementa endpoints REST básicos."},
    {"phase": "qa",       "instructions": "Valida criterios de latencia y seguridad."},
    {"phase": "infra",    "instructions": "Define CDK stack para Lambda + DynamoDB."},
    {"phase": "security", "instructions": "Audita OWASP Top 10 para la API de pagos."},
]


def _build_state() -> CycleState:
    state = initial_state(
        thread_id="test-001",
        challenge_name="PayTest",
        challenge_type="greenfield",
        challenge_description="App de pagos P2P mínima para prueba de agentes.",
        challenge_success_criteria=["Latencia < 200ms", "Autenticación JWT"],
    )
    state["plan_phases"]   = _PLAN_PHASES
    state["prd_content"]   = _STUB_PRD
    state["ux_content"]    = _STUB_UX
    state["arch_content"]  = _STUB_ARCH
    state["dev_content"]   = _STUB_DEV
    state["qa_content"]    = _STUB_QA
    state["github_plan"]   = '{"steps": []}'
    return state


# ── Mapa de agentes ───────────────────────────────────────────────────────────

def _run_prd(state):
    from nodes.prd.prd_node import run_prd_node
    return run_prd_node(state)

def _run_ux(state):
    from nodes.ux.ux_node import run_ux_node
    return run_ux_node(state)

def _run_arch(state):
    from nodes.arch.arch_node import run_arch_node
    return run_arch_node(state)

def _run_dev(state):
    from nodes.dev.dev_node import run_dev_node
    return run_dev_node(state)

def _run_qa(state):
    from nodes.qa.qa_node import run_qa_node
    return run_qa_node(state)

def _run_infra(state):
    from nodes.infra.infra_node import run_infra_node
    return run_infra_node(state)

def _run_sec(state):
    from nodes.sec.sec_node import run_security_node
    return run_security_node(state)


AGENTS = {
    "prd":   _run_prd,
    "ux":    _run_ux,
    "arch":  _run_arch,
    "dev":   _run_dev,
    "qa":    _run_qa,
    "infra": _run_infra,
    "sec":   _run_sec,
}


# ── Runner ────────────────────────────────────────────────────────────────────

def run_agent(agent_name: str) -> None:
    if agent_name not in AGENTS:
        print(f"Agente desconocido: '{agent_name}'. Opciones: {', '.join(AGENTS)}")
        sys.exit(1)

    max_tokens = os.environ.get("GROQ_MAX_TOKENS", "4096")
    model      = os.environ.get("TEST_MODEL", "llama-3.3-70b-versatile")
    print(f"\n{'='*60}")
    print(f"  Agente : {agent_name.upper()}")
    print(f"  Modelo : {model}")
    print(f"  Max tokens: {max_tokens}")
    print(f"{'='*60}")

    state = _build_state()
    t0 = time.time()

    try:
        result = AGENTS[agent_name](state)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return

    elapsed = round(time.time() - t0, 2)

    # ── Usage ────────────────────────────────────────────────────────────────
    usage_list = result.get("token_usage", [])
    if usage_list:
        u = usage_list[0]
        print(f"\n📊 Token usage:")
        print(f"   Input tokens  : {u.get('input_tokens', 0):,}")
        print(f"   Output tokens : {u.get('output_tokens', 0):,}")
        print(f"   Total tokens  : {u.get('total_tokens', 0):,}")
        print(f"   Costo         : ${u.get('cost_usd', 0):.6f} USD")
        print(f"   Duración      : {u.get('duration_s', elapsed)}s")
    else:
        print(f"\n⚠  Sin datos de usage (TEST_MODE activo o error)")

    # ── Output preview ───────────────────────────────────────────────────────
    content_key = {
        "prd": "prd_content", "ux": "ux_content", "arch": "arch_content",
        "dev": "dev_content", "qa": "qa_content",  "infra": "infra_content",
        "sec": "security_content",
    }.get(agent_name)

    content = result.get(content_key, "") if content_key else ""
    if content:
        preview = content[:500].strip()
        print(f"\n📄 Output (primeros 500 chars):\n{'-'*40}")
        print(preview)
        if len(content) > 500:
            print(f"... [{len(content) - 500} chars más]")
    else:
        print("\n⚠  Sin contenido generado")

    if result.get("error_phase"):
        print(f"\n❌ Error en fase '{result['error_phase']}': {result.get('error_message')}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    target = sys.argv[1].lower()

    if target == "all":
        totals = {"tokens": 0, "cost": 0.0}
        for name in AGENTS:
            run_agent(name)
            print()
        return

    run_agent(target)


if __name__ == "__main__":
    main()
