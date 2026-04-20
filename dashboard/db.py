import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SQLITE_PATH


@st.cache_resource
def get_db_connection():
    import sqlite3
    return sqlite3.connect(SQLITE_PATH, check_same_thread=False)


@st.cache_data(ttl=5)
def load_state(thread_id: str) -> dict | None:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer = SqliteSaver(get_db_connection())
        checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return None
        return checkpoint.get("channel_values", {})
    except Exception as e:
        st.error(f"Error leyendo checkpointer: {e}")
        return None


@st.cache_data(ttl=10)
def list_thread_ids() -> list[str]:
    try:
        cur = get_db_connection().execute(
            "SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 20"
        )
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []
