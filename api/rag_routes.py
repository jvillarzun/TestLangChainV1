"""
api/rag_routes.py
──────────────────
Router FastAPI para la Knowledge Base RAG.
Se monta en /api/rag — completamente separado del resto de la API.

Endpoints:
  GET  /api/rag/agents                  → stats por agente (chunks, docs)
  POST /api/rag/upload/{agent}          → sube archivo a la colección del agente
  DEL  /api/rag/docs/{agent}/{doc_id}   → elimina un documento
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/rag", tags=["rag"])

_VALID_AGENTS = {"prd", "ux", "arch", "dev", "qa", "infra", "sec"}
_VALID_EXTENSIONS = {".txt", ".md", ".py", ".kt", ".swift", ".java", ".pdf", ".ts", ".js"}


@router.get("/agents")
def list_agents():
    try:
        from rag.chroma_store import get_agent_stats
        return {"agents": get_agent_stats()}
    except Exception as e:
        return {"agents": [], "error": str(e)}


@router.post("/upload/{agent}")
async def upload_document(agent: str, file: UploadFile = File(...)):
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid. Use: {sorted(_VALID_AGENTS)}")

    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in _VALID_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"File type '{suffix}' not supported. Use: {sorted(_VALID_EXTENSIONS)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        from rag.chroma_store import upload_document as _upload
        result = _upload(agent, file.filename or "unknown", content)
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/docs/{agent}/{doc_id}")
def delete_document(agent: str, doc_id: str):
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from rag.chroma_store import delete_document as _delete
        _delete(agent, doc_id)
        return {"deleted": True, "doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
