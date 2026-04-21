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
  REPO_BE_NAME (mach-backend-test-hackathon),
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
    REPO_BE_NAME,
    REPO_FE_NAME,
)

# ── Singleton cliente ─────────────────────────────────────────────────────────
_gh = Github(GITHUB_TOKEN)

# Archivos clave que se incluyen en el contexto por defecto
_KEY_FILES = [
    "package.json",
    "src/app.js",
    "src/server.js",
    "src/app/page.tsx",
    "src/app/layout.tsx",
    "src/lib/api.ts",
]


def _get_repo(repo_name: str) -> Repository:
    """Devuelve el objeto Repository. repo_name puede ser 'owner/repo' o solo 'repo'."""
    full_name = repo_name if "/" in repo_name else f"{GITHUB_USERNAME}/{repo_name}"
    return _gh.get_repo(full_name)


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

        # Contenido de archivos clave
        key_contents: dict[str, str] = {}
        for path in _KEY_FILES:
            try:
                content_file = repo.get_contents(path, ref=default_branch)
                if not isinstance(content_file, list):
                    key_contents[path] = content_file.decoded_content.decode("utf-8")
            except UnknownObjectException:
                pass  # archivo no existe en este repo — omitir
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
    try:
        repo = _get_repo(repo_name)
        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha

        # Crear rama (si ya existe, reutilizarla)
        try:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
            print(f"[GitHub] Rama '{branch_name}' creada en {repo_name}")
        except GithubException as exc:
            if exc.status == 422:  # rama ya existe
                print(f"[GitHub] Rama '{branch_name}' ya existe — reutilizando")
            else:
                raise

        # Hacer commit de cada archivo
        commit_sha: str | None = None
        for change in changes:
            path: str = change["path"]
            content: str = change["content"]
            try:
                existing = repo.get_contents(path, ref=branch_name)
                # Archivo existe → actualizar
                if isinstance(existing, list):
                    existing = existing[0]
                result = repo.update_file(
                    path=path,
                    message=commit_message,
                    content=content,
                    sha=existing.sha,
                    branch=branch_name,
                )
            except UnknownObjectException:
                # Archivo no existe → crear
                result = repo.create_file(
                    path=path,
                    message=commit_message,
                    content=content,
                    branch=branch_name,
                )
            commit_sha = result["commit"].sha
            print(f"[GitHub] Committed: {path}")

        return commit_sha

    except Exception as exc:
        print(f"[GitHub] Error en create_branch_and_push({repo_name}): {exc}")
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
    try:
        repo = _get_repo(repo_name)
        target_base = base or repo.default_branch

        # Verificar si ya existe un PR abierto para esta rama
        open_prs = repo.get_pulls(state="open", head=f"{GITHUB_USERNAME}:{branch_name}", base=target_base)
        for pr in open_prs:
            print(f"[GitHub] PR ya existe: {pr.html_url}")
            return pr.html_url

        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=target_base,
        )
        print(f"[GitHub] PR abierto: {pr.html_url}")
        return pr.html_url

    except Exception as exc:
        print(f"[GitHub] Error en open_pull_request({repo_name}): {exc}")
        return None
