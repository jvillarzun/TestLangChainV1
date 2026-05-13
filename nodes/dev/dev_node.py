import json
import re
import os

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, create_llm, get_phase_instructions
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import create_branch_and_push, open_pull_request, get_files_content, get_repo_context
from config.settings import MODEL_DEV, LLM_PROVIDER_DEV, LLM_MODEL_DEV, REPO_FE_NAME

# Flag para habilitar validación de build (requiere setup adicional)
ENABLE_BUILD_VALIDATION = os.environ.get("ENABLE_BUILD_VALIDATION", "false").lower() == "true"
MAX_HEALING_ATTEMPTS = 3
_HTML_SKELETON = """\
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><!-- TÍTULO --></title>
  <style>
    /* Estilos mínimos aquí */
  </style>
</head>
<body>
  <!-- Contenido principal aquí -->
  <script>
    // Lógica JavaScript aquí
  </script>
</body>
</html>
```"""

_REACT_SKELETON = """\
```tsx
import { useState } from 'react'

export default function App() {
  const [state, setState] = useState(null)

  return (
    <div>
      {/* Componentes aquí */}
    </div>
  )
}
```"""

_LAMBDA_SKELETON = """\
```python
import json

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        # Lógica aquí
        return {'statusCode': 200, 'body': json.dumps({'ok': True})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```"""

_ANDROID_SKELETON = """\
```kotlin
@Composable
fun MainScreen(viewModel: MainViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    // UI aquí
}
```"""

_KEYWORDS: list[tuple[list[str], str]] = [
    (["html", "página", "pagina", "web estática", "landing", "static"], _HTML_SKELETON),
    (["react", "next", "frontend", "tsx", "jsx"],                       _REACT_SKELETON),
    (["android", "kotlin", "compose", "mobile"],                        _ANDROID_SKELETON),
    (["lambda", "fastapi", "api rest", "backend", "endpoint"],          _LAMBDA_SKELETON),
]


def _pick_code_reference(
    challenge_description: str,
    instructions: str,
    repo_key_files: dict | None = None,
) -> str:
    """
    Para brownfield: usa archivos reales del repo como referencia.
    Para greenfield o repo vacío: usa skeleton según tipo de challenge.
    """
    if repo_key_files:
        lines = ["Archivos clave del repositorio actual (usa como referencia de estructura y estilo):\n"]
        for path, content in list(repo_key_files.items())[:4]:
            preview = content[:1200]
            lines.append(f"### `{path}`\n```\n{preview}\n{'...(truncado)' if len(content) > 1200 else ''}\n```\n")
        return "\n".join(lines)

    text = (challenge_description + " " + instructions).lower()
    for keywords, skeleton in _KEYWORDS:
        if any(k in text for k in keywords):
            return skeleton
    return "Sin referencia de código base — genera desde cero según el ENGINEERING_PLAN."


def _get_modify_files_context(github_plan: str, repo_name: str) -> str:
    """
    Lee TODOS los archivos del engineering plan que existen en el repo.
    No filtra por action — ARQ puede etiquetar mal CREATE/MODIFY.
    Retorna string formateado listo para inyectar en el prompt.
    """
    if not github_plan:
        return ""
    try:
        plan = json.loads(github_plan)
        steps = [s for s in plan.get("steps", []) if s.get("repo", "frontend") == "frontend"]
        all_paths = [s["file"] for s in steps if s.get("file")]
        action_map = {s["file"]: s.get("action", "CREATE").upper() for s in steps if s.get("file")}
    except (json.JSONDecodeError, KeyError):
        return ""

    if not all_paths:
        return ""

    print(f"   🔍 [DEV] Verificando {len(all_paths)} archivo(s) del plan en GitHub...")
    contents = get_files_content(repo_name, all_paths)

    if not contents:
        return ""

    lines = [
        "⚠️  ARCHIVOS QUE YA EXISTEN en el repositorio — conserva TODO el código original:\n",
        "**CRÍTICO**: Incluye el contenido completo de cada archivo en GENERATED_FILES.",
        "Solo agrega/modifica lo necesario. NO elimines funciones ni lógica existente.\n",
    ]
    for path, content in contents.items():
        plan_action = action_map.get(path, "?")
        lines.append(f"### `{path}` (plan dice: {plan_action} — REAL: EXISTE en repo)\n```\n{content}\n```\n")
        print(f"   ✔ Existente: {path} ({len(content)} chars) [plan={plan_action}]")

    new_paths = [p for p in all_paths if p not in contents]
    if new_paths:
        lines.append("### Archivos NUEVOS (no existen aún — crear desde cero):\n")
        for p in new_paths:
            lines.append(f"- `{p}`")

    return "\n".join(lines)


