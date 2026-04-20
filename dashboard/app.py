"""
dashboard/app.py
────────────────
Entry point del dashboard Streamlit del ciclo ADLC — MACH Race 2026.

Uso:
    streamlit run dashboard/app.py --server.port 8501

Requiere CHECKPOINTER=sqlite en .env para leer estado entre procesos.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.db import load_state
from dashboard.components.sidebar import render_sidebar
from dashboard.components.header import render_header
from dashboard.components.timeline import render_timeline
from dashboard.components.deliverables import render_deliverables
from dashboard.components.hitl import render_hitl_decisions
from dashboard.components.jira import render_jira
from dashboard.components.challenge import render_challenge_info

st.set_page_config(
    page_title="MACH Race 2026 — ADLC Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
