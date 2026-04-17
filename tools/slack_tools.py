"""
tools/slack_tools.py
────────────────────
Herramientas de Slack para el ciclo ADLC.

Responsabilidades:
  1. notify_team()       — aviso general al canal del equipo
  2. notify_reviewer()   — DM con botones HITL a la persona correcta
  3. update_hitl_msg()   — actualiza el mensaje de Slack tras la decisión
                           (reemplaza botones con el resultado)

Los botones de Slack envían un payload POST al webhook de FastAPI
(api/slack_webhook.py), que luego reanuda el grafo con Command(resume=...).

Cada botón incluye en su `value` el thread_id del ciclo LangGraph,
para que el webhook sepa exactamente qué instancia reanudar.
"""

import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config.settings import SLACK_BOT_TOKEN, SLACK_USERS, SLACK_TEAM_CHANNEL, WEBHOOK_BASE_URL


# Singleton del cliente Slack
_slack = WebClient(token=SLACK_BOT_TOKEN)


# ── Mapeo de fases a configuración de HITL ────────────────────────────────────

PHASE_HITL_CONFIG = {
    "prd": {
        "reviewer_role": "po",
        "label":         "PRD listo para revisión",
        "deliverable":   "PRDSPECS.md",
        "emoji":         "📋",
        "instructions":  "Verificar que las User Stories cubren el challenge y que los criterios de aceptación son medibles.",
    },
    "ux_arch": {
        "reviewer_role": "architect",
        "label":         "Arquitectura lista para revisión",
        "deliverable":   "ARQSPECS.md + UXSPECS.md",
        "emoji":         "🏗️",
        "instructions":  "Verificar que la arquitectura es viable en AWS y que la latencia p95 es alcanzable.",
    },
    "dev": {
        "reviewer_role": "dev_lead",
        "label":         "PR listo para code review",
        "deliverable":   "DEVSPECS.md + PR en GitHub",
        "emoji":         "💻",
        "instructions":  "Revisar el PR en GitHub. Verificar que el código compila y los tests pasan.",
    },
    "qa": {
        "reviewer_role": "qa_lead",
        "label":         "QA sign-off pendiente",
        "deliverable":   "QASCPECS.md",
        "emoji":         "🧪",
        "instructions":  "Revisar que los 3 criterios críticos están PASS. Si hay blockers, rechazar con feedback.",
    },
    "infra_sec": {
        "reviewer_role": "devops",
        "label":         "Deploy en staging — verificar métricas",
        "deliverable":   "INFESPEOS.md + DEVSECOPS.md + deploy AWS",
        "emoji":         "⚙️",
        "instructions":  "Verificar que el endpoint responde en <200ms p95 en Grafana. Revisar el DEVSECOPS por findings críticos.",
    },
}


def notify_team(message: str, thread_id: str) -> None:
    """
    Envía un mensaje de estado al canal general del equipo.
    Se llama al inicio del ciclo, al completar cada fase, y al final.
    """
    try:
        _slack.chat_postMessage(
            channel=SLACK_TEAM_CHANNEL,
            text=message,
            blocks=[
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🏁 *MACH Race* · ciclo `{thread_id[:8]}` · {_now()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message}
                }
            ]
        )
    except SlackApiError as e:
        # No es crítico — el ciclo sigue aunque falle la notificación
        print(f"[Slack] Error en notify_team: {e.response['error']}")


def notify_reviewer(
    phase: str,
    thread_id: str,
    deliverable_content: str | None = None,
    extra_context: str | None = None,
) -> str | None:
    """
    Envía un DM al revisor de la fase con botones Aprobar/Rechazar.

    Retorna el `ts` (timestamp) del mensaje de Slack, que se guarda en el
    estado para poder actualizar el mensaje después de la decisión.

    El `value` de cada botón es un JSON con:
      - thread_id: para que el webhook sepa qué ciclo reanudar
      - phase:     para que el webhook registre la decisión correctamente
      - decision:  "approve" o "reject"
    """
    config = PHASE_HITL_CONFIG.get(phase)
    if not config:
        raise ValueError(f"Fase desconocida para HITL: {phase}")

    reviewer_id = SLACK_USERS.get(config["reviewer_role"], "")
    if not reviewer_id:
        print(f"[Slack] No hay user ID configurado para rol '{config['reviewer_role']}'")
        return None

    # Construir el preview del entregable (primeras 300 chars)
    preview = ""
    if deliverable_content:
        preview_text = deliverable_content[:300].strip()
        if len(deliverable_content) > 300:
            preview_text += "..."
        preview = f"\n```{preview_text}```"

    # Payload para los botones — el webhook necesita thread_id y phase
    approve_value = json.dumps({
        "thread_id": thread_id,
        "phase": phase,
        "decision": "approve"
    })
    reject_value = json.dumps({
        "thread_id": thread_id,
        "phase": phase,
        "decision": "reject"
    })

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{config['emoji']} MACH Race — {config['label']}"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Entregable:*\n{config['deliverable']}"},
                {"type": "mrkdwn", "text": f"*Ciclo ID:*\n`{thread_id[:8]}...`"},
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Qué revisar:*\n{config['instructions']}"
            }
        },
    ]

    # Preview del contenido si está disponible
    if preview:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Preview del entregable:*{preview}"}
        })

    # Contexto extra (ej: URL del PR de GitHub)
    if extra_context:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": extra_context}
        })

    blocks.append({"type": "divider"})

    # Botones Aprobar / Rechazar con feedback
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Aprobar"},
                "style": "primary",
                "value": approve_value,
                "action_id": "hitl_approve",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Rechazar con feedback"},
                "style": "danger",
                "value": reject_value,
                "action_id": "hitl_reject",
            }
        ]
    })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"_{_now()} · El ciclo está pausado esperando tu decisión._"}
        ]
    })

    try:
        response = _slack.chat_postMessage(
            channel=reviewer_id,   # DM directo al usuario
            text=f"MACH Race: {config['label']} — requiere tu revisión",
            blocks=blocks,
        )
        return response["ts"]
    except SlackApiError as e:
        print(f"[Slack] Error al enviar DM: {e.response['error']}")
        return None


def update_hitl_message(
    channel: str,
    ts: str,
    phase: str,
    decision: str,
    feedback: str | None = None,
) -> None:
    """
    Actualiza el mensaje HITL original (reemplaza los botones con el resultado).
    Se llama desde el webhook de Slack después de procesar la decisión.
    """
    config = PHASE_HITL_CONFIG.get(phase, {})
    emoji = "✅" if decision == "approve" else "❌"
    label = "Aprobado" if decision == "approve" else "Rechazado"
    color = "#2eb886" if decision == "approve" else "#e01e5a"

    reviewer_id = SLACK_USERS.get(config.get("reviewer_role", ""), "")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{config.get('emoji','🔄')} MACH Race — {config.get('label','Revisión')}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{label}* por <@{reviewer_id}> · {_now()}"
            }
        },
    ]

    if feedback:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Feedback:*\n{feedback}"}
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "_El ciclo ha sido reanudado._"}]
    })

    try:
        _slack.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"{label}")
    except SlackApiError as e:
        print(f"[Slack] Error al actualizar mensaje: {e.response['error']}")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
