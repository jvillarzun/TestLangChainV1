"""
rag/chroma_store.py
────────────────────
ChromaDB persistence layer — una colección por agente.
Soporta .txt, .md, .py, .kt, .swift, .java, .pdf
Si chromadb no está instalado, todas las funciones retornan vacío/None sin crash.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

RAG_DATA_DIR = Path(os.getenv("RAG_DATA_PATH", "/app/rag_data"))
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

AGENTS = ["prd", "ux", "arch", "dev", "qa", "infra", "sec"]


def _get_client():
    try:
        import chromadb
        RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(RAG_DATA_DIR))
    except ImportError:
        return None


def _chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c.strip()]


def _parse_file(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            import io
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return content.decode("utf-8", errors="ignore")


def upload_document(agent: str, filename: str, content: bytes) -> dict:
    client = _get_client()
    if client is None:
        return {"error": "chromadb not installed"}

    text = _parse_file(filename, content)
    if not text.strip():
        return {"error": "No text could be extracted from the file"}

    chunks = _chunk_text(text)
    collection = client.get_or_create_collection(f"agent_{agent}")
    doc_id = str(uuid.uuid4())

    collection.add(
        documents=chunks,
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        metadatas=[{"filename": filename, "doc_id": doc_id, "chunk": i} for i in range(len(chunks))],
    )
    return {"doc_id": doc_id, "filename": filename, "chunks": len(chunks)}


def query_context(agent: str, query: str, n_results: int = 3) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None
    try:
        collection = client.get_or_create_collection(f"agent_{agent}")
        total = collection.count()
        if total == 0:
            return None
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
        )
        docs = results.get("documents", [[]])[0]
        return "\n\n---\n\n".join(docs) if docs else None
    except Exception:
        return None


def get_agent_stats() -> list[dict]:
    client = _get_client()
    stats = []
    for agent in AGENTS:
        chunks, documents = 0, []
        if client:
            try:
                col = client.get_or_create_collection(f"agent_{agent}")
                chunks = col.count()
                if chunks > 0:
                    raw = col.get(include=["metadatas"])
                    seen: dict[str, str] = {}
                    for m in raw.get("metadatas", []):
                        did = m.get("doc_id", "")
                        fn = m.get("filename", "")
                        if did and did not in seen:
                            seen[did] = fn
                    documents = [{"doc_id": did, "filename": fn} for did, fn in seen.items()]
            except Exception:
                pass
        stats.append({"agent": agent, "chunks": chunks, "documents": documents})
    return stats


def delete_document(agent: str, doc_id: str) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        col = client.get_or_create_collection(f"agent_{agent}")
        raw = col.get(where={"doc_id": doc_id})
        ids = raw.get("ids", [])
        if ids:
            col.delete(ids=ids)
        return True
    except Exception:
        return False
