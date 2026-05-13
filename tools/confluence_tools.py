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


# ── TDD document (Arquitecto) ────────────────────────────────────────────────

def create_arch_tdd(
    challenge_name: str,
    challenge_description: str,
    arch_content: str,
    thread_id: str,
    jira_epic_key: str | None = None,
    confluence_prd_url: str | None = None,
) -> str | None:
    """
    Crea (o actualiza) una página Confluence con el Technical Design Document (TDD).

    Extrae del ARQSPECS.md las secciones técnicas y las presenta con macros
    nativas de Confluence: paneles de info/note, bloques de código Mermaid,
    tablas de API Contract y task list de Action Items.

    Retorna la URL de la página creada/actualizada, o None si falla.
    """
    title = f"[MACH Race] {challenge_name} — Architecture TDD"
    body = _build_tdd_body(
        challenge_name=challenge_name,
        challenge_description=challenge_description,
        arch_content=arch_content,
        thread_id=thread_id,
        jira_epic_key=jira_epic_key,
        confluence_prd_url=confluence_prd_url,
    )

    existing_id = _find_page_by_title(title)
    if existing_id:
        return _update_page(existing_id, title, body)
    else:
        return _create_page(title, body)


def _build_tdd_body(
    challenge_name: str,
    challenge_description: str,
    arch_content: str,
    thread_id: str,
    jira_epic_key: str | None,
    confluence_prd_url: str | None,
) -> str:
    """Genera el TDD en Confluence Storage Format con secciones ricas."""

    # ── Extraer secciones del ARQSPECS.md ────────────────────────────────────
    vision        = _extract_section(arch_content, "Visi") or _extract_section(arch_content, "Resumen")
    api_contract  = _extract_section(arch_content, "API Contract") or _extract_section(arch_content, "API") or _extract_section(arch_content, "Interfaces")
    modelo_datos  = _extract_section(arch_content, "Modelo de datos") or _extract_section(arch_content, "Persistencia") or _extract_section(arch_content, "Base de datos")
    adr           = _extract_section(arch_content, "ADR") or _extract_section(arch_content, "Decisiones")
    no_funcional  = _extract_section(arch_content, "Requisitos no funcionales") or _extract_section(arch_content, "No funcionales")
    stack         = _extract_section(arch_content, "Stack tecnol") or _extract_section(arch_content, "Stack")
    seguridad     = _extract_section(arch_content, "Seguridad")
    eng_plan      = _extract_section(arch_content, "Engineering Plan") or _extract_section(arch_content, "Tareas") or _extract_section(arch_content, "Action Items")

    # ── Extraer TODOS los bloques de código (``` ... ```) como diagramas ─────
    diagram_sections = []
    for match in re.finditer(r"(##\s*\d*\.?\s*Diagrama[^\n]*)\n", arch_content):
        heading = match.group(1).strip()
        section_content = _extract_section(arch_content, re.sub(r'^#+\s*\d*\.?\s*', '', heading))
        if section_content:
            diagram_sections.append((heading, section_content))

    # Fallback: buscar todos los code blocks directamente
    all_code_blocks = re.findall(r"```(\w*)\s*\n(.*?)```", arch_content, re.DOTALL)

    # ── Referencias ──────────────────────────────────────────────────────────
    prd_ref = ""
    if confluence_prd_url:
        prd_ref = f'<li>📄 PRD Rationale: <a href="{confluence_prd_url}">Ver documento</a></li>'
    jira_ref = ""
    if jira_epic_key:
        jira_ref = (
            f'<li>🎫 Jira Epic: <a href="{CONFLUENCE_URL.rstrip("/")}/browse/{jira_epic_key}">'
            f'{jira_epic_key}</a></li>'
        )

    # ── Diagramas C4/Arquitectura ────────────────────────────────────────────
    diagrams_html = ""
    if diagram_sections:
        for heading, content in diagram_sections:
            clean_heading = re.sub(r'^#+\s*', '', heading)
            # Extraer code blocks de dentro de la sección
            inner_blocks = re.findall(r"```(\w*)\s*\n(.*?)```", content, re.DOTALL)
            if inner_blocks:
                for lang, block in inner_blocks:
                    diagrams_html += f"""
<h3>{_esc(clean_heading)}</h3>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">{lang or 'text'}</ac:parameter>
  <ac:parameter ac:name="title">{_esc(clean_heading)}</ac:parameter>
  <ac:parameter ac:name="linenumbers">false</ac:parameter>
  <ac:plain-text-body><![CDATA[{block.strip()}]]></ac:plain-text-body>
</ac:structured-macro>
"""
            else:
                # La sección tiene texto sin code blocks, renderizar como code
                diagrams_html += f"""
<h3>{_esc(clean_heading)}</h3>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">text</ac:parameter>
  <ac:parameter ac:name="title">{_esc(clean_heading)}</ac:parameter>
  <ac:parameter ac:name="linenumbers">false</ac:parameter>
  <ac:plain-text-body><![CDATA[{content.strip()}]]></ac:plain-text-body>
</ac:structured-macro>
"""
    elif all_code_blocks:
        # No hay secciones de diagrama explícitas, buscar bloques de código sueltos
        # que no sean json (json es probablemente Engineering Plan)
        for i, (lang, block) in enumerate(all_code_blocks, 1):
            if lang == "json":
                continue
            diagrams_html += f"""
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">{lang or 'text'}</ac:parameter>
  <ac:parameter ac:name="title">Diagrama {i}</ac:parameter>
  <ac:parameter ac:name="linenumbers">false</ac:parameter>
  <ac:plain-text-body><![CDATA[{block.strip()}]]></ac:plain-text-body>
</ac:structured-macro>
"""

    diagrams_section = ""
    if diagrams_html:
        diagrams_section = f"<h2>Diagramas de Arquitectura</h2>\n{diagrams_html}"

    # ── API Contract como Code Snippet ───────────────────────────────────────
    api_html = ""
    if api_contract:
        api_html = f"""
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">yaml</ac:parameter>
  <ac:parameter ac:name="title">API Contract</ac:parameter>
  <ac:parameter ac:name="linenumbers">true</ac:parameter>
  <ac:plain-text-body><![CDATA[{api_contract}]]></ac:plain-text-body>
</ac:structured-macro>
"""
    else:
        api_html = "<p><em>Ver ARQSPECS.md para detalle completo.</em></p>"

    # ── Modelo de datos ──────────────────────────────────────────────────────
    datos_html = _md_to_storage(modelo_datos) if modelo_datos else "<p><em>Ver ARQSPECS.md para detalle completo.</em></p>"

    # ── ADRs como paneles expandibles ────────────────────────────────────────
    adr_html = ""
    if adr:
        # Buscar sub-secciones ADR-XXX
        adr_entries = re.split(r'(?=###\s+ADR-)', adr)
        if len(adr_entries) > 1:
            for entry in adr_entries:
                entry = entry.strip()
                if not entry:
                    continue
                title_match = re.match(r'###\s+(ADR-\d+[^\n]*)', entry)
                adr_title = title_match.group(1) if title_match else "ADR"
                adr_body = entry[title_match.end():].strip() if title_match else entry
                adr_html += f"""
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">{_esc(adr_title)}</ac:parameter>
  <ac:rich-text-body>
    {_md_to_storage(adr_body)}
  </ac:rich-text-body>
</ac:structured-macro>
"""
        else:
            adr_html = _md_to_storage(adr)
    else:
        adr_html = "<p><em>Ver ARQSPECS.md para detalle completo.</em></p>"

    # ── Requisitos no funcionales ────────────────────────────────────────────
    nfr_html = _md_to_storage(no_funcional) if no_funcional else ""
    nfr_section = f"<h2>Requisitos No Funcionales</h2>\n{nfr_html}" if nfr_html else ""

    # ── Stack tecnológico como tabla ─────────────────────────────────────────
    stack_html = ""
    if stack:
        table = _md_table_to_html(stack)
        if table:
            stack_html = table
        else:
            stack_html = _md_to_storage(stack)
    stack_section = f"<h2>Stack Tecnológico</h2>\n{stack_html}" if stack_html else ""

    # ── Seguridad (note panel) ───────────────────────────────────────────────
    security_section = ""
    if seguridad:
        security_section = f"""
<h2>Consideraciones de Seguridad</h2>
<ac:structured-macro ac:name="note">
  <ac:parameter ac:name="title">Puntos críticos de seguridad</ac:parameter>
  <ac:rich-text-body>
    {_md_to_storage(seguridad)}
  </ac:rich-text-body>
</ac:structured-macro>
"""

    # ── Engineering Plan como task list ───────────────────────────────────────
    eng_html = ""
    if eng_plan:
        # Si tiene un bloque JSON, mostrarlo como code
        json_match = re.search(r"```json\s*\n(.*?)```", eng_plan, re.DOTALL)
        if json_match:
            eng_html = f"""
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">json</ac:parameter>
  <ac:parameter ac:name="title">Engineering Plan</ac:parameter>
  <ac:parameter ac:name="linenumbers">true</ac:parameter>
  <ac:plain-text-body><![CDATA[{json_match.group(1).strip()}]]></ac:plain-text-body>
</ac:structured-macro>
"""
        else:
            eng_html = _md_to_storage(eng_plan)
    eng_section = f"<h2>Engineering Plan / Action Items</h2>\n{eng_html}" if eng_html else ""

    return f"""
<h1>Technical Design Document — {_esc(challenge_name)}</h1>

<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Documento generado automáticamente por el Agente Arquitecto</ac:parameter>
  <ac:rich-text-body>
    <p>Generado por el agente ARQ del ciclo ADLC · MACH Race 2026</p>
    <p>Thread ID: <code>{thread_id}</code> · {_now()}</p>
    <ul>{prd_ref}{jira_ref}</ul>
  </ac:rich-text-body>
</ac:structured-macro>

<h2>Visión Arquitectónica</h2>
{_md_to_storage(vision) if vision else f"<p>{_esc(challenge_description)}</p>"}

<h2>Referencias y Trazabilidad</h2>
<table>
  <tbody>
    <tr><th>Artefacto</th><th>Enlace</th></tr>
    {'<tr><td>PRD Rationale</td><td><a href="' + confluence_prd_url + '">Ver en Confluence</a></td></tr>' if confluence_prd_url else '<tr><td>PRD Rationale</td><td><em>No disponible</em></td></tr>'}
    {'<tr><td>Jira Epic</td><td><a href="' + CONFLUENCE_URL.rstrip("/") + "/browse/" + jira_epic_key + '">' + jira_epic_key + '</a></td></tr>' if jira_epic_key else ''}
  </tbody>
</table>

{diagrams_section}

<h2>Especificación de Interfaces (API Contract)</h2>
{api_html}

<h2>Diseño de Persistencia</h2>
{datos_html}

<h2>Decisiones de Diseño (ADR)</h2>
{adr_html}

{nfr_section}

{stack_section}

{security_section}

{eng_section}

<h2>Documento completo (ARQSPECS.md)</h2>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">markdown</ac:parameter>
  <ac:parameter ac:name="title">ARQSPECS.md</ac:parameter>
  <ac:plain-text-body><![CDATA[{arch_content}]]></ac:plain-text-body>
</ac:structured-macro>
""".strip()


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


def _md_table_to_html(text: str) -> str | None:
    """Convierte una tabla markdown a HTML. Retorna None si no encuentra tabla."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Buscar líneas que parezcan tabla (|col|col|)
    table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
    if len(table_lines) < 2:
        return None

    html = "<table>\n  <tbody>\n"
    for i, row in enumerate(table_lines):
        cells = [c.strip() for c in row.strip("|").split("|")]
        # Saltar la línea separadora (|---|---|)
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        tag = "th" if i == 0 else "td"
        html += "    <tr>" + "".join(f"<{tag}>{_esc(c)}</{tag}>" for c in cells) + "</tr>\n"
    html += "  </tbody>\n</table>"
    return html


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
