"""
api/rag_routes.py
──────────────────
Router FastAPI para la Knowledge Base RAG.
Se monta en /api/rag — completamente separado del resto de la API.

Endpoints:
  GET  /api/rag/agents                  → stats por agente (chunks, docs)
  GET  /api/rag/models                  → lista de modelos Groq disponibles
  POST /api/rag/upload/{agent}          → sube archivo a la colección del agente
  DEL  /api/rag/docs/{agent}/{doc_id}   → elimina un documento
  POST /api/rag/query/{agent}           → test: chunks RAG para una query
  POST /api/rag/run/{agent}             → test: ejecuta agente con prompt libre + RAG + model override
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from config.settings import MODEL_DEV as _DEFAULT_MODEL

router = APIRouter(prefix="/api/rag", tags=["rag"])

_VALID_AGENTS = {"prd", "ux", "arch", "dev", "qa", "infra", "sec"}
_VALID_EXTENSIONS = {".txt", ".md", ".py", ".kt", ".swift", ".java", ".pdf", ".ts", ".js"}

_MODEL_LIST = [
    {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
    {"id": "llama-3.1-70b-versatile", "label": "Llama 3.1 70B"},
    {"id": "llama-3.1-8b-instant",    "label": "Llama 3.1 8B (fast)"},
    {"id": "mixtral-8x7b-32768",      "label": "Mixtral 8x7B"},
    {"id": "gemma2-9b-it",            "label": "Gemma 2 9B"},
]
# El default lo toma de settings.py (MODEL_DEV) — si cambia ahí, refleja aquí
GROQ_MODELS = [{**m, "default": m["id"] == _DEFAULT_MODEL} for m in _MODEL_LIST]
DEFAULT_MODEL = "llama-3.3-70b-versatile"


@router.get("/agents")
def list_agents():
    try:
        from rag.chroma_store import get_agent_stats
        return {"agents": get_agent_stats()}
    except Exception as e:
        return {"agents": [], "error": str(e)}


@router.get("/models")
def list_models():
    return {"models": GROQ_MODELS}


@router.post("/upload/{agent}")
async def upload_document(agent: str, file: UploadFile = File(...)):
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid. Use: {sorted(_VALID_AGENTS)}")

    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in _VALID_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"File type '{suffix}' not supported.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
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
    prompt: str
    challenge_name: str = "Test"
    challenge_type: str = "greenfield"
    n_results: int = 3
    model: str | None = None  # override per-request; None = use agent default


@router.post("/query/{agent}")
def test_query(agent: str, body: QueryRequest):
    """Devuelve chunks RAG para una query sin llamar al LLM."""
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from rag.chroma_store import _get_client
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
                        "text":     doc,
                        "filename": meta.get("filename", ""),
                        "chunk":    meta.get("chunk", 0),
                        "score":    round(1 - dist, 3),
                    })
        return {"query": body.query, "chunks": chunks, "total_retrieved": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _detect_artifact(text: str) -> tuple[str, str]:
    """
    Detecta si el output contiene HTML y lo extrae.
    Retorna (artifact_type, clean_content).
    artifact_type: 'html' | 'md'
    """
    import re
    # HTML en bloque de código
    match = re.search(r"```html\n?([\s\S]*?)```", text)
    if match:
        return "html", match.group(1).strip()
    # HTML suelto
    if "<!DOCTYPE html" in text or "<html" in text:
        return "html", text.strip()
    return "md", text.strip()


def _save_artifact(agent: str, content: str, ext: str) -> str:
    """Guarda el artefacto en outputs/ y retorna la URL relativa."""
    import uuid
    from pathlib import Path
    outputs = Path(__file__).parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)
    filename = f"rag_{agent}_{uuid.uuid4().hex[:8]}.{ext}"
    (outputs / filename).write_text(content, encoding="utf-8")
    return f"/deliverables/{filename}"


@router.post("/run/{agent}")
def test_run_agent(agent: str, body: RunRequest):
    """
    Ejecuta el agente con prompt + RAG opcional.
    Guarda el output como archivo y devuelve la URL — evita JSON gigante
    y permite previsualizar HTML directo desde la URL.
    """
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from nodes.helper import load_prompt, llm_invoke
        from rag.rag_helper import get_rag_context

        model = body.model or DEFAULT_MODEL

        valid_ids = {m["id"] for m in GROQ_MODELS}
        if model not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Model '{model}' not valid.")

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
                github_plan="",
                repo_be_name="",
                repo_fe_name="",
                feedback="Sin feedback previo.",
            )
        except Exception:
            system_prompt = f"Eres el agente {agent.upper()}. Responde con detalle según tu especialidad."

        rag_context = get_rag_context(agent, body.prompt, n_results=body.n_results)
        rag_chars = 0
        if rag_context:
            system_prompt += f"\n\n## Knowledge Base ({agent.upper()}):\n{rag_context}"
            rag_chars = len(rag_context)

        output = llm_invoke(
            model=model,
            system_prompt=system_prompt,
            user_message=body.prompt,
            stub_content=f"[TEST_MODE] stub — agente {agent} · modelo {model}",
        )

        artifact_type, clean = _detect_artifact(output)
        ext = "html" if artifact_type == "html" else "md"
        artifact_url = _save_artifact(agent, clean, ext)

        return {
            "agent":         agent,
            "artifact_url":  artifact_url,
            "artifact_type": artifact_type,
            "rag_used":      rag_chars > 0,
            "rag_chars":     rag_chars,
            "model":         model,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
