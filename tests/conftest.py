from __future__ import annotations

from pathlib import Path

import pytest

from server.mcp_server import mcp


PROJECT_ROOT = Path(__file__).parent.parent
TEST_MODEL_DIR = PROJECT_ROOT / "proyectos" / "test power bi"


def _discover_pbip() -> Path:
    candidates = sorted(TEST_MODEL_DIR.glob("*.pbip"))
    if not candidates:
        raise RuntimeError(
            f"No se encontro ningun .pbip en {TEST_MODEL_DIR}. "
            "Coloca un proyecto Power BI para que los tests tengan algo con que trabajar."
        )
    return candidates[0]


TEST_PBIP = _discover_pbip()
TEST_PROJECT_DIR = TEST_PBIP.parent
TEST_SEMANTIC_MODEL = next(TEST_PROJECT_DIR.glob("*.SemanticModel"), None)
TEST_REPORT = next(TEST_PROJECT_DIR.glob("*.Report"), None)


@pytest.fixture(scope="session")
def tools() -> dict:
    return {name: t.fn for name, t in mcp._tool_manager._tools.items()}


@pytest.fixture(scope="session")
def project_path() -> str:
    return str(TEST_PROJECT_DIR)


@pytest.fixture(scope="session")
def semantic_model_path() -> str:
    return str(TEST_SEMANTIC_MODEL)


@pytest.fixture(scope="session")
def report_path() -> str:
    return str(TEST_REPORT)
