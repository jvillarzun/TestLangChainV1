import streamlit as st


def render_hitl_decisions(state: dict) -> None:
    st.divider()
    st.subheader("Historial de decisiones HITL")

    decisions = state.get("hitl_decisions", [])
    if not decisions:
        st.caption("Sin decisiones registradas aún.")
        return

    for d in reversed(decisions):
        icon = "✅" if d.get("decision") == "approve" else "❌"
        label_str = "Aprobado" if d.get("decision") == "approve" else "Rechazado"
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                st.markdown(f"**{icon} {label_str}**")
                st.caption(f"Fase: `{d.get('phase', '?')}`")
            with c2:
                st.caption(f"Revisor: `{d.get('reviewer', '?')}`")
                st.caption((d.get("timestamp") or "")[:16])
            with c3:
                if d.get("feedback"):
                    st.info(d["feedback"], icon="💬")
