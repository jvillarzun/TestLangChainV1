"""
dashboard/app.py
────────────────
Dashboard Streamlit del ciclo ADLC — MACH Race 2026.

Uso:
    streamlit run dashboard/app.py --server.port 8501

Requiere CHECKPOINTER=sqlite en .env para leer estado entre procesos.
"""

import sqlite3
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CHECKPOINTER, SQLITE_PATH

st.set_page_config(
    page_title="MACH Race 2026 — ADLC Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

PHASES = ["init", "prd", "ux_arch", "dev", "qa", "infra_sec", "done"]

PHASE_LABELS = {
    "init":      "🚀 Init",
    "prd":       "📋 PRD",
    "ux_arch":   "🎨 UX + ARQ",
    "dev":       "💻 DEV",
    "qa":        "🧪 QA",
    "infra_sec": "⚙️ INFRA + SEC",
    "done":      "✅ Done",
}

DELIVERABLES = [
    ("prd_content",      "📋 PRDSPECS.md",   "PRDSPECS.md"),
    ("ux_content",       "🎨 UXSPECS.md",    "UXSPECS.md"),
    ("arch_content",     "🏗️ ARQSPECS.md",   "ARQSPECS.md"),
    ("dev_content",      "💻 DEVSPECS.md",   "DEVSPECS.md"),
    ("qa_content",       "🧪 QASCPECS.md",   "QASCPECS.md"),
    ("infra_content",    "⚙️ INFESPEOS.md",  "INFESPEOS.md"),
    ("security_content", "🔐 DEVSECOPS.md",  "DEVSECOPS.md"),
]


# ── DB connection — @st.cache_resource: una sola conexión compartida por sesión ──

@st.cache_resource
def _get_db_connection():
    return sqlite3.connect(SQLITE_PATH, check_same_thread=False)


# ── Data loaders — @st.cache_data con TTL corto para refrescar estado del ciclo ──

@st.cache_data(ttl=5)
def _load_state(thread_id: str) -> dict | None:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer = SqliteSaver(_get_db_connection())
        checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return None
        return checkpoint.get("channel_values", {})
    except Exception as e:
        st.error(f"Error leyendo checkpointer: {e}")
        return None


@st.cache_data(ttl=10)
def _list_thread_ids() -> list[str]:
    try:
        cur = _get_db_connection().execute(
            "SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 20"
        )
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def _phase_index(phase: str) -> int:
    try:
        return PHASES.index(phase)
    except ValueError:
        return 0


# ── Sidebar ───────────────────────────────────────────────────────────────────

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

    thread_ids = _list_thread_ids()
    params = st.query_params
    default_thread = params.get("thread_id", thread_ids[0] if thread_ids else "")

    if thread_ids:
        selected = st.selectbox("Ciclo activo", thread_ids, index=0)
        thread_id = st.text_input("O ingresa Thread ID manual", value=default_thread or selected)
    else:
        thread_id = st.text_input("Thread ID del ciclo", value=default_thread, placeholder="uuid del ciclo activo")

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (5s)", value=False)
    if st.button("🔄 Refresh ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Fases del ciclo:")
    for p in PHASES:
        st.caption(f"  {PHASE_LABELS[p]}")


# ── Main ──────────────────────────────────────────────────────────────────────

if not thread_id:
    st.info("👈 Ingresa un Thread ID en el sidebar para ver el estado del ciclo.")
    st.stop()

state = _load_state(thread_id)

if state is None:
    st.error(f"No se encontró estado para thread `{thread_id}`.")
    st.stop()

current_phase = state.get("current_phase", "init")
challenge_name = state.get("challenge_name", "—")
challenge_type = state.get("challenge_type", "—")
phase_idx = _phase_index(current_phase)
progress = phase_idx / (len(PHASES) - 1)
qa_passed = state.get("qa_passed")

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_phase, col_qa = st.columns([3, 1, 1])
with col_title:
    st.title(f"🏁 {challenge_name}")
    st.caption(f"Thread: `{thread_id}` · Tipo: **{challenge_type}**")
with col_phase:
    st.metric("Fase actual", PHASE_LABELS.get(current_phase, current_phase), border=True)
with col_qa:
    qa_label = "✅ PASS" if qa_passed is True else ("❌ FAIL" if qa_passed is False else "⏳ Pendiente")
    st.metric("QA", qa_label, border=True)

# ── Progress timeline ─────────────────────────────────────────────────────────
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

# ── Error state ───────────────────────────────────────────────────────────────
error_phase = state.get("error_phase")
error_message = state.get("error_message")
if error_phase and error_message:
    st.error(f"**Error en fase `{error_phase}`:** {error_message}", icon="🚨")

# ── Deliverables ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Entregables generados")

outputs_dir = Path(__file__).parent.parent / "outputs"

for state_key, label, filename in DELIVERABLES:
    content = state.get(state_key)
    file_path = outputs_dir / filename
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

# ── HITL decisions ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Historial de decisiones HITL")

decisions = state.get("hitl_decisions", [])
if not decisions:
    st.caption("Sin decisiones registradas aún.")
else:
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

# ── Jira ──────────────────────────────────────────────────────────────────────
jira_epic = state.get("jira_epic_key")
jira_stories = state.get("jira_story_keys", [])
if jira_epic or jira_stories:
    st.divider()
    st.subheader("Jira")
    with st.container(horizontal=True):
        st.metric("Epic", jira_epic or "—", border=True)
        st.metric("Stories/Tasks", len(jira_stories), border=True)
    if jira_stories:
        st.caption("Keys: " + ", ".join(f"`{k}`" for k in jira_stories if k))

# ── Challenge info ────────────────────────────────────────────────────────────
with st.expander("ℹ️ Detalles del challenge"):
    st.markdown(f"**Descripción:** {state.get('challenge_description', '—')}")
    for c in state.get("challenge_success_criteria", []):
        st.markdown(f"  - {c}")
    if state.get("cycle_start_time"):
        st.caption(f"Inicio: {state['cycle_start_time']}")
    if state.get("cycle_end_time"):
        st.caption(f"Fin: {state['cycle_end_time']}")

# ── Auto-refresh — @st.fragment con run_every evita rerun del app completo ────

@st.fragment(run_every=5 if auto_refresh else None)
def _auto_refresh_indicator():
    if auto_refresh:
        st.caption("🔄 Auto-refresh activo — actualizando cada 5s")
        st.cache_data.clear()
        st.rerun()

_auto_refresh_indicator()
