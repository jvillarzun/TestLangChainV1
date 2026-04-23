"""
tools/github_tools.py
─────────────────────
Herramientas de GitHub para el ciclo ADLC.

Responsabilidades:
  1. get_repo_context()       — árbol de archivos + contenido de archivos clave
  2. create_branch_and_push() — crear rama y hacer commit de cambios
  3. open_pull_request()      — abrir PR hacia 'main' y devolver URL

Usa PyGithub. Requiere en .env:
  GITHUB_TOKEN, GITHUB_USERNAME,
  REPO_FE_NAME (mach-frontend-test-hackathon)
"""

from __future__ import annotations

import os
from typing import Any

from github import Github, GithubException, UnknownObjectException
from github.Repository import Repository

from config.settings import (
    GITHUB_TOKEN,
    GITHUB_USERNAME,
    REPO_FE_NAME,
)

# ── Singleton cliente ─────────────────────────────────────────────────────────
print(f"🔑 [GitHub Init] Inicializando cliente GitHub...")
print(f"🔑 [GitHub Init] Token presente: {'✓' if GITHUB_TOKEN else '✗ FALTA'}")
print(f"🔑 [GitHub Init] Username: {GITHUB_USERNAME or '✗ FALTA'}")
print(f"🔑 [GitHub Init] Repo FE: {REPO_FE_NAME}")

_gh = None
_github_available = False

try:
    _gh = Github(GITHUB_TOKEN)
    # Validar credenciales
    user = _gh.get_user()
    _github_available = True
    print(f"✅ [GitHub Init] Autenticado como: {user.login}")
except Exception as e:
    print(f"⚠️  [GitHub Init] WARNING: No se pudo autenticar con GitHub: {e}")
    print(f"⚠️  [GitHub Init] Las funciones de GitHub NO estarán disponibles")
    print(f"⚠️  [GitHub Init] El ciclo ADLC continuará pero sin crear PRs en la fase DEV")
    _gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None  # Cliente sin validar

_COMPONENT_DIRS = {"components", "component", "ui", "atoms", "molecules", "organisms", "widgets", "screens", "views", "layouts"}
_LIB_DIRS       = {"lib", "utils", "helpers", "services", "store", "context", "hooks", "api"}
_CODE_EXTS      = {".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte", ".py"}

_ROOT_CONFIGS = [
    "package.json", "pyproject.toml", "tsconfig.json",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.ts", "vite.config.js", "tailwind.config.ts", "tailwind.config.js",
]
_ENTRY_POINTS = [
    "src/app/page.tsx", "app/page.tsx",
    "src/app/layout.tsx", "app/layout.tsx",
    "src/pages/index.tsx", "pages/index.tsx",
    "src/main.tsx", "src/App.tsx",
    "src/lib/api.ts", "src/utils/api.ts",
]


def _detect_key_files(tree: list[str]) -> list[str]:
    """
    Detecta archivos relevantes del repo a partir del árbol ya obtenido.
    Prioriza: configs raíz → entry points → componentes UI → lib/utils.
    Cap de 35 archivos para no exceder ventana de contexto.
    """
    tree_set = set(tree)
    selected: list[str] = []

    for name in _ROOT_CONFIGS:
        if name in tree_set:
            selected.append(name)

    for path in _ENTRY_POINTS:
        if path in tree_set and path not in selected:
            selected.append(path)

    component_files = [
        f for f in tree
        if any(seg in _COMPONENT_DIRS for seg in f.split("/"))
        and any(f.endswith(ext) for ext in _CODE_EXTS)
        and f not in selected
    ]
    selected.extend(component_files[:20])

    lib_files = [
        f for f in tree
        if any(seg in _LIB_DIRS for seg in f.split("/"))
        and any(f.endswith(ext) for ext in _CODE_EXTS)
        and f not in selected
    ]
    selected.extend(lib_files[:10])

    return selected[:35]


