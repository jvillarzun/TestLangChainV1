"""
tools/confluence_tools.py
──────────────────────────
Herramientas de Confluence para el ciclo ADLC.

El agente PRD publica automáticamente un documento Rationale en Confluence
al completar el PRDSPECS.md. El rationale explica el "por qué" de las
decisiones de producto en formato legible para stakeholders no técnicos.

Usa la API REST de Confluence Cloud v2:
  POST /wiki/api/v2/pages           → crear página
  PUT  /wiki/api/v2/pages/{id}      → actualizar página (re-run con feedback)

Requiere las variables de entorno:
  CONFLUENCE_URL          → ej: https://sapo-re-frito.atlassian.net
  CONFLUENCE_EMAIL        → mismo email que Jira
  CONFLUENCE_API_TOKEN    → mismo token que Jira
  CONFLUENCE_SPACE_KEY    → clave del Space, ej: MACH
"""

import re
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

from config.settings import (
    CONFLUENCE_URL,
    CONFLUENCE_EMAIL,
    CONFLUENCE_API_TOKEN,
    CONFLUENCE_SPACE_KEY,
)


def _auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)


def _headers() -> dict:
    return {"Content-Type": "application/json", "Accept": "application/json"}


def _api(path: str) -> str:
    return f"{CONFLUENCE_URL.rstrip('/')}/wiki/api/v2{path}"


# ── Rationale document ────────────────────────────────────────────────────────

def create_prd_rationale(
    challenge_name: str,
    challenge_description: str,
    prd_content: str,
    thread_id: str,
    jira_epic_key: str | None = None,
) -> str | None:
    """
    Crea (o actualiza) una página Confluence con el Rationale del PRD.

    El rationale extrae del PRDSPECS.md las decisiones clave y el "por qué",
    y las presenta en formato Confluence Storage Format (XHTML simplificado).

    Retorna la URL de la página creada, o None si falla.
    """
    title = f"[MACH Race] {challenge_name} — PRD Rationale"
    body = _build_rationale_body(
        challenge_name=challenge_name,
        challenge_description=challenge_description,
        prd_content=prd_content,
        thread_id=thread_id,
        jira_epic_key=jira_epic_key,
    )

    # Buscar si ya existe una página con ese título para actualizar
    existing_id = _find_page_by_title(title)
    if existing_id:
        return _update_page(existing_id, title, body)
    else:
        return _create_page(title, body)


