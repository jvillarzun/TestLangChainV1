"""
main.py
────────
Punto de entrada del ciclo ADLC.

Uso:
    # Arrancar el ciclo con el challenge FraudShield
    python main.py

    # Arrancar el servidor de webhooks de Slack (en otra terminal)
    uvicorn api.slack_webhook:app --reload --port 8000

    # En desarrollo, exponer el webhook con ngrok:
    ngrok http 8000
    → Copiar URL en Slack App > Interactivity > Request URL

Flujo:
    1. main.py arranca el ciclo → orquestador genera el plan
    2. El ciclo corre hasta el primer interrupt() (PRD)
    3. Slack envía DM al PO con botones Aprobar/Rechazar
    4. PO hace click → el webhook reanuda el grafo
    5. El ciclo continúa hasta el siguiente interrupt()
    6. ... y así hasta que las 5 fases son aprobadas
    7. El orquestador finaliza, cierra el Epic en Jira y notifica al equipo
"""

import asyncio
import threading
import uuid

import uvicorn

from state.cycle_state import initial_state
from graph.mach_graph import build_graph, get_graph_config


# ── Challenge de ejemplo: FraudShield ─────────────────────────────────────────

EXAMPLE_CHALLENGE = {
    "challenge_name": "PingTest",
    "challenge_type": "greenfield",
    "challenge_description": "Endpoint HTTP que retorna 'pong' con latencia < 10ms.",
    "challenge_success_criteria": [
        "GET /ping retorna 200 con body 'pong'",
    ],
}


def run_cycle(challenge: dict | None = None) -> str:
    """
    Arranca el ciclo ADLC con el challenge dado.

    Retorna el thread_id del ciclo, que el webhook de Slack usa
    para reanudar el grafo cuando lleguen las aprobaciones.
    """
    challenge = challenge or EXAMPLE_CHALLENGE
    thread_id = str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"🚀 Iniciando ciclo ADLC — MACH Race 2026")
    print(f"   Challenge: {challenge['challenge_name']}")
    print(f"   Tipo: {challenge['challenge_type'].upper()}")
    print(f"   Thread ID: {thread_id}")
    print(f"{'='*60}\n")

    # Construir el estado inicial
    state = initial_state(
        thread_id=thread_id,
        **challenge,
    )

    # Construir el grafo
    graph = build_graph()
    config = get_graph_config(thread_id)

    # Arrancar el ciclo
    # El grafo correrá hasta el primer interrupt() (PRD)
    # y retornará con {"__interrupt__": [...]}
    print("⚡ Arrancando grafo LangGraph...\n")
    result = graph.invoke(state, config=config)

    # Verificar si quedó en un interrupt (HITL checkpoint)
    interrupted = result.get("__interrupt__")
    if interrupted:
        interrupt_info = interrupted[0].value
        print(f"\n⏸️  Ciclo pausado en checkpoint HITL:")
        print(f"   Fase: {interrupt_info.get('phase')}")
        print(f"   Esperando aprobación de: {interrupt_info.get('waiting_for')}")
        print(f"\n💡 El DM de Slack fue enviado al revisor.")
        print(f"   Cuando apruebe, el webhook reanudará el ciclo automáticamente.")
        print(f"\n   Thread ID para referencia: {thread_id}")
    else:
        # El ciclo completó sin HITL (poco probable en prod, útil en tests)
        print(f"\n✅ Ciclo completado en fase: {result.get('current_phase')}")

    return thread_id


def run_webhook_server():
    """
    Corre el servidor FastAPI del webhook de Slack en un thread separado.
    Solo necesario en desarrollo — en producción corre como servicio independiente.
    """
    from config.settings import WEBHOOK_PORT
    uvicorn.run(
        "api.slack_webhook:app",
        host="0.0.0.0",
        port=WEBHOOK_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "cycle"

    if mode == "webhook":
        # Solo el servidor de webhooks
        print(f"🌐 Iniciando webhook server en puerto 8000...")
        print(f"   Exponer con: ngrok http 8000")
        run_webhook_server()

    elif mode == "both":
        # Webhook en background + ciclo en foreground
        webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
        webhook_thread.start()
        print("🌐 Webhook server corriendo en background\n")
        run_cycle()

    else:
        # Solo el ciclo (default) — el webhook debe estar corriendo por separado
        run_cycle()
