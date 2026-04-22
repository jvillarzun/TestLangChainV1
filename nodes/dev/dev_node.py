import json
import re

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, get_phase_instructions
from nodes.dev.dev_validator import validate_dev_output, parse_file_blocks
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import create_branch_and_push, open_pull_request
from config.settings import MODEL_DEV, REPO_BE_NAME, REPO_FE_NAME


def _parse_generated_files(content: str) -> list[dict]:
    """
    Extrae archivos del output del LLM.
    Soporta dos formatos:
      1. Nuevo (preferido): bloques ## FILE: repo/path
      2. Legacy: bloque ```json { "files": [...] }```
    """
    print(f"\n🔍 [DEV Parser] Buscando archivos en respuesta LLM...")
    print(f"   Longitud del contenido: {len(content)} chars")

    # ── Formato nuevo: ## FILE: repo/path ────────────────────────────────────
    files = parse_file_blocks(content)
    if files:
        print(f"✅ [DEV Parser] Formato ## FILE: — {len(files)} archivo(s) encontrado(s)")
        for i, f in enumerate(files, 1):
            print(f"   {i}. Repo: {f['repo']}, Path: {f['path']}, Content: {len(f['content'])} chars")
        return files

    # ── Formato legacy: bloque JSON ───────────────────────────────────────────
    print(f"⚠️  [DEV Parser] Formato ## FILE: no encontrado — intentando JSON legacy...")
    match = re.search(r"```json\s*(\{.*?\"files\".*?\})\s*```", content, re.DOTALL)
    if not match:
        print(f"❌ [DEV Parser] NO se encontró ningún formato válido de archivos")
        return []

    json_str = match.group(1)
    try:
        data = json.loads(json_str)
        files = data.get("files", [])
        print(f"✅ [DEV Parser] JSON legacy parseado — {len(files)} archivo(s)")
        for i, f in enumerate(files, 1):
            print(f"   {i}. Repo: {f.get('repo','?')}, Path: {f.get('path','?')}, Content: {len(f.get('content',''))} chars")
        return files
    except json.JSONDecodeError as e:
        print(f"❌ [DEV Parser] ERROR parseando JSON: {e}")
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

    try:
        from rag.rag_helper import get_rag_context
        _rag_query = get_phase_instructions(state, "dev") or f"{state['challenge_name']} {state['challenge_description']}"
        _rag = get_rag_context("dev", _rag_query)
    except Exception:
        _rag = None

    system_prompt = load_prompt(
        "dev",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        arch_content=state.get("arch_content") or "",
        ux_content=state.get("ux_content") or "",
        github_plan=github_plan,
        repo_be_name=REPO_BE_NAME,
        repo_fe_name=REPO_FE_NAME,
        feedback=feedback or "Sin feedback previo.",
        orchestrator_instructions=get_phase_instructions(state, "dev") or "Sin instrucciones adicionales.",
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
                f"Los siguientes templates son archivos REALES del proyecto. "
                f"DEBES usarlos como base y adaptarlos. "
                f"Mantén la estructura, estilos y patrones del template.\n\n"
                f"{_tpl}"
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
        be_files = [f for f in generated_files if f.get("repo") == "backend"]
        fe_files = [f for f in generated_files if f.get("repo") == "frontend"]
        challenge_name = state["challenge_name"]

        if be_files:
            print(f"   📦 Subiendo {len(be_files)} archivos a {REPO_BE_NAME}...")
            pr = _push_files_and_open_pr(REPO_BE_NAME, branch, be_files, challenge_name, github_plan)
            if pr:
                pr_urls.append(pr)
                print(f"   🔗 PR backend: {pr}")

        if fe_files:
            print(f"   📦 Subiendo {len(fe_files)} archivos a {REPO_FE_NAME}...")
            pr = _push_files_and_open_pr(REPO_FE_NAME, branch, fe_files, challenge_name, github_plan)
            if pr:
                pr_urls.append(pr)
                print(f"   🔗 PR frontend: {pr}")
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
