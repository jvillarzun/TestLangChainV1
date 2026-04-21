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
  cloudflared tunnel --url http://localhost:8000
  → Copiar la URL en la Slack App > Interactivity > Request URL
"""

import json
import hashlib
import hmac
import time
from typing import Any
from pathlib import Path as _Path

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from graph.singleton import get_graph
from graph.mach_graph import get_graph_config
from tools.slack_tools import _slack
from config.settings import SLACK_SIGNING_SECRET
from api.control import router as control_router


app = FastAPI(title="MACH Race — Slack HITL Webhook")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control_router)

_outputs_dir = _Path(__file__).parent.parent / "outputs"
_outputs_dir.mkdir(exist_ok=True)

# Raw files en /deliverables (para descargas)
app.mount("/deliverables", StaticFiles(directory=str(_outputs_dir)), name="deliverables")

_graph = get_graph()


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


@app.get("/view/{filename}", response_class=HTMLResponse)
async def view_deliverable(filename: str):
    """Renderiza un .md de outputs/ como HTML con sintaxis resaltada."""
    if not filename.endswith(".md") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Archivo inválido")

    file_path = _outputs_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} aún no generado")

    content = file_path.read_text(encoding="utf-8")

    try:
        import markdown
        body_html = markdown.markdown(content, extensions=["tables", "fenced_code"])
    except ImportError:
        # Fallback: mostrar como <pre> si markdown no está instalado
        body_html = f"<pre>{content}</pre>"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{filename} — MACH Race 2026</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 860px; margin: 40px auto; padding: 0 20px;
           color: #1a1a2e; background: #f8f9fa; }}
    h1, h2, h3 {{ color: #16213e; border-bottom: 1px solid #dee2e6; padding-bottom: 6px; }}
    code {{ background: #e9ecef; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
    pre {{ background: #212529; color: #f8f9fa; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    pre code {{ background: none; padding: 0; color: inherit; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #dee2e6; padding: 8px 12px; text-align: left; }}
    th {{ background: #e9ecef; font-weight: 600; }}
    blockquote {{ border-left: 4px solid #6c757d; margin: 0; padding: 8px 16px; color: #6c757d; }}
    .header {{ background: #16213e; color: white; padding: 12px 20px; border-radius: 8px;
               margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
    .header a {{ color: #adb5bd; font-size: 0.85em; text-decoration: none; }}
    .header a:hover {{ color: white; }}
  </style>
</head>
<body>
  <div class="header">
    <span>🏁 MACH Race 2026 — {filename}</span>
    <a href="/deliverables/{filename}" download>⬇ Descargar</a>
  </div>
  {body_html}
</body>
</html>"""
    return HTMLResponse(content=html)


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
        result = get_graph().invoke(
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
            "submit":           {"type": "plain_text", "text": "Rehacer con feedback"},
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
                    "text":    {"type": "mrkdwn", "text": f"El agente rehará la fase *{phase}* con tus instrucciones."},
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
