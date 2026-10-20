from __future__ import annotations

from pathlib import Path

URI = "usage://getting-started"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CANDIDATES = [
    PROJECT_ROOT / "docs" / "agent" / "agent-guide.md",
    PROJECT_ROOT / "docs" / "agent-guide.md",
    PROJECT_ROOT / "agent-guide.md",
]


def _find_file() -> Path | None:
    for c in CANDIDATES:
        if c.exists():
            return c
    return None


def register(mcp) -> None:
    @mcp.resource(URI)
    def agent_guide() -> str:
        """Guia operativa para el agente LLM.

        Describe las 4 tools, los 3 resources, el flujo recomendado para una
        auditoria y para generar un diseno, y como manejar errores comunes.
        """
        path = _find_file()
        if path is None:
            return (
                "# agent-guide.md no encontrado\n\n"
                "El servidor busca `docs/agent/agent-guide.md` en el proyecto."
            )
        return path.read_text(encoding="utf-8")