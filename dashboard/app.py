"""
dashboard/app.py
────────────────
Entry point del dashboard Streamlit del ciclo ADLC — MACH Race 2026.

Uso:
    streamlit run dashboard/app.py --server.port 8501

Requiere CHECKPOINTER=sqlite en .env para leer estado entre procesos.
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="MACH Race 2026 — ADLC Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.db import load_state
from dashboard.components.sidebar import render_sidebar
from dashboard.components.header import render_header
from dashboard.components.timeline import render_timeline
from dashboard.components.deliverables import render_deliverables
from dashboard.components.hitl import render_hitl_decisions
from dashboard.components.jira import render_jira
from dashboard.components.challenge import render_challenge_info
import config.settings as settings

_PHASES_REQUIRING_HITL = {"prd", "ux", "arch", "dev", "qa", "infra", "sec"}
_API_BASE = os.environ.get("WEBHOOK_BASE_URL", "http://mach-api:8000")


def _post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _API_BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def render_hitl_controls(state: dict, thread_id: str) -> None:
    st.sidebar.write(f"Debug SHOW_MANUAL_CONTROLS: {settings.SHOW_MANUAL_CONTROLS}")
    if not settings.SHOW_MANUAL_CONTROLS:
        return
    phase = state.get("current_phase", "init")
    if phase not in _PHASES_REQUIRING_HITL:
        return

    st.subheader("🔔 Checkpoint HITL — aprobación manual")
    st.caption(f"Fase en espera: **{phase.upper()}**")

    col_approve, col_gap, col_reject = st.columns([2, 1, 2])

    with col_approve:
        if st.button("✅ Aprobar (Manual)", use_container_width=True, type="primary"):
            try:
                st.toast("Enviando decisión…")
                _post_json("/api/cycle/resume", {"thread_id": thread_id, "decision": "approve"})
                st.rerun()
            except Exception as exc:
                st.error(f"Error al aprobar: {exc}")

    with col_reject:
        if st.button("❌ Rechazar (Manual)", use_container_width=True):
            try:
                st.toast("Enviando decisión…")
                _post_json("/api/cycle/resume", {"thread_id": thread_id, "decision": "reject"})
                st.rerun()
            except Exception as exc:
                st.error(f"Error al rechazar: {exc}")

    st.divider()


thread_id, auto_refresh = render_sidebar()

if not thread_id:
    st.info("👈 Ingresa un Thread ID en el sidebar para ver el estado del ciclo.")
    st.stop()

state = load_state(thread_id)

if state is None:
    st.error(f"No se encontró estado para thread `{thread_id}`.")
    st.stop()

render_header(state, thread_id)
render_timeline(state.get("current_phase", "init"))
render_hitl_controls(state, thread_id)
render_deliverables(state)
render_hitl_decisions(state)
render_jira(state)
render_challenge_info(state)


@st.fragment(run_every=5 if auto_refresh else None)
def _auto_refresh_indicator():
    if auto_refresh:
        st.caption("🔄 Auto-refresh activo — actualizando cada 5s")
        st.cache_data.clear()
        st.rerun()


_auto_refresh_indicator()
