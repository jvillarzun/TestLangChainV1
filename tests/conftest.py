"""
tests/conftest.py
─────────────────
Fixtures compartidos para todos los tests de criterios de evaluación.
Usa TEST_MODE=true — no gasta tokens Groq.
"""

import os
import pytest

# Forzar TEST_MODE antes de importar cualquier módulo del proyecto
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CHECKPOINTER", "sqlite")
os.environ.setdefault("SQLITE_PATH", ":memory:")  # SQLite in-memory para tests


from state.cycle_state import initial_state, CycleState


@pytest.fixture
def challenge_contador() -> CycleState:
    """Estado inicial para challenge brownfield 'contador en página principal'."""
    return initial_state(
        thread_id="test-contador-001",
        challenge_name="ContadorMACH",
        challenge_type="brownfield",
        challenge_description="Agregar un contador en la página principal que aumente de 1 en 1 al presionar un botón.",
        challenge_success_criteria=[
            "Contador visible en la página principal",
            "Botón que incrementa el contador en +1 por click",
            "Estado reseteado al recargar la página",
        ],
    )


@pytest.fixture
def estado_con_feedback_dev(challenge_contador) -> CycleState:
    """Estado con un rechazo HITL en fase DEV — simula alucinación detectada."""
    state = dict(challenge_contador)
    state["current_phase"] = "dev"
    state["retry_count"] = 1
    state["dev_content"] = "# DEVSPECS.md\n\nImplementación con useState en page.tsx sin 'use client'"
    state["hitl_decisions"] = [{
        "phase":     "dev",
        "reviewer":  "dev_lead",
        "decision":  "reject",
        "feedback":  "page.tsx es Server Component — no puede usar useState directamente. Crear CounterSection.tsx con 'use client'.",
        "timestamp": "2026-04-23T10:00:00",
    }]
    return state


@pytest.fixture
def estado_max_retries(challenge_contador) -> CycleState:
    """Estado con retry_count en el límite máximo."""
    state = dict(challenge_contador)
    state["current_phase"] = "dev"
    state["retry_count"] = 3
    state["hitl_decisions"] = [
        {"phase": "dev", "decision": "reject", "feedback": "fix 1", "reviewer": "dev_lead", "timestamp": "2026-04-23T10:00:00"},
        {"phase": "dev", "decision": "reject", "feedback": "fix 2", "reviewer": "dev_lead", "timestamp": "2026-04-23T10:05:00"},
        {"phase": "dev", "decision": "reject", "feedback": "fix 3", "reviewer": "dev_lead", "timestamp": "2026-04-23T10:10:00"},
    ]
    return state
