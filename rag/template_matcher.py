"""
rag/template_matcher.py
────────────────────────
Busca templates COMPLETOS relevantes al prompt del usuario.

A diferencia del RAG chunkeado (ChromaDB), este módulo:
  1. Indexa archivos completos de rag/templates/{agent}/
  2. Usa keyword matching para encontrar templates relevantes
  3. Retorna el contenido ÍNTEGRO del archivo — no fragmentos

Esto permite que el LLM use el template como BASE y lo adapte,
en vez de recibir chunks sueltos que no puede reconstruir.
"""

import re
from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(__file__).parent / "templates"
SUPPORTED_EXTENSIONS = {".md", ".txt", ".html", ".css", ".py", ".kt", ".swift", ".java", ".ts", ".js", ".tsx", ".jsx", ".vue"}

# Keywords por archivo → se matchean contra el prompt del usuario
# Si no hay entrada aquí, se usa el nombre del archivo como keyword
_KEYWORD_MAP: dict[str, list[str]] = {
    "credit-card.html": [
        "tarjeta", "crédito", "credito", "credit", "card",
        "landing", "onboarding", "producto financiero", "cupo",
        "cashback", "beneficios", "costos",
    ],
    "screen-template.md": [
        "screen", "pantalla", "kotlin", "compose", "jetpack",
        "android", "balance", "header", "navigation", "design system",
    ],
    "architecture-guidelines.md": [
        "arquitectura", "architecture", "mvvm", "clean", "repository",
        "kotlin", "android", "compose",
    ],
    "compose-patterns.md": [
        "compose", "composable", "jetpack", "state", "remember",
        "lazycolumn", "modifier",
    ],
    "react-query-patterns.md": [
        "react", "query", "tanstack", "fetch", "cache", "mutation",
    ],
    "folder-structure.md": [
        "react", "folder", "estructura", "carpetas", "proyecto",
    ],
    "android-cli-onboarding.md": [
        "android", "cli", "onboarding", "setup", "gradle",
    ],
}


def _normalize(text: str) -> str:
    """Normaliza texto para matching: lowercase, sin acentos comunes."""
    text = text.lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _score_file(filename: str, query_normalized: str) -> int:
    """Cuenta cuántos keywords del archivo aparecen en el query."""
    keywords = _KEYWORD_MAP.get(filename, [filename.replace("-", " ").replace("_", " ").split(".")[0]])
    return sum(1 for kw in keywords if kw in query_normalized)


def find_templates(agent: str, query: str, max_results: int = 2) -> list[dict]:
    """
    Busca templates completos relevantes al query.

    Returns:
        Lista de dicts: [{"filename": str, "content": str, "score": int}]
        Ordenados por score descendente. Solo incluye score > 0.
    """
    agent_dir = TEMPLATES_DIR / agent
    if not agent_dir.exists():
        return []

    query_norm = _normalize(query)
    results = []

    for fpath in agent_dir.rglob("*"):
        if not fpath.is_file() or fpath.suffix not in SUPPORTED_EXTENSIONS:
            continue

        score = _score_file(fpath.name, query_norm)
        if score > 0:
            try:
                content = fpath.read_text(encoding="utf-8")
                rel_path = str(fpath.relative_to(TEMPLATES_DIR))
                results.append({
                    "filename": rel_path,
                    "content": content,
                    "score": score,
                })
            except Exception:
                continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def get_template_context(agent: str, query: str, max_results: int = 2) -> Optional[str]:
    """
    Retorna templates completos formateados para inyectar en el prompt.
    Retorna None si no hay templates relevantes.
    """
    templates = find_templates(agent, query, max_results)
    if not templates:
        return None

    parts = []
    for t in templates:
        ext = Path(t["filename"]).suffix.lstrip(".")
        parts.append(
            f"### Template: {t['filename']} (relevancia: {t['score']})\n"
            f"```{ext}\n{t['content']}\n```"
        )

    return "\n\n".join(parts)
