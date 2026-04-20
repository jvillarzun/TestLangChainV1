import streamlit as st


def render_challenge_info(state: dict) -> None:
    with st.expander("ℹ️ Detalles del challenge"):
        st.markdown(f"**Descripción:** {state.get('challenge_description', '—')}")
        for c in state.get("challenge_success_criteria", []):
            st.markdown(f"  - {c}")
        if state.get("cycle_start_time"):
            st.caption(f"Inicio: {state['cycle_start_time']}")
        if state.get("cycle_end_time"):
            st.caption(f"Fin: {state['cycle_end_time']}")
