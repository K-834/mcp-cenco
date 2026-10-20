from __future__ import annotations

import json
from pathlib import Path

URI = "power-bi://reference"
URI_SKILL = "power-bi://skill/{name}"
URI_RULES_SUMMARY = "power-bi://rules/summary"
URI_GRID_LAYOUT = "power-bi://grid-layout"
URI_ANTI_PATTERNS = "power-bi://anti-patterns-compact"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Skills disponibles via MCP resource. Hay UN SOLO skill local (que cubre
# audit/edit/create + diseno HTML Content) y los 5 skills Microsoft.
AVAILABLE_SKILLS = {
    "power-bi-pbip": "logica-bi-pbip-cenco",
    "powerbi-report-authoring": "powerbi-report-authoring",
    "powerbi-report-design": "powerbi-report-design",
    "powerbi-report-planning": "powerbi-report-planning",
    "powerbi-report-management": "powerbi-report-management",
    "semantic-model-authoring": "semantic-model-authoring",
}


def _candidate_paths() -> list[Path]:
    """Orden de busqueda del skill local unificado. El primero que exista gana.

    Prioriza copias project-local para que el resource funcione en cualquier
    clon/copia del repo, sin depender del estado del sistema del usuario.
    """
    return [
        PROJECT_ROOT / "docs" / "agent" / "SKILL_POWER_BI.md",
        PROJECT_ROOT / "docs" / "SKILL_POWER_BI.md",
        PROJECT_ROOT / ".opencode" / "skills" / "logica-bi-pbip-cenco" / "SKILL.md",
        PROJECT_ROOT / ".agents" / "skills" / "logica-bi-pbip-cenco" / "SKILL.md",
        PROJECT_ROOT / "skills" / "logica-bi-pbip-cenco" / "SKILL.md",
        Path.home() / ".config" / "opencode" / "skills" / "logica-bi-pbip-cenco" / "SKILL.md",
    ]


def _candidate_skill_paths(name: str, slug: str) -> list[Path]:
    """Busca un skill (local o Microsoft) en sus multiples ubicaciones."""
    return [
        PROJECT_ROOT / "docs" / "agent" / name / "SKILL.md",
        PROJECT_ROOT / ".opencode" / "skills" / slug / "SKILL.md",
        PROJECT_ROOT / ".agents" / "skills" / slug / "SKILL.md",
        PROJECT_ROOT / "skills" / slug / "SKILL.md",
        Path.home() / ".config" / "opencode" / "skills" / slug / "SKILL.md",
    ]


def _find_skill_file() -> Path | None:
    for candidate in _candidate_paths():
        if candidate.exists():
            return candidate
    return None


def _load_rules() -> list[dict]:
    """Carga rules.json (versionado en el repo)."""
    path = PROJECT_ROOT / "rules" / "rules.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("rules", [])
    except (json.JSONDecodeError, OSError):
        return []


def register(mcp) -> None:
    @mcp.resource(URI)
    def skill_reference() -> str:
        """Skill de referencia sobre Power BI (PBIP/PBIR/TMDL).

        Busca el archivo en este orden:
          1. docs/agent/SKILL_POWER_BI.md (canonica, versionada con el repo)
          2. docs/SKILL_POWER_BI.md (compatibilidad con versiones anteriores)
          3. .opencode/skills/logica-bi-pbip-cenco/SKILL.md (project-local para opencode)
          4. .agents/skills/logica-bi-pbip-cenco/SKILL.md
          5. skills/logica-bi-pbip-cenco/SKILL.md
          6. ~/.config/opencode/skills/logica-bi-pbip-cenco/SKILL.md

        Sincroniza con `uv run python scripts/sync_skill.py`.
        """
        path = _find_skill_file()
        if path is None:
            return (
                "# Power BI reference skill no encontrado\n\n"
                "El servidor busca el skill en:\n"
                "  1. docs/agent/SKILL_POWER_BI.md (canonica)\n"
                "  2. docs/SKILL_POWER_BI.md (legacy)\n"
                "  3. .opencode/skills/logica-bi-pbip-cenco/SKILL.md\n"
                "  4. .agents/skills/logica-bi-pbip-cenco/SKILL.md\n"
                "  5. skills/logica-bi-pbip-cenco/SKILL.md\n"
                "  6. ~/.config/opencode/skills/logica-bi-pbip-cenco/SKILL.md\n\n"
                "Corré `uv run python scripts/sync_skill.py` para regenerarlo."
            )
        return path.read_text(encoding="utf-8")

    @mcp.resource(URI_SKILL)
    def get_skill(name: str) -> str:
        """Sirve un skill por nombre (local o Microsoft) para clientes sin skill loading nativo.

        Nombres validos: power-bi-pbip (local), powerbi-report-authoring, powerbi-report-design,
        powerbi-report-planning, powerbi-report-management, semantic-model-authoring.
        """
        if name not in AVAILABLE_SKILLS:
            return (
                f"# Skill desconocido: {name}\n\n"
                f"Skills disponibles: {', '.join(sorted(AVAILABLE_SKILLS.keys()))}"
            )
        slug = AVAILABLE_SKILLS[name]
        for candidate in _candidate_skill_paths(name, slug):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        return (
            f"# Skill {name} no encontrado en ninguna ubicacion\n\n"
            f"Ejecuta `uv run scripts/run.py setup-microsoft && uv run scripts/run.py sync` para descargarlo."
        )

    @mcp.resource(URI_RULES_SUMMARY)
    def rules_summary() -> str:
        """Tabla compacta de las 36 reglas compiladas (id, categoria, severidad, titulo).

        Util cuando el agente necesita ver todas las reglas de un vistazo
        sin leer rules.json completo. Para detalle de cada regla usar
        el skill local power-bi-pbip que referencia rules.json.
        """
        rules = _load_rules()
        if not rules:
            return "# Sin reglas compiladas\n\nCorré `uv run scripts/run.py compile`."

        lines = ["# Resumen de las reglas de auditoria Power BI\n"]
        lines.append(f"Total: **{len(rules)} reglas**\n")
        lines.append("| ID | Severidad | Categoria | Titulo |")
        lines.append("|---|---|---|---|")
        for r in rules:
            rid = r.get("id", "?")
            sev = r.get("severity", "?")
            cat = r.get("category", "?")
            title = r.get("title", "").replace("|", "\\|")[:80]
            lines.append(f"| {rid} | {sev} | {cat} | {title} |")
        return "\n".join(lines)

    @mcp.resource(URI_GRID_LAYOUT)
    def grid_layout() -> str:
        """Convencion del proyecto: grilla modular adaptable a los visuales (sin limite rigido de 1280x720)."""
        return """# Grilla canvas del proyecto (adaptable a visuales)

| Zona | Sugerencia Y | H sugerido | W | Visual recomendado |
|---|---|---|---|---|
| Encabezado / Filtros | 15 | 60 | 1250 | slicer |
| Fila de KPIs | 90 | 110 | 290 c/u | card, multiRowCard |
| Graficos principales | 215+ | 280 c/u | 610 c/u | clusteredColumnChart, lineChart |
| Detalle de datos | Segun flujo | 240 | 1250 | table, matrix |

Reglas del proyecto:
- El canvas NO tiene un maximo estricto de 1280x720: sus dimensiones y altura se adecuan dinamicamente a la cantidad y tamano de los visuales.
- Si hay multiples filas de graficos o tablas extensas, el alto del canvas crece verticalmente (ej. 900px, 1200px) con displayOption='FitToWidth'.
- 4 franjas verticales no se solapan: Header arriba, KPIs debajo, charts al medio, detalle al fondo.
- W = 1250 deja 15px de margen a cada lado sobre base de 1280px.
"""

    @mcp.resource(URI_ANTI_PATTERNS)
    def anti_patterns() -> str:
        """Top 10 anti-patterns del proyecto (compacto).

        Para el catalogo exhaustivo de visual types y patrones DAX,
        consultar los skills oficiales de microsoft/skills-for-fabric:
        - powerbi-report-authoring (PBIR)
        - semantic-model-authoring (TMDL/DAX)
        """
        return """# Top 10 anti-patterns del proyecto

| # | Categoria | Mal | Bien |
|---|---|---|---|
| 1 | DAX | `A / B` sin proteccion | `DIVIDE(A, B, 0)` |
| 2 | DAX | `FILTER(T, T[col]=x)` | filtro directo o `REMOVEFILTERS` |
| 3 | DAX | medida sin metadatos | `formatString`, `displayFolder`, `description` |
| 4 | Modelo | relacion bidirectional | single-direction |
| 5 | Modelo | FK visible | ocultar (`isHidden = true`) |
| 6 | Modelo | nombre crudo `customer_id` | nomenclatura legible (`Customer ID`) |
| 7 | Visual | `card` legacy | `cardVisual` |
| 8 | Visual | `table` legacy | `tableEx` |
| 9 | Visual | `matrix` legacy | `pivotTable` |
| 10 | Visual | `map` legacy | `azureMap` |
"""