def _get_repo(repo_name: str) -> Repository:
    """Devuelve el objeto Repository. repo_name puede ser 'owner/repo' o solo 'repo'."""
    if not _gh:
        raise RuntimeError("Cliente GitHub no inicializado - verificar GITHUB_TOKEN")
    if not _github_available:
        raise RuntimeError("GitHub no disponible - credenciales inválidas")
    full_name = repo_name if "/" in repo_name else f"{GITHUB_USERNAME}/{repo_name}"
    return _gh.get_repo(full_name)


# ── get_files_content ────────────────────────────────────────────────────────

def get_files_content(repo_name: str, paths: list[str]) -> dict[str, str]:
    """
    Lee el contenido actual de archivos específicos desde default_branch.
    Retorna {path: contenido} — omite archivos que no existen.
    """
    if not paths:
        return {}
    try:
        repo = _get_repo(repo_name)
        default_branch = repo.default_branch
        result: dict[str, str] = {}
        for path in paths:
            try:
                cf = repo.get_contents(path, ref=default_branch)
                if not isinstance(cf, list):
                    result[path] = cf.decoded_content.decode("utf-8")
            except UnknownObjectException:
                pass
            except Exception as exc:
                print(f"[GitHub] No se pudo leer {path}: {exc}")
        return result
    except Exception as exc:
        print(f"[GitHub] Error en get_files_content({repo_name}): {exc}")
        return {}


# ── get_repo_context ──────────────────────────────────────────────────────────

def get_repo_context(repo_name: str) -> dict[str, Any]:
    """
    Devuelve:
      {
        "tree": ["path/to/file", ...],          # todos los archivos del repo
        "files": {"path": "contenido", ...},    # archivos clave
        "default_branch": "main",
      }

    Errores no fatales: loggea y continúa.
    """
    try:
        repo = _get_repo(repo_name)
        default_branch = repo.default_branch

        # Árbol de archivos (recursivo, solo blobs)
        git_tree = repo.get_git_tree(default_branch, recursive=True)
        file_tree = [
            item.path
            for item in git_tree.tree
            if item.type == "blob"
        ]

        # Detectar archivos clave dinámicamente según estructura real del repo
        key_paths = _detect_key_files(file_tree)
        print(f"[GitHub] Archivos clave detectados: {len(key_paths)}")

        key_contents: dict[str, str] = {}
        for path in key_paths:
            try:
                content_file = repo.get_contents(path, ref=default_branch)
                if not isinstance(content_file, list):
                    key_contents[path] = content_file.decoded_content.decode("utf-8")
            except UnknownObjectException:
                pass
            except Exception as exc:
                print(f"[GitHub] No se pudo leer {path}: {exc}")

        return {
            "tree": file_tree,
            "files": key_contents,
            "default_branch": default_branch,
        }

    except Exception as exc:
        print(f"[GitHub] Error en get_repo_context({repo_name}): {exc}")
        return {"tree": [], "files": {}, "default_branch": "main"}


# ── create_branch_and_push ────────────────────────────────────────────────────

