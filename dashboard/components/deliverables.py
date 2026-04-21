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
                if file_path.exists() and file_path.stat().st_size > 0:
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

    # ── Pull Requests abiertos por el Dev Agent ───────────────────────────────
    pr_urls: list[str] = state.get("dev_pr_urls") or []
    if state.get("dev_pr_url") and not pr_urls:
        pr_urls = [state["dev_pr_url"]]
    if pr_urls:
        st.divider()
        st.subheader("🔗 Pull Requests")
        for url in pr_urls:
            repo_label = "Backend" if "backend" in url.lower() else "Frontend" if "frontend" in url.lower() else "Repo"
            st.markdown(f"- [{repo_label} PR]({url})")
