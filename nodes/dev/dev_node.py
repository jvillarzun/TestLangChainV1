import json
import re

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import create_branch_and_push, open_pull_request
from config.settings import MODEL_DEV, REPO_BE_NAME, REPO_FE_NAME


def _parse_generated_files(content: str) -> list[dict]:
    """
    Extrae el bloque JSON GENERATED_FILES del output del LLM.
    Retorna lista de dicts: [{"repo": ..., "path": ..., "content": ...}]
    """
    match = re.search(r"```json\s*(\{.*?\"files\".*?\})\s*```", content, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
        return data.get("files", [])
    except json.JSONDecodeError:
        return []


def _push_files_and_open_pr(
    repo_name: str,
    branch: str,
    files: list[dict],
    challenge_name: str,
    github_plan: str,
) -> str | None:
    """Sube los archivos a la rama y abre PR. Retorna URL del PR."""
    changes = [{"path": f["path"], "content": f["content"]} for f in files]
    commit_sha = create_branch_and_push(
        repo_name=repo_name,
        branch_name=branch,
        changes=changes,
        commit_message=f"feat({challenge_name}): ADLC auto-generated code",
    )
    if not commit_sha:
        print(f"[DEV-AGENT] No se pudo hacer push a {repo_name}")
        return None

    pr_body = (
        f"## ADLC Auto-generated PR\n\n"
        f"**Challenge:** {challenge_name}\n\n"
        f"### Engineering Plan\n```json\n{github_plan}\n```\n\n"
        f"### Archivos modificados\n"
        + "\n".join(f"- `{f['path']}`" for f in files)
    )
    return open_pull_request(
        repo_name=repo_name,
        branch_name=branch,
        title=f"feat({challenge_name}): ADLC implementation",
        body=pr_body,
    )


def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — genera código real y abre PRs en BE y FE repos."""
    print("\n💻 DEV-AGENT: Generando DEVSPECS.md + código para PRs...")

    feedback = _get_last_feedback(state, "dev")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    github_plan = state.get("github_plan") or ""

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
    )

    try:
        dev_content = llm_invoke(
            model=MODEL_DEV,
            system_prompt=system_prompt,
            user_message="Genera el DEVSPECS.md completo y el bloque GENERATED_FILES según las instrucciones.",
            stub_content="# DEVSPECS.md stub — TEST_MODE activo",
        )
    except Exception as e:
        print(f"[DEV-AGENT] Error LLM: {e}")
        notify_team(f"❌ DEV-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "dev", "error_message": str(e), "dev_content": None, "dev_pr_url": None, "dev_pr_urls": []}

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

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

    print(f"   ✅ DEVSPECS.md generado ({len(dev_content)} chars)")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")
    print(f"   🔗 PRs abiertos: {len(pr_urls)}")

    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_urls[0] if pr_urls else None,
        "dev_pr_urls":     pr_urls,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
    }

