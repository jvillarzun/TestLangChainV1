"""
api/slack_webhook.py
──────────────────────
Servidor FastAPI que recibe los payloads de los botones interactivos de Slack.

Cuando un revisor hace click en "✅ Aprobar" o "❌ Rechazar" en el DM de Slack,
Slack envía un POST a este endpoint con el payload del botón.

Este endpoint:
1. Verifica la firma de Slack (seguridad)
2. Parsea el payload para extraer thread_id, phase, decision
3. Si fue "Rechazar": pide el feedback via modal de Slack
4. Llama a graph.invoke(Command(resume=...), config) para reanudar el ciclo
5. Actualiza el mensaje de Slack con el resultado

Para correrlo en desarrollo:
  uvicorn api.slack_webhook:app --reload --port 8000

Para exponerlo a Slack:
  ngrok http 8000
  → Copiar la URL de ngrok en la Slack App > Interactivity > Request URL
"""

import json
import hashlib
import hmac
import time
from typing import Any

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from langgraph.types import Command

from graph.mach_graph import build_graph, get_graph_config
from tools.slack_tools import _slack
from config.settings import SLACK_SIGNING_SECRET


app = FastAPI(title="MACH Race — Slack HITL Webhook")

# Grafo compartido — singleton (el checkpointer guarda el estado por thread_id)
_graph = build_graph()


# ── Endpoint principal ────────────────────────────────────────────────────────

@app.post("/slack/interactive")
async def slack_interactive(request: Request, background_tasks: BackgroundTasks):
    """
    Recibe los payloads de botones y modales de Slack.

    Slack envía los payloads como application/x-www-form-urlencoded
    con un campo "payload" que contiene un JSON.
    """
    # 1. Verificar que la request viene de Slack
    await _verify_slack_signature(request)

    # 2. Parsear el payload
    body = await request.body()
    form_data = dict(item.split("=", 1) for item in body.decode().split("&"))
    payload_str = form_data.get("payload", "{}")

    # URL-decode el payload
    from urllib.parse import unquote_plus
    payload = json.loads(unquote_plus(payload_str))

    payload_type = payload.get("type")

    if payload_type == "block_actions":
        # Click en botón (Aprobar o Rechazar)
        background_tasks.add_task(_handle_button_click, payload)
        # Slack requiere respuesta inmediata (3 segundos)
        return JSONResponse(content={"ok": True})

    elif payload_type == "view_submission":
        # Envío del modal de feedback (cuando rechaza)
        background_tasks.add_task(_handle_modal_submit, payload)
        return JSONResponse(content={"response_action": "clear"})

    return JSONResponse(content={"ok": True})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MACH Race Slack Webhook"}


# ── Handlers ──────────────────────────────────────────────────────────────────

async def _handle_button_click(payload: dict[str, Any]):
    """
    Procesa el click en botón Aprobar o Rechazar.

    Si es Aprobar: reanuda el grafo directamente.
    Si es Rechazar: abre un modal de Slack pidiendo el feedback,
                    y espera el envío del modal para reanudar.
    """
    action = payload["actions"][0]
    action_id = action["action_id"]
    button_value = json.loads(action["value"])

    thread_id = button_value["thread_id"]
    phase = button_value["phase"]
    reviewer_id = payload["user"]["id"]

    print(f"\n[Webhook] Acción recibida: {action_id}")
    print(f"  thread_id: {thread_id[:8]}...")
    print(f"  phase: {phase}")
    print(f"  reviewer: {reviewer_id}")

    if action_id == "hitl_approve":
        # Reanudar el grafo con aprobación
        resume_payload = {
            "decision":  "approve",
            "feedback":  None,
            "reviewer":  reviewer_id,
            "timestamp": _now(),
        }
        _resume_graph(thread_id, resume_payload)

    elif action_id == "hitl_reject":
        # Abrir modal pidiendo feedback antes de reanudar
        trigger_id = payload["trigger_id"]
        await _open_feedback_modal(
            trigger_id=trigger_id,
            thread_id=thread_id,
            phase=phase,
            channel_id=payload["container"]["channel_id"],
            message_ts=payload["container"]["message_ts"],
        )


