"""
rag/rag_helper.py
──────────────────
Helper único para que los nodos consuman RAG sin importar si chromadb está instalado.
Retorna None si no hay contexto — nunca falla el ciclo.
"""

from typing import Optional


def get_rag_context(agent: str, query: str, n_results: int = 3) -> Optional[str]:
    """Returns relevant KB context for the agent, or None if unavailable/empty."""
    try:
        from rag.chroma_store import query_context
        return query_context(agent, query, n_results)
    except Exception:
        return None
