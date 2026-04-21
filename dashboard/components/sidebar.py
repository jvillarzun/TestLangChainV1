import os
import json
import urllib.request

import streamlit as st

from config.settings import CHECKPOINTER
from dashboard.constants import PHASES, PHASE_LABELS
from dashboard.db import list_thread_ids


def render_sidebar() -> tuple[str, bool]:
    """
    Returns:
        (thread_id, auto_refresh)
    """
    with st.sidebar:
        st.title("🏁 MACH Race 2026")
        st.caption("ADLC Orchestrator Dashboard")
        st.divider()

        with st.expander("🚀 Nuevo ciclo", expanded=False):
            c_name = st.text_input("Nombre del desafío", value="FraudShield", key="new_c_name")
            c_type = st.selectbox("Tipo", ["greenfield", "brownfield"], key="new_c_type")
            c_desc = st.text_area(
                "Descripción",
                value="Describe el desafío aquí.",
                key="new_c_desc",
                height=80,
            )
            c_criteria_raw = st.text_area(
                "Criterios de éxito (uno por línea)",
                value="Definir criterios de éxito",
                key="new_c_criteria",
                height=70,
            )
            if st.button("🚀 Iniciar ciclo", use_container_width=True, type="primary"):
                criteria = [
                    l.strip() for l in c_criteria_raw.splitlines() if l.strip()
                ] or ["Definir criterios de éxito"]
                _url = (
                    os.environ.get("WEBHOOK_BASE_URL", "http://mach-api:8000")
                    + "/api/cycle/start"
                )
                try:
                    _payload = json.dumps({
                        "challenge_name": c_name,
                        "challenge_type": c_type,
                        "challenge_description": c_desc,
                        "challenge_success_criteria": criteria,
                    }).encode("utf-8")
                    _req = urllib.request.Request(
                        _url,
                        data=_payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(_req, timeout=15) as _resp:
                        _body = json.loads(_resp.read().decode("utf-8"))
                    new_tid = _body["thread_id"]
                    st.session_state["started_thread_id"] = new_tid
                    st.success(f"¡Ciclo iniciado! `{new_tid[:8]}...`")
                    st.query_params["thread_id"] = new_tid
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al iniciar el ciclo: {exc}")

        st.divider()
        if CHECKPOINTER != "sqlite":
            st.warning(
                "**CHECKPOINTER=memory** — dashboard no puede leer estado entre procesos.\n\n"
                "Cambiar a `CHECKPOINTER=sqlite` en `.env`.",
                icon="⚠️",
            )

        thread_ids = list_thread_ids()
        params = st.query_params
        default_thread = params.get("thread_id", thread_ids[0] if thread_ids else "")

        if thread_ids:
            selected = st.selectbox("Ciclo activo", thread_ids, index=0)
            thread_id = st.text_input("O ingresa Thread ID manual", value=default_thread or selected)
        else:
            thread_id = st.text_input(
                "Thread ID del ciclo",
                value=default_thread,
                placeholder="uuid del ciclo activo",
            )

        st.divider()
        auto_refresh = st.toggle("Auto-refresh (5s)", value=False)
        if st.button("🔄 Refresh ahora", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption("Fases del ciclo:")
        for p in PHASES:
            st.caption(f"  {PHASE_LABELS[p]}")

    return thread_id, auto_refresh
