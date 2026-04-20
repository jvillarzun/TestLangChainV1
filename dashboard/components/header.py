import streamlit as st

from dashboard.constants import PHASE_LABELS


def render_header(state: dict, thread_id: str) -> None:
    current_phase = state.get("current_phase", "init")
    challenge_name = state.get("challenge_name", "—")
    challenge_type = state.get("challenge_type", "—")
    qa_passed = state.get("qa_passed")

    col_title, col_phase, col_qa = st.columns([3, 1, 1])
    with col_title:
        st.title(f"🏁 {challenge_name}")
        st.caption(f"Thread: `{thread_id}` · Tipo: **{challenge_type}**")
    with col_phase:
        st.metric("Fase actual", PHASE_LABELS.get(current_phase, current_phase), border=True)
    with col_qa:
        qa_label = "✅ PASS" if qa_passed is True else ("❌ FAIL" if qa_passed is False else "⏳ Pendiente")
        st.metric("QA", qa_label, border=True)

    error_phase = state.get("error_phase")
    error_message = state.get("error_message")
    if error_phase and error_message:
        st.error(f"**Error en fase `{error_phase}`:** {error_message}", icon="🚨")