def _parse_generated_files(content: str) -> list[dict]:
    """
    Extrae archivos del output del LLM. Intenta dos formatos en orden:
      1. Delimitadores <<<FILE: path>>> ... <<<ENDFILE>>> (preferido — sin JSON escaping)
      2. Bloque JSON {"files": [...]} (fallback — por si el LLM usa el formato antiguo)
    """
    print(f"\n🔍 [DEV Parser] Buscando archivos en respuesta LLM ({len(content)} chars)...")

    # ── Formato 1: delimitadores ───────────────────────────────────────────────
    matches = re.findall(r"<<<FILE:\s*(.+?)>>>(.*?)<<<ENDFILE>>>", content, re.DOTALL)
    if matches:
        files = []
        for path, file_content in matches:
            path = path.strip()
            file_content = file_content.strip()
            files.append({"repo": "frontend", "path": path, "content": file_content})
            print(f"   ✔ [delimitador] {path} ({len(file_content)} chars)")
        print(f"✅ [DEV Parser] {len(files)} archivo(s) extraídos via <<<FILE>>>")
        return files

    # ── Formato 2: JSON fallback ───────────────────────────────────────────────
    print(f"⚠️  [DEV Parser] No se encontraron <<<FILE>>> — intentando fallback JSON...")
    match = re.search(r"```json\s*(\{.*?\"files\".*?\})\s*```", content, re.DOTALL)
    if not match:
        print(f"❌ [DEV Parser] Ningún formato reconocido — no se generarán PRs")
        return []

    try:
        data = json.loads(match.group(1))
        all_files = data.get("files", [])
        files = [f for f in all_files if f.get("repo", "frontend") != "backend"]
        skipped = len(all_files) - len(files)
        print(f"✅ [DEV Parser] JSON fallback: {len(files)} archivo(s) | ignorados backend: {skipped}")
        for f in files:
            print(f"   ✔ [json] {f.get('path', '?')} ({len(f.get('content', ''))} chars)")
        return files
    except json.JSONDecodeError as e:
        print(f"❌ [DEV Parser] JSON inválido: {e}")
        return []

