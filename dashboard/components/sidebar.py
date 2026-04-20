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
