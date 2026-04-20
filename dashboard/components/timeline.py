import streamlit as st

from dashboard.constants import PHASES, PHASE_LABELS


def _phase_index(phase: str) -> int:
    try:
        return PHASES.index(phase)
    except ValueError:
        return 0


def render_timeline(current_phase: str) -> None:
    phase_idx = _phase_index(current_phase)
    progress = phase_idx / (len(PHASES) - 1)

    st.divider()
    st.subheader("Progreso del ciclo")

    phase_cols = st.columns(len(PHASES))
    for i, (phase, col) in enumerate(zip(PHASES, phase_cols)):
        with col:
            if i < phase_idx:
                st.success(PHASE_LABELS[phase], icon="✅")
            elif i == phase_idx:
                st.info(PHASE_LABELS[phase], icon="▶️")
            else:
                st.caption(PHASE_LABELS[phase])

    st.progress(progress)
