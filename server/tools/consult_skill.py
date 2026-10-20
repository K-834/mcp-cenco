from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

TOPIC_MAPPING = {
    "audit": ("logica-bi-pbip-cenco", "Reglas locales de auditoria y buenas practicas (36 reglas)"),
    "reglas": ("logica-bi-pbip-cenco", "Reglas locales de auditoria y buenas practicas (36 reglas)"),
    "pbip": ("logica-bi-pbip-cenco", "Formato PBIP y buenas practicas locales"),
    "html-content": ("logica-bi-pbip-cenco", "Diseno de KPIs y tarjetas con visual HTML Content"),
    "planning": ("powerbi-report-planning", "Metodologia de planificacion de reportes y dashboards Microsoft"),
    "plan": ("powerbi-report-planning", "Metodologia de planificacion de reportes y dashboards Microsoft"),
    "design": ("powerbi-report-design", "Principios de diseno visual, arquetipos, paletas y accesibilidad Microsoft"),
    "authoring": ("powerbi-report-authoring", "Mecanica PBIR, contenedores visuales, filtros y temas Microsoft"),
    "management": ("powerbi-report-management", "Despliegue a Fabric / Power BI Service via REST API Microsoft"),
    "model": ("semantic-model-authoring", "Modelado semantico TMDL, relaciones, DAX y particiones Microsoft"),
    "dax": ("semantic-model-authoring", "Modelado semantico TMDL, relaciones, DAX y particiones Microsoft"),
}


def _find_skill(slug: str) -> str | None:
    candidates = [
        PROJECT_ROOT / ".agents" / "skills" / slug / "SKILL.md",
        PROJECT_ROOT / "skills" / slug / "SKILL.md",
        PROJECT_ROOT / "docs" / "agent" / slug / "SKILL.md",
        PROJECT_ROOT / ".opencode" / "skills" / slug / "SKILL.md",
        PROJECT_ROOT / "docs" / "agent" / "SKILL_POWER_BI.md",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    return None


def register(mcp) -> None:
    @mcp.tool()
    def consult_skill(topic: str) -> dict:
        """Permite a la IA consultar de forma autonoma las guias y buenas practicas de Power BI segun el objetivo.

        La IA debe invocar esta herramienta cuando el usuario pida asesoramiento, diseno,
        planificacion o modelado en Power BI, para cargar el contexto metodologico adecuado.

        Args:
            topic: Tema a consultar ('planning', 'design', 'authoring', 'management', 'model', 'audit', 'html-content').

        Returns:
            Dict con el contenido de la guia metodologica y el rol a asumir.
        """
        t_clean = topic.strip().lower()
        mapping = TOPIC_MAPPING.get(t_clean)

        if not mapping:
            # Busqueda difusa por palabras clave
            for key, val in TOPIC_MAPPING.items():
                if key in t_clean or t_clean in key:
                    mapping = val
                    break

        if not mapping:
            return {
                "ok": False,
                "message": f"Tema '{topic}' no reconocido.",
                "available_topics": list(set(TOPIC_MAPPING.keys())),
            }

        slug, desc = mapping
        content = _find_skill(slug)

        if not content:
            return {
                "ok": False,
                "message": f"No se pudo cargar el archivo SKILL.md para {slug}.",
            }

        return {
            "ok": True,
            "topic": topic,
            "skill_slug": slug,
            "description": desc,
            "guidance": content,
        }