def create_branch_and_push(
    repo_name: str,
    branch_name: str,
    changes: list[dict[str, str]],
    commit_message: str = "chore: ADLC auto-commit",
) -> str | None:
    """
    Crea una rama nueva desde 'default_branch' y hace commit de los cambios.

    Args:
        repo_name:      Nombre del repo (o 'owner/repo').
        branch_name:    Nombre de la rama a crear.
        changes:        Lista de dicts [{"path": "src/app.js", "content": "..."}].
        commit_message: Mensaje del commit.

    Returns:
        SHA del commit creado, o None si hubo error.
    """
    print(f"\n🛠️  [GitHub] create_branch_and_push()")
    print(f"    Repo: {repo_name}")
    print(f"    Rama: {branch_name}")
    print(f"    Cambios: {len(changes)} archivo(s)")
    for i, ch in enumerate(changes, 1):
        print(f"      {i}. {ch.get('path', 'SIN PATH')} ({len(ch.get('content', ''))} chars)")
    
    try:
        print(f"🔍 [GitHub] Obteniendo repositorio: {repo_name}...")
        repo = _get_repo(repo_name)
        print(f"✅ [GitHub] Repo obtenido: {repo.full_name}")
        
        default_branch = repo.default_branch
        print(f"🔍 [GitHub] Rama base: {default_branch}")
        
        base_sha = repo.get_branch(default_branch).commit.sha
        print(f"✅ [GitHub] Base SHA: {base_sha[:8]}...")

        # Crear rama (si ya existe, reutilizarla)
        print(f"🔨 [GitHub] Intentando crear rama: {branch_name}...")
        try:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
            print(f"✅ [GitHub] Rama '{branch_name}' creada exitosamente en {repo_name}")
        except GithubException as exc:
            if exc.status == 422:  # rama ya existe
                print(f"⚠️  [GitHub] Rama '{branch_name}' ya existe — reutilizando")
            else:
                print(f"❌ [GitHub] ERROR al crear rama: Status {exc.status}, Msg: {exc.data}")
                raise

        # Hacer commit de cada archivo
        print(f"📝 [GitHub] Iniciando commits de {len(changes)} archivo(s)...")
        commit_sha: str | None = None
        for idx, change in enumerate(changes, 1):
            path: str = change.get("path", "")
            content: str = change.get("content", "")

            if not path:
                print(f"❌ [GitHub] Archivo {idx}/{len(changes)}: SIN PATH - saltando")
                continue

            print(f"📝 [GitHub] Archivo {idx}/{len(changes)}: {path}")
            try:
                print(f"   🔍 Verificando si existe en rama {branch_name}...")
                existing = repo.get_contents(path, ref=branch_name)
                # Archivo existe → actualizar
                if isinstance(existing, list):
                    existing = existing[0]
                print(f"   ♻️  Actualizando archivo existente...")
                result = repo.update_file(
                    path=path,
                    message=commit_message,
                    content=content,
                    sha=existing.sha,
                    branch=branch_name,
                )
                print(f"   ✅ Actualizado exitosamente")
            except UnknownObjectException:
                # Archivo no existe → crear
                print(f"   ➕ Creando nuevo archivo...")
                result = repo.create_file(
                    path=path,
                    message=commit_message,
                    content=content,
                    branch=branch_name,
                )
                print(f"   ✅ Creado exitosamente")
            except Exception as file_exc:
                print(f"   ❌ ERROR al procesar {path}: {file_exc}")
                raise

            commit_sha = result["commit"].sha
            print(f"   📌 Commit SHA: {commit_sha[:8]}...")

        print(f"✅ [GitHub] Todos los commits completados. SHA final: {commit_sha[:8] if commit_sha else 'NONE'}...")
        return commit_sha

    except Exception as exc:
        print(f"❌ [GitHub] ERROR CRÍTICO en create_branch_and_push({repo_name}): {type(exc).__name__}: {exc}")
        import traceback
        print(f"❌ [GitHub] Stack trace:\n{traceback.format_exc()}")
        return None


# ── open_pull_request ─────────────────────────────────────────────────────────

