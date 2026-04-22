"""
nodes/dev/dev_validator.py
───────────────────────────
Valida el output del Dev Agent antes de abrir PRs.

Detecta:
  - Placeholders / lazy coding (TODO, FIXME, "tu lógica aquí", etc.)
  - Archivos vacíos o con contenido mínimo
  - Ausencia del bloque FILE: requerido por el prompt

Retorna un ValidationResult con lista de errores y un flag `is_valid`.
"""

import re
from dataclasses import dataclass, field


# ── Patrones que indican lazy coding ──────────────────────────────────────────
_LAZY_PATTERNS: list[tuple[str, str]] = [
    (r"#\s*TODO",                        "TODO comment encontrado"),
    (r"#\s*FIXME",                       "FIXME comment encontrado"),
    (r"//\s*TODO",                       "TODO comment encontrado"),
    (r"//\s*FIXME",                      "FIXME comment encontrado"),
    (r"//\s*tu (lógica|código) aquí",    "Placeholder 'tu lógica aquí'"),
    (r"//\s*your (logic|code) here",     "Placeholder 'your code here'"),
    (r"pass\s*#",                        "Python pass con comentario (stub)"),
    (r"raise NotImplementedError",       "NotImplementedError sin implementar"),
    (r"\.\.\.(\s*#.*)?$",               "Ellipsis como cuerpo de función"),
    (r"# Agregar .{0,40} aquí",         "Placeholder 'Agregar X aquí'"),
    (r"# Implementar",                   "Placeholder 'Implementar'"),
    (r"// Implementar",                  "Placeholder 'Implementar'"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE | re.MULTILINE), msg) for p, msg in _LAZY_PATTERNS]

# Mínimo de chars para considerar un archivo "no vacío"
_MIN_FILE_CONTENT = 50


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_found: int = 0

    def summary(self) -> str:
        lines = [
            f"{'✅ VÁLIDO' if self.is_valid else '❌ INVÁLIDO'} — {self.files_found} archivo(s) encontrado(s)",
        ]
        if self.errors:
            lines.append(f"  Errores ({len(self.errors)}):")
            lines.extend(f"    • {e}" for e in self.errors)
        if self.warnings:
            lines.append(f"  Advertencias ({len(self.warnings)}):")
            lines.extend(f"    • {w}" for w in self.warnings)
        return "\n".join(lines)


def validate_dev_output(content: str) -> ValidationResult:
    """
    Valida el output completo del Dev Agent.

    Args:
        content: Texto completo generado por el LLM (DEVSPECS + bloques FILE)

    Returns:
        ValidationResult con errores y warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. Verificar que existan bloques FILE: ────────────────────────────────
    file_headers = re.findall(r"^##\s+FILE:\s+(.+)$", content, re.MULTILINE)
    files_found = len(file_headers)

    if files_found == 0:
        errors.append("No se encontró ningún bloque '## FILE: repo/path' — el agente no generó código")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings, files_found=0)

    # ── 2. Extraer bloques de código por archivo ──────────────────────────────
    # Patrón: ## FILE: path\n```ext\n...código...\n```
    file_blocks = re.findall(
        r"##\s+FILE:\s+(.+?)\n```\w*\n(.*?)```",
        content,
        re.DOTALL,
    )

    if not file_blocks:
        warnings.append(f"Se encontraron {files_found} headers FILE: pero no se pudieron extraer bloques de código")

    # ── 3. Validar cada bloque ────────────────────────────────────────────────
    for file_path, code in file_blocks:
        file_path = file_path.strip()

        # Contenido mínimo
        if len(code.strip()) < _MIN_FILE_CONTENT:
            errors.append(f"[{file_path}] Contenido demasiado corto ({len(code.strip())} chars) — posible stub vacío")
            continue

        # Patrones lazy
        for pattern, msg in _COMPILED:
            match = pattern.search(code)
            if match:
                line_num = code[: match.start()].count("\n") + 1
                errors.append(f"[{file_path}] línea ~{line_num}: {msg}")

    # ── 4. Verificar checklist en DEVSPECS ────────────────────────────────────
    if "status: READY_FOR_REVIEW" not in content:
        warnings.append("No se encontró 'status: READY_FOR_REVIEW' al final del output")

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        files_found=files_found,
    )


def parse_file_blocks(content: str) -> list[dict]:
    """
    Extrae archivos del nuevo formato ## FILE: repo/path.

    Retorna lista de dicts: [{"repo": str, "path": str, "content": str}]
    Compatible con _push_files_and_open_pr().
    """
    blocks = re.findall(
        r"##\s+FILE:\s+(\S+?)/(\S+?)\n```\w*\n(.*?)```",
        content,
        re.DOTALL,
    )

    files = []
    for repo, path, code in blocks:
        files.append({
            "repo":    repo.strip(),
            "path":    path.strip(),
            "content": code.strip(),
        })
    return files