def _create_page(title: str, body: str) -> str | None:
    payload = {
        "spaceId": _get_space_id(),
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
    }
    if not payload["spaceId"]:
        return None

    try:
        r = requests.post(
            _api("/pages"),
            json=payload,
            auth=_auth(),
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        page_id = data.get("id")
        url = f"{CONFLUENCE_URL}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"
        print(f"[Confluence] Página creada: {url}")
        return url
    except requests.RequestException as e:
        print(f"[Confluence] Error al crear página: {e}")
        return None
    except Exception as e:
        print(f"[Confluence] Error inesperado: {e}")
        return None


def _update_page(page_id: str, title: str, body: str) -> str | None:
    # Obtener versión actual para incrementarla
    try:
        r = requests.get(
            _api(f"/pages/{page_id}"),
            auth=_auth(),
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        current_version = r.json().get("version", {}).get("number", 1)
    except Exception:
        current_version = 1

    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
        "version": {"number": current_version + 1},
    }

    try:
        r = requests.put(
            _api(f"/pages/{page_id}"),
            json=payload,
            auth=_auth(),
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        url = f"{CONFLUENCE_URL}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"
        print(f"[Confluence] Página actualizada: {url}")
        return url
    except requests.RequestException as e:
        print(f"[Confluence] Error al actualizar página: {e}")
        return None
    except Exception as e:
        print(f"[Confluence] Error inesperado al actualizar: {e}")
        return None


def _find_page_by_title(title: str) -> str | None:
    """Busca una página por título en el space. Retorna el ID si existe."""
    try:
        r = requests.get(
            _api("/pages"),
            params={"spaceKey": CONFLUENCE_SPACE_KEY, "title": title, "limit": 1},
            auth=_auth(),
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0]["id"] if results else None
    except Exception:
        return None


def _get_space_id() -> str | None:
    """Obtiene el spaceId numérico a partir de la clave del Space."""
    try:
        r = requests.get(
            _api("/spaces"),
            params={"keys": CONFLUENCE_SPACE_KEY, "limit": 1},
            auth=_auth(),
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            print(f"[Confluence] Space '{CONFLUENCE_SPACE_KEY}' no encontrado")
            return None
        return results[0]["id"]
    except Exception as e:
        print(f"[Confluence] Error al obtener Space: {e}")
        return None


# ── Builder de contenido ──────────────────────────────────────────────────────

def _build_rationale_body(
    challenge_name: str,
    challenge_description: str,
    prd_content: str,
    thread_id: str,
    jira_epic_key: str | None,
) -> str:
    """
    Genera el cuerpo en Confluence Storage Format (XHTML simplificado).
    Extrae las secciones clave del PRDSPECS.md para construir el rationale.
    """
    resumen = _extract_section(prd_content, "Resumen ejecutivo")
    problema = _extract_section(prd_content, "Problema y contexto")
    solucion = _extract_section(prd_content, "Solución propuesta")
    metricas = _extract_section(prd_content, "Métricas de éxito")

    jira_ref = (
        f'<p>🎫 Jira Epic: <a href="{CONFLUENCE_URL.rstrip("/")}/browse/{jira_epic_key}">'
        f'{jira_epic_key}</a></p>'
        if jira_epic_key else ""
    )

    return f"""
<h1>Product Decision Rationale — {_esc(challenge_name)}</h1>

<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Documento generado automáticamente</ac:parameter>
  <ac:rich-text-body>
    <p>Generado por el agente PRD del ciclo ADLC · MACH Race 2026</p>
    <p>Thread ID: <code>{thread_id}</code> · {_now()}</p>
    {jira_ref}
  </ac:rich-text-body>
</ac:structured-macro>

<h2>¿Qué problema resolvemos?</h2>
<p><strong>Challenge:</strong> {_esc(challenge_description)}</p>
{_md_to_storage(problema)}

<h2>¿Por qué esta solución?</h2>
{_md_to_storage(solucion)}

<h2>Resumen ejecutivo</h2>
{_md_to_storage(resumen)}

<h2>¿Cómo medimos el éxito?</h2>
{_md_to_storage(metricas)}

<h2>Documento completo (PRDSPECS.md)</h2>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">markdown</ac:parameter>
  <ac:plain-text-body><![CDATA[{prd_content}]]></ac:plain-text-body>
</ac:structured-macro>
""".strip()


def _extract_section(content: str, section_name: str) -> str:
    """Extrae el contenido de una sección del markdown por su encabezado.
    
    Soporta encabezados numerados (## 2. Problema y contexto)
    y encabezados simples (## Problema y contexto).
    """
    # Patrón: ## (opcional: número + punto + espacio) nombre_sección
    pattern = rf"^(#+)\s*(?:\d+\.\s*)?{re.escape(section_name)}.*?$"
    lines = content.split("\n")
    start_idx = None
    heading_level = None

    for i, line in enumerate(lines):
        if re.match(pattern, line, re.IGNORECASE):
            start_idx = i + 1
            heading_level = len(re.match(r'^(#+)', line).group(1))
            break

    if start_idx is None:
        return ""

    # Recopilar líneas hasta el próximo heading del mismo nivel o superior
    result_lines = []
    for line in lines[start_idx:]:
        header_match = re.match(r'^(#+)\s', line)
        if header_match and len(header_match.group(1)) <= heading_level:
            break
        result_lines.append(line)

    return "\n".join(result_lines).strip()


def _md_to_storage(text: str) -> str:
    """Convierte markdown básico a Confluence Storage Format."""
    if not text:
        return "<p><em>Sin contenido.</em></p>"
    lines = []
    in_list = False
    for line in text.split("\n"):
        line = line.rstrip()
        is_list_item = line.startswith("- ") or line.startswith("* ") or re.match(r'^\d+\.\s', line)
        if is_list_item:
            if not in_list:
                lines.append("<ul>")
                in_list = True
            # strip list marker
            item_text = re.sub(r'^[-*]\s|^\d+\.\s', '', line)
            # handle bold **text**
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            lines.append(f"  <li>{item_text}</li>")
        else:
            if in_list:
                lines.append("</ul>")
                in_list = False
            if line.startswith("### "):
                lines.append(f"<h4>{_esc(line[4:])}</h4>")
            elif line.startswith("## "):
                lines.append(f"<h3>{_esc(line[3:])}</h3>")
            elif line.startswith("# "):
                lines.append(f"<h3>{_esc(line[2:])}</h3>")
            elif line == "":
                pass  # skip blank lines (no <br/> noise)
            else:
                # handle bold **text**
                formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', _esc(line))
                lines.append(f"<p>{formatted}</p>")
    if in_list:
        lines.append("</ul>")
    return "\n".join(lines)


def _esc(text: str) -> str:
    """Escapa caracteres especiales XML."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
