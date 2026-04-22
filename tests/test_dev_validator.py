"""
tests/test_dev_validator.py
────────────────────────────
Tests para nodes/dev/dev_validator.py

Cubre:
  - validate_dev_output: sin bloques FILE, con código limpio, con placeholders,
    con archivo vacío, con warnings de READY_FOR_REVIEW
  - parse_file_blocks: formato correcto, múltiples archivos, sin bloques,
    extensiones variadas
"""

import pytest
from nodes.dev.dev_validator import validate_dev_output, parse_file_blocks, ValidationResult


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — bloques de contenido reutilizables
# ─────────────────────────────────────────────────────────────────────────────

CLEAN_FILE_BLOCK = """\
## FILE: backend/src/routes/ping.py
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping():
    return {"message": "pong"}
```
"""

CLEAN_OUTPUT = CLEAN_FILE_BLOCK + "\nstatus: READY_FOR_REVIEW"

TODO_FILE_BLOCK = """\
## FILE: backend/src/routes/fraud.py
```python
from fastapi import APIRouter

router = APIRouter()

@router.post("/check")
def check_fraud(transaction: dict):
    # TODO: Implementar lógica de detección
    return {}
```
"""

FIXME_FILE_BLOCK = """\
## FILE: frontend/src/App.tsx
```tsx
export default function App() {
  // FIXME: agregar autenticación
  return <div>Hello</div>;
}
```
"""

PLACEHOLDER_LOGICA = """\
## FILE: backend/src/service.py
```python
def calculate(amount):
    // tu lógica aquí
    pass
```
"""

NOT_IMPLEMENTED_BLOCK = """\
## FILE: backend/src/handler.py
```python
def handle_request(data):
    raise NotImplementedError
```
"""

EMPTY_FILE_BLOCK = """\
## FILE: backend/src/empty.py
```python
x = 1
```
"""

MULTI_FILE_OUTPUT = """\
## FILE: backend/src/routes/ping.py
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping():
    return {"message": "pong", "status": "ok"}
```

## FILE: frontend/src/views/Home.vue
```vue
<template>
  <div class="home">
    <h1>Home</h1>
    <p>Bienvenido al dashboard de MACH Race</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const title = ref('Home')
</script>
```

status: READY_FOR_REVIEW
"""


# ─────────────────────────────────────────────────────────────────────────────
# validate_dev_output
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateDevOutput:

    def test_valid_clean_output(self):
        result = validate_dev_output(CLEAN_OUTPUT)
        assert result.is_valid is True
        assert result.errors == []
        assert result.files_found == 1

    def test_no_file_blocks_returns_invalid(self):
        content = "# DEVSPECS\n\nAlgún texto sin bloques FILE.\n\nstatus: READY_FOR_REVIEW"
        result = validate_dev_output(content)
        assert result.is_valid is False
        assert result.files_found == 0
        assert any("no generó código" in e for e in result.errors)

    def test_todo_comment_detected(self):
        result = validate_dev_output(TODO_FILE_BLOCK)
        assert result.is_valid is False
        assert any("TODO" in e for e in result.errors)

    def test_fixme_comment_detected(self):
        result = validate_dev_output(FIXME_FILE_BLOCK)
        assert result.is_valid is False
        assert any("FIXME" in e for e in result.errors)

    def test_placeholder_logica_detected(self):
        result = validate_dev_output(PLACEHOLDER_LOGICA)
        assert result.is_valid is False
        assert any("lógica" in e.lower() or "placeholder" in e.lower() for e in result.errors)

    def test_not_implemented_error_detected(self):
        result = validate_dev_output(NOT_IMPLEMENTED_BLOCK)
        assert result.is_valid is False
        assert any("NotImplementedError" in e for e in result.errors)

    def test_empty_file_content_detected(self):
        result = validate_dev_output(EMPTY_FILE_BLOCK)
        assert result.is_valid is False
        assert any("corto" in e or "stub" in e for e in result.errors)

    def test_missing_ready_for_review_adds_warning(self):
        # Output limpio pero sin el status final
        content = CLEAN_FILE_BLOCK  # sin "status: READY_FOR_REVIEW"
        result = validate_dev_output(content)
        assert result.is_valid is True  # no es error, solo warning
        assert any("READY_FOR_REVIEW" in w for w in result.warnings)

    def test_multiple_files_all_clean(self):
        result = validate_dev_output(MULTI_FILE_OUTPUT)
        assert result.is_valid is True
        assert result.files_found == 2
        assert result.errors == []

    def test_multiple_files_one_with_todo(self):
        content = CLEAN_FILE_BLOCK + "\n" + TODO_FILE_BLOCK + "\nstatus: READY_FOR_REVIEW"
        result = validate_dev_output(content)
        assert result.is_valid is False
        assert result.files_found == 2
        # El error debe referenciar el archivo con TODO
        assert any("fraud.py" in e for e in result.errors)

    def test_files_found_count_is_correct(self):
        result = validate_dev_output(MULTI_FILE_OUTPUT)
        assert result.files_found == 2

    def test_summary_contains_valid_label(self):
        result = validate_dev_output(CLEAN_OUTPUT)
        assert "✅ VÁLIDO" in result.summary()

    def test_summary_contains_invalid_label(self):
        result = validate_dev_output(TODO_FILE_BLOCK)
        assert "❌ INVÁLIDO" in result.summary()

    def test_summary_lists_errors(self):
        result = validate_dev_output(TODO_FILE_BLOCK)
        summary = result.summary()
        assert "TODO" in summary


# ─────────────────────────────────────────────────────────────────────────────
# parse_file_blocks
# ─────────────────────────────────────────────────────────────────────────────

class TestParseFileBlocks:

    def test_single_file_parsed_correctly(self):
        files = parse_file_blocks(CLEAN_FILE_BLOCK)
        assert len(files) == 1
        assert files[0]["repo"] == "backend"
        assert files[0]["path"] == "src/routes/ping.py"
        assert "pong" in files[0]["content"]

    def test_multiple_files_parsed(self):
        files = parse_file_blocks(MULTI_FILE_OUTPUT)
        assert len(files) == 2
        repos = {f["repo"] for f in files}
        assert "backend" in repos
        assert "frontend" in repos

    def test_no_blocks_returns_empty_list(self):
        files = parse_file_blocks("# Solo texto sin bloques FILE")
        assert files == []

    def test_content_is_stripped(self):
        files = parse_file_blocks(CLEAN_FILE_BLOCK)
        assert not files[0]["content"].startswith("\n")
        assert not files[0]["content"].endswith("\n")

    def test_python_extension_block(self):
        files = parse_file_blocks(CLEAN_FILE_BLOCK)
        assert "router" in files[0]["content"]

    def test_vue_extension_block(self):
        files = parse_file_blocks(MULTI_FILE_OUTPUT)
        vue_file = next(f for f in files if "vue" in f["path"])
        assert "<template>" in vue_file["content"]

    def test_repo_and_path_split_correctly(self):
        content = """\
## FILE: frontend/src/components/Button.tsx
```tsx
export const Button = ({ label }: { label: string }) => (
  <button className="btn">{label}</button>
);
```
"""
        files = parse_file_blocks(content)
        assert files[0]["repo"] == "frontend"
        assert files[0]["path"] == "src/components/Button.tsx"

    def test_returns_list_of_dicts_with_required_keys(self):
        files = parse_file_blocks(CLEAN_FILE_BLOCK)
        for f in files:
            assert "repo" in f
            assert "path" in f
            assert "content" in f
