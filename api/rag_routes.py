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
router = APIRouter(prefix="/api/rag", tags=["rag"])

_VALID_AGENTS = {"prd", "ux", "arch", "dev", "qa", "infra", "sec"}
_VALID_EXTENSIONS = {".txt", ".md", ".py", ".kt", ".swift", ".java", ".pdf", ".ts", ".js"}

DEFAULT_MODEL = "llama-3.1-8b-instant"

_MODEL_LIST = [
    {"id": "gpt-4o-mini",             "label": "GPT-4o Mini (OpenAI)"},
    {"id": "gpt-4o",                  "label": "GPT-4o (OpenAI)"},
    {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
    {"id": "llama-3.1-70b-versatile", "label": "Llama 3.1 70B"},
    {"id": "llama-3.1-8b-instant",    "label": "Llama 3.1 8B (fast)"},
    {"id": "mixtral-8x7b-32768",      "label": "Mixtral 8x7B"},
    {"id": "gemma2-9b-it",            "label": "Gemma 2 9B"},
]
GROQ_MODELS = [{**m, "default": m["id"] == DEFAULT_MODEL} for m in _MODEL_LIST]


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


class IterateRequest(BaseModel):
    artifact_url: str
    feedback: str
    model: str | None = None
    n_results: int = 3


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


def _build_sandbox_prompt(agent: str, user_prompt: str) -> str:
    """
    Prompt de sandbox optimizado para generar artefactos visuales completos.
    NO usa dev_prompt.md (que es para DEVSPECS/PRs del ciclo ADLC).
    """
    return f"""Eres el agente {agent.upper()} de MACHBank — un desarrollador senior experto en UI/UX.

## Tu tarea
El usuario te pide generar un artefacto. Debes producir código COMPLETO y FUNCIONAL.

## Reglas OBLIGATORIAS para HTML

1. **HTML completo**: Siempre incluye `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`
2. **CSS inline en `<style>`**: TODOS los estilos dentro de `<head><style>...</style></head>`
   - Colores, gradientes, sombras, bordes redondeados
   - Tipografía: font-family, font-size, font-weight, line-height
   - Espaciado: margin, padding consistentes
   - Layout: flexbox o grid para estructura
3. **Responsive**: Incluye `<meta name="viewport">` y media queries para mobile
4. **Diseño profesional**: NO texto plano sin estilos. Debe verse como una app real:
   - Paleta de colores coherente (usa morados/violetas como marca MACHBank)
   - Jerarquía visual clara (headings, cards, secciones)
   - Hover states en elementos interactivos
   - Iconos con emojis o SVG inline si aplica
5. **NO uses CDNs externos** — todo el CSS debe ser inline en `<style>`
6. **Responde SOLO con el HTML** — sin explicaciones, sin bloques markdown

## Reglas para Markdown
- Estructura clara con headings, listas, tablas
- Código con syntax highlighting markers

## Si hay templates de referencia
- COPIA la estructura del template como base
- ADAPTA el contenido al pedido del usuario
- MEJORA los estilos: agrega CSS completo si el template no tiene
- MANTÉN las secciones y patrones del template

## Paleta MACHBank
- Primary: #7C3AED (violet-600)
- Primary dark: #5B21B6 (violet-800)
- Primary light: #A78BFA (violet-400)
- Background: #F8FAFC (slate-50)
- Surface: #FFFFFF
- Text primary: #0F172A (slate-900)
- Text secondary: #475569 (slate-600)
- Success: #10B981
- Error: #EF4444
"""


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
    Ejecuta el agente con prompt + RAG + templates.
    Usa un system prompt de sandbox optimizado para generar artefactos visuales.
    """
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from nodes.helper import llm_invoke
        from rag.rag_helper import get_rag_context

        model = body.model or DEFAULT_MODEL

        valid_ids = {m["id"] for m in GROQ_MODELS}
        if model not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Model '{model}' not valid.")

        # System prompt de sandbox — enfocado en generar artefactos completos
        system_prompt = _build_sandbox_prompt(agent, body.prompt)

        rag_context = get_rag_context(agent, body.prompt, n_results=body.n_results)
        rag_chars = 0
        if rag_context:
            system_prompt += f"\n\n## Knowledge Base ({agent.upper()}):\n{rag_context}"
            rag_chars = len(rag_context)

        # Templates completos — inyectar como base
        try:
            from rag.template_matcher import get_template_context
            tpl_context = get_template_context(agent, body.prompt)
            if tpl_context:
                system_prompt += (
                    f"\n\n## 📐 Templates de referencia (USAR COMO BASE)\n"
                    f"Los siguientes templates son archivos REALES del proyecto. "
                    f"DEBES usarlos como punto de partida. Copia su estructura HTML, "
                    f"adapta el contenido al pedido del usuario, y AGREGA estilos CSS "
                    f"completos con colores, tipografía, espaciado y responsive design.\n\n"
                    f"{tpl_context}"
                )
                rag_chars += len(tpl_context)
        except Exception:
            pass

        output, _usage = llm_invoke(
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


@router.post("/iterate/{agent}")
def iterate_artifact(agent: str, body: IterateRequest):
    """
    Itera sobre un artefacto existente con feedback del usuario.
    Lee el artefacto anterior, lo pasa como contexto y aplica el feedback.
    """
    if agent not in _VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' not valid")
    try:
        from pathlib import Path
        from nodes.helper import llm_invoke
        from rag.rag_helper import get_rag_context

        model = body.model or DEFAULT_MODEL
        valid_ids = {m["id"] for m in GROQ_MODELS}
        if model not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Model '{model}' not valid.")

        # Leer artefacto anterior desde disco
        filename = body.artifact_url.split("/")[-1]
        artifact_path = Path(__file__).parent.parent / "outputs" / filename
        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="Artefacto anterior no encontrado")
        previous_content = artifact_path.read_text(encoding="utf-8")

        # Detectar tipo del artefacto anterior
        prev_type, _ = _detect_artifact(previous_content)
        is_html = prev_type == "html" or filename.endswith(".html")

        # RAG context
        rag_context = get_rag_context(agent, body.feedback, n_results=body.n_results)
        rag_chars = len(rag_context) if rag_context else 0

        system_prompt = (
            f"Eres el agente {agent.upper()} de MACHBank — un desarrollador senior experto en UI/UX.\n"
            f"El usuario generó un artefacto y quiere mejorarlo.\n\n"
            f"## Artefacto actual\n```{'html' if is_html else 'markdown'}\n{previous_content}\n```\n\n"
            f"## Instrucciones\n"
            f"- Aplica el feedback del usuario al artefacto\n"
            f"- Devuelve el artefacto COMPLETO modificado, no solo los cambios\n"
            f"- {'Devuelve HTML completo válido con <!DOCTYPE html>, <head> con <style> CSS completo, y <body>. TODO el CSS debe estar inline en <style>, NO uses CDNs.' if is_html else 'Devuelve Markdown completo'}\n"
            f"- {'El HTML debe verse profesional: colores, tipografía, espaciado, responsive, hover states.' if is_html else ''}\n"
            f"- NO envuelvas la respuesta en bloques de código markdown\n"
            f"- Responde SOLO con el artefacto, sin explicaciones adicionales\n"
        )
        if rag_context:
            system_prompt += f"\n\n## Knowledge Base ({agent.upper()}):\n{rag_context}"

        # Templates completos como referencia
        try:
            from rag.template_matcher import get_template_context
            tpl_context = get_template_context(agent, body.feedback)
            if tpl_context:
                system_prompt += (
                    f"\n\n## 📐 Templates de referencia\n"
                    f"Usa estos templates como guía de estructura y estilos:\n\n"
                    f"{tpl_context}"
                )
                rag_chars += len(tpl_context)
        except Exception:
            pass

        output, _usage = llm_invoke(
            model=model,
            system_prompt=system_prompt,
            user_message=body.feedback,
            stub_content=f"[TEST_MODE] stub iteración — agente {agent}",
        )

        artifact_type, clean = _detect_artifact(output)
        # Si el anterior era HTML, forzar HTML
        if is_html and artifact_type != "html":
            artifact_type = "html"
            clean = output.strip()

        ext = "html" if artifact_type == "html" else "md"
        artifact_url = _save_artifact(agent, clean, ext)

        return {
            "agent":         agent,
            "artifact_url":  artifact_url,
            "artifact_type": artifact_type,
            "rag_used":      rag_chars > 0,
            "rag_chars":     rag_chars,
            "model":         model,
            "iteration":     True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
