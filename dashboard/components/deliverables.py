from pathlib import Path

import streamlit as st

from dashboard.constants import DELIVERABLES

_OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"


def render_deliverables(state: dict) -> None:
    st.divider()
    st.subheader("Entregables generados")

    for state_key, label, filename in DELIVERABLES:
        content = state.get(state_key)
        file_path = _OUTPUTS_DIR / filename
        if content:
            with st.expander(f"{label} ✅", expanded=False):
                st.markdown(content)
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Descargar {filename}",
                            data=f,
                            file_name=filename,
                            mime="text/markdown",
                            key=f"dl_{filename}",
                        )
        else:
            st.caption(f"⏳ {label} — pendiente")
