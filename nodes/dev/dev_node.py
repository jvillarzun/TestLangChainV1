import json
import re

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from nodes.dev.dev_validator import validate_dev_output, parse_file_blocks
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import create_branch_and_push, open_pull_request, get_files_content, get_repo_context
from config.settings import MODEL_DEV, REPO_FE_NAME

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

def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — genera código real y abre PRs en BE y FE repos."""
    print("\n💻 DEV-AGENT: Generando DEVSPECS.md + código para PRs...")

    feedback = _get_last_feedback(state, "dev")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    github_plan = state.get("github_plan") or ""

    # Contexto real del repositorio — árbol completo + archivos clave
    print(f"   🗂️  [DEV] Leyendo contexto del repositorio {REPO_FE_NAME}...")
    _repo_ctx = get_repo_context(REPO_FE_NAME)
    _repo_tree = "\n".join(_repo_ctx.get("tree", [])) or "Repositorio vacío o no accesible."
    _repo_key_files = _repo_ctx.get("files", {})
    print(f"   🗂️  [DEV] Árbol: {len(_repo_ctx.get('tree', []))} archivos | Clave: {list(_repo_key_files.keys())}")

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
    if _rag:
        system_prompt += f"\n\n## Contexto de Knowledge Base (DEV):\n{_rag}"
        print(f"   📚 RAG: {len(_rag)} chars de contexto inyectados")

    # Templates completos — inyectar como base para UI/código
    try:
        from rag.template_matcher import get_template_context
        _tpl_query = f"{state['challenge_name']} {state['challenge_description']}"
        _tpl = get_template_context("dev", _tpl_query)
        if _tpl:
            system_prompt += (
                f"\n\n## 📐 Templates de referencia (USAR COMO BASE)\n"
                f"DEBES usarlos como base y adaptarlos.\n\n{_tpl}"
            )
            print(f"   📐 Templates: {len(_tpl)} chars inyectados como base")
    except Exception:
        pass

    try:
        dev_content, _usage = llm_invoke(
            model=MODEL_DEV,
            system_prompt=system_prompt,
            user_message="Genera el DEVSPECS.md completo y el bloque GENERATED_FILES según las instrucciones.",
            stub_content="# DEVSPECS.md stub — TEST_MODE activo",
        )
        _usage["agent"] = "dev"
    except Exception as e:
        print(f"[DEV-AGENT] Error LLM: {e}")
        notify_team(f"❌ DEV-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "dev", "error_message": str(e), "dev_content": None, "dev_pr_url": None, "dev_pr_urls": [], "token_usage": []}

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

    # ── Validar output del LLM ────────────────────────────────────────────────
    validation = validate_dev_output(dev_content)
    print(f"\n🔎 [DEV Validator]\n{validation.summary()}")

    if not validation.is_valid:
        print(f"⚠️  [DEV Validator] Output con errores — se continúa pero el HITL debería rechazar")
        notify_team(
            f"⚠️ DEV-AGENT generó código con {len(validation.errors)} error(es) de calidad en `{state['thread_id'][:8]}`:\n"
            + "\n".join(f"• {e}" for e in validation.errors[:5]),
            state["thread_id"],
        )

    # ── Extraer archivos generados y subir PRs ────────────────────────────────
    generated_files = _parse_generated_files(dev_content)
    branch = f"feat/adlc-{state['thread_id'][:8]}"
    pr_urls: list[str] = []

    if generated_files:
        for gf in generated_files:
            fpath = gf.get("path", "unknown")
            fcontent = gf.get("content", "")
            local_path = save_output(f"generated/{fpath}", fcontent)
            print(f"   💾 Guardado local: {local_path}")

        challenge_name = state["challenge_name"]
        print(f"   📦 Subiendo {len(generated_files)} archivos a {REPO_FE_NAME}...")
        pr = _push_files_and_open_pr(REPO_FE_NAME, branch, generated_files, challenge_name, github_plan)
        if pr:
            pr_urls.append(pr)
            print(f"   🔗 PR: {pr}")
    else:
        print("   ⚠️  GENERATED_FILES no encontrado — no se abrieron PRs")

    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
        parent_key=state.get("jira_epic_key"),
        pr_url=pr_urls[0] if pr_urls else None,
    )

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
    print(f"{'='*80}\n")

    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_urls[0] if pr_urls else None,
        "dev_pr_urls":     pr_urls,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
        "token_usage":     [_usage],
    }
