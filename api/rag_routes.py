"""
api/rag_routes.py
──────────────────
Router FastAPI para la Knowledge Base RAG.
Se monta en /api/rag — completamente separado del resto de la API.

Endpoints:
  GET  /api/rag/agents                  → stats por agente (chunks, docs)
  POST /api/rag/upload/{agent}          → sube archivo a la colección del agente
  DEL  /api/rag/docs/{agent}/{doc_id}   → elimina un documento
  POST /api/rag/query/{agent}           → test: qué chunks recupera para una query
  POST /api/rag/run/{agent}             → test: ejecuta el agente con prompt libre + RAG
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

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


class QueryRequest(BaseModel):
    query: str
    n_results: int = 3


class RunRequest(BaseModel):
    prompt: str                  # descripción libre del challenge / pregunta
    challenge_name: str = "Test"
    challenge_type: str = "greenfield"
    n_results: int = 3


@router.post("/query/{agent}")
def test_query(agent: str, body: QueryRequest):
    """Devuelve los chunks que RAG recuperaría para una query — sin llamar al LLM."""
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from rag.chroma_store import query_context, _get_client
        client = _get_client()
        chunks = []
        if client:
            col = client.get_or_create_collection(f"agent_{agent}")
            total = col.count()
            if total > 0:
                results = col.query(
                    query_texts=[body.query],
                    n_results=min(body.n_results, total),
                    include=["documents", "metadatas", "distances"],
                )
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    chunks.append({
                        "text": doc,
                        "filename": meta.get("filename", ""),
                        "chunk": meta.get("chunk", 0),
                        "score": round(1 - dist, 3),  # cosine similarity approx
                    })
        return {"query": body.query, "chunks": chunks, "total_retrieved": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{agent}")
def test_run_agent(agent: str, body: RunRequest):
    """Ejecuta el agente con el prompt dado, inyectando contexto RAG si existe."""
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from nodes.helper import load_prompt, llm_invoke
        from rag.rag_helper import get_rag_context
        from config.settings import MODEL_DEV  # fallback model

        _agent_models = {
            "prd": "llama-3.3-70b-versatile",
            "ux":  "llama-3.3-70b-versatile",
            "arch":"llama-3.3-70b-versatile",
            "dev": "llama-3.3-70b-versatile",
            "qa":  "llama-3.3-70b-versatile",
            "infra":"llama-3.3-70b-versatile",
            "sec": "llama-3.3-70b-versatile",
        }
        model = _agent_models.get(agent, MODEL_DEV)

        # Cargar prompt del agente con valores de prueba
        try:
            system_prompt = load_prompt(
                agent,
                challenge_name=body.challenge_name,
                challenge_type=body.challenge_type,
                challenge_description=body.prompt,
                prd_content="[test — no disponible]",
                ux_content="[test — no disponible]",
                arch_content="[test — no disponible]",
                dev_content="[test — no disponible]",
                qa_content="[test — no disponible]",
                infra_content="[test — no disponible]",
                feedback="Sin feedback previo.",
            )
        except Exception:
            system_prompt = f"Eres el agente {agent.upper()}. Responde según tu especialidad."

        # Inyectar RAG si hay contexto
        rag_context = get_rag_context(agent, body.prompt, n_results=body.n_results)
        rag_chars = 0
        if rag_context:
            system_prompt += f"\n\n## Contexto de Knowledge Base ({agent.upper()}):\n{rag_context}"
            rag_chars = len(rag_context)

        output = llm_invoke(
            model=model,
            system_prompt=system_prompt,
            user_message=body.prompt,
            stub_content=f"[TEST_MODE] stub output para agente {agent}",
        )

        return {
            "agent": agent,
            "output": output,
            "rag_used": rag_chars > 0,
            "rag_chars": rag_chars,
            "model": model,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