def _parse_generated_files(content: str) -> list[dict]:
    """
    Extrae archivos usando el NUEVO FORMATO de bloques Markdown.
    Busca patrones: ## FILE: {path} seguido de ```{lang} ... ```
    Frontend-Only: todos los archivos se asumen del repo frontend.
    Retorna lista de dicts: [{"repo": ..., "path": ..., "content": ...}]
    """
    print(f"\n🔍 [DEV Parser] Parseando archivos con NUEVO formato Markdown...")
    print(f"   Longitud del contenido: {len(content)} chars")
    
    files = []
    # Patrón actualizado: ## FILE: src/app/page.tsx (sin prefijo de repo)
    # Captura: path completo + código
    pattern = r"##\s*FILE:\s*([^\n]+?)\s*\n```[a-z]*\s*\n(.*?)\n```"
    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        path = match.group(1).strip()
        file_content = match.group(2)
        
        # Frontend-Only Architecture: todo es frontend
        repo = "frontend"
        
        print(f"   ✅ Encontrado: {path} ({len(file_content)} chars)")
        
        files.append({
            "repo": repo,
            "path": path,
            "content": file_content,
        })
    
    if not files:
        print(f"⚠️  [DEV Parser] NO se encontraron archivos con formato Markdown")
        print(f"   Intentando fallback a formato JSON antiguo...")
        # Fallback al formato JSON antiguo por compatibilidad
        match = re.search(r"```json\s*(\{.*?\"files\".*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                files = data.get("files", [])
                print(f"   ✅ Fallback JSON exitoso: {len(files)} archivos")
            except json.JSONDecodeError as e:
                print(f"   ❌ Fallback JSON falló: {e}")
                return []
        else:
            print(f"   ❌ Tampoco se encontró formato JSON - retornando lista vacía")
            return []
    
    print(f"\n✅ [DEV Parser] Total archivos parseados: {len(files)}")
    for i, f in enumerate(files, 1):
        print(f"   {i}. {f['repo']}/{f['path']} ({len(f['content'])} chars)")
    
    return files


def _push_files_and_open_pr(
    repo_name: str,
    branch: str,
    files: list[dict],
    challenge_name: str,
    github_plan: str,
) -> str | None:
    """Sube los archivos a la rama y abre PR. Retorna URL del PR."""
    print(f"\n🚀 [DEV] _push_files_and_open_pr()")
    print(f"    Repo: {repo_name}")
    print(f"    Rama: {branch}")
    print(f"    Archivos: {len(files)}")
    print(f"    Challenge: {challenge_name}")
    
    if not files:
        print(f"⚠️  [DEV] Lista de archivos vacía - abortando")
        return None
    
    changes = [{"path": f.get("path", ""), "content": f.get("content", "")} for f in files]
    print(f"📦 [DEV] Preparados {len(changes)} cambios para commit")
    
    print(f"\n📤 [DEV] Llamando a create_branch_and_push()...")
    commit_sha = create_branch_and_push(
        repo_name=repo_name,
        branch_name=branch,
        changes=changes,
        commit_message=f"feat({challenge_name}): ADLC auto-generated code",
    )
    
    if not commit_sha:
        print(f"❌ [DEV] create_branch_and_push FALLÓ - no se pudo hacer push a {repo_name}")
        return None
    
    print(f"✅ [DEV] Push exitoso! Commit SHA: {commit_sha[:8]}...")

    pr_body = (
        f"## ADLC Auto-generated PR\n\n"
        f"**Challenge:** {challenge_name}\n\n"
        f"### Engineering Plan\n```json\n{github_plan}\n```\n\n"
        f"### Archivos modificados\n"
        + "\n".join(f"- `{f.get('path', 'unknown')}`" for f in files)
    )
    
    print(f"\n🔗 [DEV] Llamando a open_pull_request()...")
    pr_url = open_pull_request(
        repo_name=repo_name,
        branch_name=branch,
        title=f"feat({challenge_name}): ADLC implementation",
        body=pr_body,
    )
    
    if pr_url:
        print(f"✅ [DEV] PR creado exitosamente: {pr_url}")
    else:
        print(f"❌ [DEV] open_pull_request FALLÓ - no se pudo abrir PR")
    
    return pr_url


def _self_healing_loop(
    state: CycleState,
    initial_content: str,
    system_prompt: str,
) -> tuple[str, list[dict]]:
    """
    Bucle de auto-sanación: valida build y reintenta con feedback si falla.
    También detecta cuando el LLM ignora el formato de salida.
    
    Returns:
        (final_content: str, generated_files: list[dict])
    """
    if not ENABLE_BUILD_VALIDATION:
        print("\n⚠️  [Self-Healing] Validación de build deshabilitada (ENABLE_BUILD_VALIDATION=false)")
        return initial_content, _parse_generated_files(initial_content)
    
    print(f"\n🔄 [Self-Healing] Iniciando bucle de auto-sanación (máx {MAX_HEALING_ATTEMPTS} intentos)")
    
    from nodes.dev.build_validator import setup_repo, validate_frontend_build
    
    branch = f"feat/adlc-{state['thread_id'][:8]}"
    current_content = initial_content
    
    for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):
        print(f"\n🔄 [Intento {attempt}/{MAX_HEALING_ATTEMPTS}]")
        
        # Parsear archivos del contenido actual
        generated_files = _parse_generated_files(current_content)
        
        # ── Auto-Sanación del Parser (Formato Incorrecto) ────────────────────
        if not generated_files and len(current_content) > 100:
            print("\n⚠️  [Self-Healing] Parser no encontró archivos pero hay contenido")
            print("   🔄 El LLM probablemente ignoró el formato - forzando reintento...")
            
            if attempt < MAX_HEALING_ATTEMPTS:
                error_feedback = """## 🚨 ERROR CRÍTICO DE FORMATO

**Tu respuesta anterior NO SIGUIÓ el formato requerido.**

El parser NO pudo extraer ningún archivo de tu output. Esto significa que:
- NO usaste el formato de bloques Markdown especificado
- O envolviste el código en formato incorrecto
- O agregaste texto extra fuera de los bloques

**FORMATO OBLIGATORIO (cada archivo):**
```
## FILE: repo/ruta/archivo.ext
```extension
código aquí
```
```

**EJEMPLO CORRECTO:**
```
## FILE: backend/src/api.js
```javascript
const express = require('express');
module.exports = express.Router();
```
```

**REGLAS CRÍTICAS:**
1. Header exacto: `## FILE: repo/path`
2. Bloque de código con extensión correcta
3. Código completo dentro del bloque
4. NO agregues explicaciones fuera de los bloques
5. NO uses formato JSON

**AHORA GENERA NUEVAMENTE TODOS LOS ARCHIVOS USANDO EL FORMATO CORRECTO.**
"""
                healing_prompt = system_prompt + "\n\n" + error_feedback
                
                try:
                    print(f"   🔄 Reintentando con instrucciones de formato...")
                    llm = create_llm(MODEL_DEV)
                    from langchain_core.messages import SystemMessage, HumanMessage
                    response = llm.invoke([
                        SystemMessage(content=healing_prompt),
                        HumanMessage(content="Genera TODOS los archivos usando el formato Markdown especificado (## FILE: repo/path)."),
                    ])
                    current_content = response.content
                    save_output(f"DEVSPECS_format_healing_{attempt}.md", current_content)
                    print(f"   💾 Guardado intento de corrección de formato en outputs/")
                    continue  # Volver al inicio del loop para re-parsear
                except Exception as e:
                    print(f"   ❌ Error invocando LLM para corrección de formato: {e}")
                    return current_content, []
            else:
                print(f"\n⚠️  [Self-Healing] Máximo de intentos - parser sigue sin encontrar archivos")
                return current_content, []
        
        if not generated_files:
            print("   ⚠️  No se encontraron archivos generados - abortando auto-sanación")
            return current_content, generated_files
        
        # Frontend-Only: Solo procesar archivos del frontend
        fe_files = [f for f in generated_files if (
            f.get("repo") == "frontend" or 
            f.get("repo") == "fe" or 
            REPO_FE_NAME in f.get("repo", "")
        )]
        
        # ── Validar Frontend ─────────────────────────────────────────────
        fe_valid = True
        fe_error = ""
        if fe_files:
            print(f"\n🔨 [Validando Frontend] {len(fe_files)} archivos...")
            fe_repo_path = setup_repo(REPO_FE_NAME, branch, fe_files)
            if fe_repo_path:
                fe_valid, fe_error = validate_frontend_build(fe_repo_path)
            else:
                print("   ⚠️  No se pudo preparar repo frontend - saltando validación")
        
        # ── Resultado ────────────────────────────────────────────────────
        if fe_valid:
            print(f"\n✅ [Self-Healing] Build validado exitosamente en intento {attempt}!")
            return current_content, generated_files
        
        # ── Si falló, reintentar con feedback ────────────────────────────
        if attempt < MAX_HEALING_ATTEMPTS:
            print(f"\n❌ [Self-Healing] Build falló - reintentando con feedback del error...")
            
            # Construir mensaje de error
            error_feedback = "## 🚨 ERRORES DE COMPILACIÓN\n\n"
            error_feedback += "Tu código generó los siguientes errores al compilar:\n\n"
            error_feedback += f"### Frontend Error:\n```\n{fe_error[:1000]}\n```\n\n"
            
            error_feedback += "\n**INSTRUCCIONES:**\n"
            error_feedback += "1. Analiza el error cuidadosamente\n"
            error_feedback += "2. Identifica la causa raíz (syntax error, import faltante, tipo incorrecto, etc.)\n"
            error_feedback += "3. Corrige TODOS los archivos afectados\n"
            error_feedback += "4. Devuelve el código COMPLETO corregido\n"
            error_feedback += "5. NO agregues comentarios tipo 'aquí va el código' - ESCRIBE el código completo\n"
            
            # Reinvocar LLM con el error
            healing_prompt = system_prompt + "\n\n" + error_feedback
            
            try:
                print(f"   🔄 Invocando LLM para auto-sanación...")
                llm = create_llm(MODEL_DEV)
                from langchain_core.messages import SystemMessage, HumanMessage
                response = llm.invoke([
                    SystemMessage(content=healing_prompt),
                    HumanMessage(content="Corrige los errores de compilación y genera nuevamente TODOS los archivos completos."),
                ])
                current_content = response.content
                save_output(f"DEVSPECS_healing_attempt_{attempt}.md", current_content)
                print(f"   💾 Guardado intento {attempt} en outputs/")
            except Exception as e:
                print(f"   ❌ Error invocando LLM: {e}")
                return current_content, generated_files
        else:
            print(f"\n⚠️  [Self-Healing] Máximo de intentos alcanzado - usando última versión")
            print(f"   ⚠️  El código puede tener errores de compilación")
            return current_content, generated_files
    
    return current_content, generated_files