async def _handle_modal_submit(payload: dict[str, Any]):
    """
    Procesa el envío del modal de feedback.
    Reanuda el grafo con la decisión de rechazo + el feedback.
    """
    values = payload["view"]["state"]["values"]
    feedback = values.get("feedback_block", {}).get("feedback_input", {}).get("value", "")

    # Los metadatos del modal guardan thread_id y phase
    private_metadata = json.loads(payload["view"].get("private_metadata", "{}"))
    thread_id = private_metadata.get("thread_id")
    reviewer_id = payload["user"]["id"]

    if not thread_id:
        print("[Webhook] Error: no thread_id en modal metadata")
        return

    resume_payload = {
        "decision":  "reject",
        "feedback":  feedback,
        "reviewer":  reviewer_id,
        "timestamp": _now(),
    }
    _resume_graph(thread_id, resume_payload)


def _resume_graph(thread_id: str, resume_payload: dict):
    """
    Reanuda el grafo LangGraph con el payload de la decisión humana.

    El resume_payload se convierte en el return value de interrupt()
    dentro del nodo HITL correspondiente.
    """
    config = get_graph_config(thread_id)

    print(f"\n[Webhook] Reanudando grafo para thread {thread_id[:8]}...")
    print(f"  Decisión: {resume_payload['decision']}")

    try:
        result = _graph.invoke(
            Command(resume=resume_payload),
            config=config,
        )
        next_interrupted = result.get("__interrupt__")
        if next_interrupted:
            print(f"[Webhook] Grafo pausado en nuevo checkpoint: {next_interrupted[0].value.get('phase')}")
        else:
            print(f"[Webhook] Grafo avanzó a fase: {result.get('current_phase', 'unknown')}")
    except Exception as e:
        print(f"[Webhook] Error al reanudar grafo: {e}")


async def _open_feedback_modal(
    trigger_id: str,
    thread_id: str,
    phase: str,
    channel_id: str,
    message_ts: str,
):
    """
    Abre un modal en Slack pidiendo el feedback de rechazo.
    El thread_id y phase se guardan en private_metadata para recuperarlos
    cuando el modal se envíe.
    """
    _slack.views_open(
        trigger_id=trigger_id,
        view={
            "type":             "modal",
            "callback_id":      "hitl_feedback_modal",
            "title":            {"type": "plain_text", "text": "Feedback de rechazo"},
            "submit":           {"type": "plain_text", "text": "Enviar y rechazar"},
            "close":            {"type": "plain_text", "text": "Cancelar"},
            "private_metadata": json.dumps({
                "thread_id":  thread_id,
                "phase":      phase,
                "channel_id": channel_id,
                "message_ts": message_ts,
            }),
            "blocks": [
                {
                    "type":    "section",
                    "text":    {"type": "mrkdwn", "text": f"Estás rechazando la fase *{phase}*."},
                },
                {
                    "type":    "input",
                    "block_id": "feedback_block",
                    "label":   {"type": "plain_text", "text": "¿Qué debe corregir el agente?"},
                    "element": {
                        "type":        "plain_text_input",
                        "action_id":   "feedback_input",
                        "multiline":   True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Ej: Agregar criterio de latencia, cambiar el modelo de datos..."
                        }
                    }
                }
            ]
        }
    )


# ── Verificación de firma Slack ────────────────────────────────────────────────

async def _verify_slack_signature(request: Request):
    """
    Verifica que la request viene realmente de Slack usando HMAC-SHA256.
    Slack incluye X-Slack-Signature y X-Slack-Request-Timestamp en cada request.

    Ver: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Rechazar requests con más de 5 minutos de antigüedad (replay attacks)
    if abs(time.time() - float(timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request too old")

    body = await request.body()
    sig_base = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_base.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()
