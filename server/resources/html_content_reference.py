from __future__ import annotations

from pathlib import Path

URI = "html-content://reference"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _candidate_paths() -> list[Path]:
    """Orden de busqueda del skill. El primero que exista gana.

    Prioriza copias project-local para que el resource funcione en cualquier
    clon/copia del repo, sin depender del estado del sistema del usuario.
    """
    return [
        PROJECT_ROOT / "docs" / "agent" / "SKILL_HTML_POWERBI.md",
        PROJECT_ROOT / ".opencode" / "skills" / "diseno-bi-content-cenco" / "SKILL.md",
        PROJECT_ROOT / ".agents" / "skills" / "diseno-bi-content-cenco" / "SKILL.md",
        PROJECT_ROOT / "skills" / "diseno-bi-content-cenco" / "SKILL.md",
        Path.home() / ".config" / "opencode" / "skills" / "diseno-bi-content-cenco" / "SKILL.md",
    ]


def _find_skill_file() -> Path | None:
    for candidate in _candidate_paths():
        if candidate.exists():
            return candidate
    return None


def register(mcp) -> None:
    @mcp.resource(URI)
    def skill_reference() -> str:
        """Skill de referencia sobre HTML/CSS embebido en Power BI (visual "HTML Content").

        Busca el archivo en este orden:
          1. docs/agent/SKILL_HTML_POWERBI.md (canonica, versionada con el repo)
          2. .opencode/skills/diseno-bi-content-cenco/SKILL.md (project-local para opencode)
          3. .agents/skills/diseno-bi-content-cenco/SKILL.md
          4. skills/diseno-bi-content-cenco/SKILL.md
          5. ~/.config/opencode/skills/diseno-bi-content-cenco/SKILL.md

        Sincroniza con `uv run python scripts/sync_skill.py`.
        """
        path = _find_skill_file()
        if path is None:
            return (
                "# HTML Content reference skill no encontrado\n\n"
                "El servidor busca el skill en:\n"
                "  1. docs/agent/SKILL_HTML_POWERBI.md (canonica)\n"
                "  2. .opencode/skills/diseno-bi-content-cenco/SKILL.md\n"
                "  3. .agents/skills/diseno-bi-content-cenco/SKILL.md\n"
                "  4. skills/diseno-bi-content-cenco/SKILL.md\n"
                "  5. ~/.config/opencode/skills/diseno-bi-content-cenco/SKILL.md\n\n"
                "Corré `uv run python scripts/sync_skill.py` para regenerarlo."
            )
        return path.read_text(encoding="utf-8")