def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — genera código real y abre PRs en BE y FE repos."""
    print("\n💻 DEV-AGENT: Generando DEVSPECS.md + código para PRs...")
    
    # Mostrar configuración de LLM
    print("\n" + "="*80)
    print(f"🤖 CONFIGURACIÓN LLM DEV")
    print(f"   Proveedor: {LLM_PROVIDER_DEV}")
    print(f"   Modelo: {LLM_MODEL_DEV}")
    print("="*80 + "\n")

    feedback = _get_last_feedback(state, "dev")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    github_plan = state.get("github_plan") or ""

    # ── Leer contexto del repo Frontend (FRONTEND-ONLY) ──────────────────────
    print(f"   🗂️  [DEV] Leyendo contexto del repositorio {REPO_FE_NAME}...")
    try:
        _repo_ctx = get_repo_context(REPO_FE_NAME)
        _repo_tree = "\n".join(_repo_ctx.get("tree", [])) or "Repositorio vacío o no accesible."
        _repo_key_files = _repo_ctx.get("files", {})
        print(f"   🗂️  [DEV] Árbol: {len(_repo_ctx.get('tree', []))} archivos | Clave: {list(_repo_key_files.keys())}")
        fe_context = "Árbol: " + str(len(_repo_ctx.get('tree', []))) + " archivos\nArchivos clave:\n"
        for path, content in _repo_key_files.items():
            fe_context += "\n--- " + path + " ---\n" + content[:2000] + "...\n"
    except Exception as e:
        print(f"   ⚠️  No se pudo leer repo (GitHub no disponible): {e}")
        _repo_tree = "No disponible - GitHub offline"
        _repo_key_files = {}
        fe_context = "No disponible - GitHub offline"

    try:
        from rag.rag_helper import get_rag_context
        _rag_query = get_phase_instructions(state, "dev") or f"{state['challenge_name']} {state['challenge_description']}"
        _rag = get_rag_context("dev", _rag_query)
    except Exception:
        _rag = None

    _instructions = get_phase_instructions(state, "dev") or ""
    _code_ref     = _pick_code_reference(state["challenge_description"], _instructions, _repo_key_files or None)
    _modify_ctx   = _get_modify_files_context(github_plan, REPO_FE_NAME)

    system_prompt = load_prompt(
        "dev",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        arch_content=state.get("arch_content") or "",
        ux_content=state.get("ux_content") or "",
        github_plan=github_plan,
        repo_fe_name=REPO_FE_NAME,
        repo_tree=_repo_tree,
        modify_files_context=_modify_ctx or "Sin archivos existentes a modificar.",
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=_instructions or "Sin instrucciones adicionales.",
        code_reference=_code_ref,
    )
    
    # Inyectar contexto de código actual para evitar sobreescritura
    system_prompt += "\n\n## 📖 Código Actual del Repositorio Frontend (para MODIFY)\n\n"
    system_prompt += "### Frontend — " + REPO_FE_NAME + "\n" + fe_context + "\n\n"
    system_prompt += "**IMPORTANTE**: Cuando modifiques un archivo existente, DEBES incluir TODO el código actual en tu respuesta, fusionando tus cambios con el contenido original mostrado arriba.\n\n"
    
    if _rag:
        system_prompt += "\n\n## Contexto de Knowledge Base (DEV):\n" + _rag
        print(f"   📚 RAG: {len(_rag)} chars de contexto inyectados")
    
    print(f"   📦 Contexto total del prompt: {len(system_prompt)} chars")

    try:
        # Usar proveedor configurado o fallback a Gemini con MODEL_DEV
        provider = LLM_PROVIDER_DEV
        model = LLM_MODEL_DEV if LLM_PROVIDER_DEV in ["gemini", "openai"] else MODEL_DEV
        print(f"   🤖 LLM: {provider} | Modelo: {model}")

        dev_content, _usage = llm_invoke(
            model=model,
            system_prompt=system_prompt,
            user_message="Genera el DEVSPECS.md completo y el código de TODOS los archivos usando el formato de bloques Markdown especificado (## FILE: repo/path). Recuerda: CERO placeholders, CERO comentarios vacíos, código COMPLETO y funcional.",
            stub_content="# DEVSPECS.md stub — TEST_MODE activo",
            provider=provider,
        )
        _usage["agent"] = "dev"
    except Exception as e:
        print(f"[DEV-AGENT] Error LLM: {e}")
        notify_team(f"❌ DEV-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "dev", "error_message": str(e), "dev_content": None, "dev_pr_url": None, "dev_pr_urls": [], "token_usage": []}

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

    # ── Auto-sanación con validación de build ─────────────────────────────────
    dev_content, generated_files = _self_healing_loop(state, dev_content, system_prompt)
    
    # Actualizar archivo con versión final
    if dev_content != save_output("DEVSPECS.md", dev_content):
        save_output("DEVSPECS.md", dev_content)

    # ── Extraer archivos generados y subir PRs ────────────────────────────────
    branch = f"feat/adlc-{state['thread_id'][:8]}"
    pr_urls: list[str] = []
    preview_url: str | None = None
    
    # Frontend-Only: Solo procesar archivos del frontend
    fe_files: list[dict] = []

    if generated_files:
        for gf in generated_files:
            fpath = gf.get("path", "unknown")
            fcontent = gf.get("content", "")
            save_output(f"generated/{fpath}", fcontent)

        # Filtro robusto: acepta "frontend", "fe", o el nombre completo del repo
        fe_files = [f for f in generated_files if (
            f.get("repo") == "frontend" or
            f.get("repo") == "fe" or
            REPO_FE_NAME in f.get("repo", "")
        )]

        challenge_name = state["challenge_name"]
        print(f"\n📦 [Frontend-Only Architecture]")
        print(f"   Frontend: {len(fe_files)} archivos")

        if fe_files:
            print(f"\n📤 [Subiendo Frontend] {len(fe_files)} archivos a {REPO_FE_NAME}...")
            pr = _push_files_and_open_pr(REPO_FE_NAME, branch, fe_files, challenge_name, github_plan)
            if pr:
                pr_urls.append(pr)
                print(f"   ✅ PR frontend creado: {pr}")
            else:
                print(f"   ⚠️  No se pudo crear PR frontend")
        else:
            print(f"   ⚠️  No se encontraron archivos de frontend - verificar formato del LLM")
    else:
        print("\n⚠️  [Sin archivos generados] No se abrieron PRs")

    # ── Iniciar servidor de preview si está habilitado ────────────────────────
    if ENABLE_BUILD_VALIDATION and fe_files:
        print(f"\n🚀 [Preview Server] Intentando iniciar servidor de preview...")
        from nodes.dev.build_validator import setup_repo, start_preview_server
        
        fe_repo_path = setup_repo(REPO_FE_NAME, branch, fe_files)
        if fe_repo_path:
            success, url = start_preview_server(fe_repo_path, port=3001)
            if success:
                preview_url = url
                print(f"   ✅ Preview disponible: {preview_url}")
            else:
                print(f"   ⚠️  No se pudo iniciar servidor de preview")
        else:
            print(f"   ⚠️  No se pudo preparar repo para preview")
    elif fe_files:
        print(f"\n⚠️  [Preview Server] Validación de build deshabilitada - no se inicia preview")
    
    # ── Crear Jira Task ──────────────────────────────────────────────────────
    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
    )

    notify_team(f"✅ DEV-AGENT completado para `{state['challenge_name']}`.\n\nPRs: {', '.join(pr_urls) if pr_urls else 'Ninguno'}", state["thread_id"])

    print(f"\n{'='*80}")
    print(f"📋 [DEV-AGENT] RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"   ✅ DEVSPECS.md generado ({len(dev_content)} chars) | tokens: {_usage['total_tokens']} | ${_usage['cost_usd']:.4f}")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")
    print(f"   🔗 PRs abiertos: {len(pr_urls)}")
    if pr_urls:
        for i, url in enumerate(pr_urls, 1):
            print(f"      {i}. {url}")
    else:
        print(f"   ⚠️  NO SE ABRIERON PRs")
    if preview_url:
        print(f"   👁️  Preview disponible: {preview_url}")
    print(f"{'='*80}\n")

    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_urls[0] if pr_urls else None,
        "dev_pr_urls":     pr_urls,
        "preview_url":     preview_url,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
        "token_usage":     [_usage],
    }