def open_pull_request(
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    base: str | None = None,
) -> str | None:
    """
    Abre un Pull Request desde branch_name hacia base (default: default_branch).

    Returns:
        URL del PR (html_url), o None si hubo error.
    """
    print(f"\n🔗 [GitHub] open_pull_request()")
    print(f"    Repo: {repo_name}")
    print(f"    Rama: {branch_name}")
    print(f"    Título: {title}")
    
    try:
        print(f"🔍 [GitHub] Obteniendo repositorio...")
        repo = _get_repo(repo_name)
        target_base = base or repo.default_branch
        print(f"✅ [GitHub] Target base: {target_base}")

        # Verificar si ya existe un PR abierto para esta rama
        print(f"🔍 [GitHub] Verificando PRs existentes...")
        head_ref = f"{GITHUB_USERNAME}:{branch_name}"
        print(f"    Head ref: {head_ref}")
        open_prs = repo.get_pulls(state="open", head=head_ref, base=target_base)
        for pr in open_prs:
            print(f"⚠️  [GitHub] PR ya existe: {pr.html_url}")
            return pr.html_url

        print(f"🔨 [GitHub] Creando nuevo Pull Request...")
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=target_base,
        )
        print(f"✅ [GitHub] PR CREADO EXITOSAMENTE!")
        print(f"🔗 [GitHub] URL: {pr.html_url}")
        print(f"📌 [GitHub] Número: #{pr.number}")
        return pr.html_url

    except Exception as exc:
        print(f"❌ [GitHub] ERROR CRÍTICO en open_pull_request({repo_name}): {type(exc).__name__}: {exc}")
        import traceback
        print(f"❌ [GitHub] Stack trace:\n{traceback.format_exc()}")
        return None


# ── get_pr_ci_status ──────────────────────────────────────────────────────────

def get_pr_ci_status(repo_name: str, pr_url: str) -> dict[str, str]:
    """
    Consulta el estado del CI (GitHub Actions check runs) para un PR.

    Returns:
        {
            "status":      "success" | "failure" | "pending" | "no_ci" | "error",
            "summary":     texto listo para inyectar en el prompt QA,
            "details_url": url del PR,
        }
    """
    import re as _re

    m = _re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return {"status": "error", "summary": "URL de PR inválida — no se pudo obtener CI status", "details_url": pr_url}

    pr_number = int(m.group(1))
    print(f"   🔍 [GitHub CI] Consultando CI para PR #{pr_number} en {repo_name}...")

    try:
        repo = _get_repo(repo_name)
        pr   = repo.get_pull(pr_number)
        head_sha = pr.head.sha
        print(f"   🔍 [GitHub CI] Head SHA: {head_sha[:8]}...")

        # Preferir check runs (GitHub Actions)
        try:
            commit     = repo.get_commit(head_sha)
            check_runs = list(commit.get_check_runs())
        except Exception as e:
            print(f"   ⚠️  [GitHub CI] check_runs no disponible: {e} — usando combined status")
            check_runs = []

        if check_runs:
            pending    = [r for r in check_runs if r.status != "completed"]
            conclusions = [r.conclusion for r in check_runs if r.status == "completed"]

            if pending:
                overall = "pending"
            elif any(c in ("failure", "timed_out", "cancelled", "action_required") for c in conclusions):
                overall = "failure"
            elif all(c in ("success", "neutral", "skipped") for c in conclusions if c):
                overall = "success"
            else:
                overall = "pending"

            icon_map = {"success": "✅", "failure": "❌", "timed_out": "⏱️", "cancelled": "🚫", "neutral": "⚪", "skipped": "⏭️"}
            lines = [f"CI: **{overall.upper()}** — {len(check_runs)} check(s) | PR: {pr_url}"]
            for r in check_runs:
                icon = icon_map.get(r.conclusion or "", "⏳")
                lines.append(f"  {icon} `{r.name}`: {r.conclusion or r.status}")

        else:
            # Fallback: commit combined status (legacy branch protection / webhooks)
            commit   = repo.get_commit(head_sha)
            combined = commit.get_combined_status()
            state_map = {"success": "success", "failure": "failure", "error": "failure", "pending": "pending"}
            overall   = state_map.get(combined.state, "no_ci") if combined.total_count > 0 else "no_ci"
            lines     = [f"CI: **{overall.upper()}** ({combined.total_count} status checks) | PR: {pr_url}"]

        print(f"   {'✅' if overall == 'success' else '❌' if overall == 'failure' else '⏳'} [GitHub CI] Status: {overall}")
        return {"status": overall, "summary": "\n".join(lines), "details_url": pr_url}

    except Exception as exc:
        print(f"   ❌ [GitHub CI] Error: {exc}")
        return {"status": "error", "summary": f"No se pudo obtener CI status: {exc}", "details_url": pr_url}