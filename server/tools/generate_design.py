from __future__ import annotations

DEFAULT_PALETTE = [
    "#1F4E79",
    "#2E75B6",
    "#9DC3E6",
    "#F2F2F2",
    "#404040",
    "#7F7F7F",
    "#C00000",
    "#ED7D31",
]


def _build_theme() -> dict:
    return {
        "name": "PowerBI Corporate Theme",
        "dataColors": DEFAULT_PALETTE,
        "background": "#FFFFFF",
        "foreground": "#252423",
        "tableAccent": DEFAULT_PALETTE[0],
        "good": "#1F8B4C",
        "neutral": "#7F7F7F",
        "bad": "#C00000",
        "maximum": DEFAULT_PALETTE[0],
        "center": DEFAULT_PALETTE[2],
        "minimum": DEFAULT_PALETTE[5],
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 14, "color": "#252423"},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#252423"},
            "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#404040"},
            "callout": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#252423"},
        },
        "visualStyles": {},
    }


def _estimate_canvas_height(visuals: list[dict]) -> int:
    """Calcula la altura requerida del canvas adecuándose al número y tipo de visuales."""
    padding = 15
    y = padding
    types = [v.get("type", "") for v in visuals]
    if any(t in ["slicer"] for t in types):
        y += 60 + padding
    cards = [t for t in types if t in ["card", "multiRowCard", "kpi"]]
    if cards:
        rows = (len(cards) - 1) // 4 + 1
        y += (110 + padding) * rows
    charts = [t for t in types if t in ["barChart", "columnChart", "lineChart", "areaChart", "pieChart", "donutChart", "clusteredColumnChart"]]
    if charts:
        rows = (len(charts) - 1) // 2 + 1
        y += (280 + padding) * rows
    tables = [t for t in types if t in ["table", "matrix"] or t not in ["slicer", "card", "multiRowCard", "kpi", "barChart", "columnChart", "lineChart", "areaChart", "pieChart", "donutChart", "clusteredColumnChart"]]
    if tables:
        y += 240 + padding
    # Se adecúa a los visuales colocados (mínimo base 720, pero crece sin techo rígido según los elementos)
    return max(720, y + padding)


def _suggest_pages(model: dict, goal: str | None) -> list[dict]:
    tables = [t["name"] for t in model.get("tables", [])]
    measures = [m["name"] for m in model.get("measures", [])]
    first_measure = measures[0] if measures else "Indicador principal"
    first_table = tables[0] if tables else "Hechos"

    goal_norm = (goal or "").lower()
    if any(kw in goal_norm for kw in ["ventas", "sales", "ingresos", "revenue"]):
        kpis = ["Ventas Totales", "Margen", "Clientes Activos", "Ticket Promedio"]
    elif any(kw in goal_norm for kw in ["inventario", "stock", "almacen"]):
        kpis = ["Stock Total", "Rotacion", "Cobertura", "SKU sin movimiento"]
    elif any(kw in goal_norm for kw in ["rrhh", "empleado", "personal", "headcount"]):
        kpis = ["Headcount", "Rotacion Voluntaria", "Antiguedad Media", "Costo por Empleado"]
    else:
        kpis = [first_measure, "Variacion vs periodo anterior", "Top 5 categorias", "Distribucion geografica"]

    pages = [
        {
            "name": "Resumen Ejecutivo",
            "visuals": [
                {"type": "card", "title": kpis[0], "dataBinding": {"table": first_table, "measure": kpis[0]}},
                {"type": "card", "title": kpis[1], "dataBinding": {"table": first_table, "measure": kpis[1]}},
                {"type": "lineChart", "title": f"{kpis[0]} por periodo", "dataBinding": {"table": first_table, "measure": kpis[0]}},
                {"type": "table", "title": "Detalle", "dataBinding": {"table": first_table}},
            ],
        },
        {
            "name": "Analisis Detallado",
            "visuals": [
                {"type": "barChart", "title": kpis[2], "dataBinding": {"table": first_table, "measure": kpis[0], "axis": kpis[2]}},
                {"type": "donutChart", "title": kpis[3], "dataBinding": {"table": first_table, "measure": kpis[0], "legend": kpis[3]}},
            ],
        },
    ]

    for p in pages:
        h = _estimate_canvas_height(p["visuals"])
        p["canvas"] = {
            "width": 1280,
            "height": h,
            "displayOption": "FitToWidth" if h > 720 else "FitToPage",
            "is_adaptive": True,
        }

    return pages


def register(mcp) -> None:
    @mcp.tool()
    def generate_design(model: dict, report_goal: str | None = None) -> dict:
        """Genera theme.json y una propuesta de layout adaptable a los visuales sin tope fijo de 1280x720.

        Args:
            model: Salida de la tool `read_pbip`.
            report_goal: Objetivo del reporte en lenguaje natural (ej. "ventas por region").
                Si falta, devuelve instrucciones para que el cliente lo pida al usuario.

        Returns:
            Dict con `theme` (theme.json listo para importar en Power BI), `layout`
            (lista de paginas con visuales sugeridos y canvas adaptado dinamicamente) y
            guia de dimensionamiento.
        """
        if not report_goal:
            return {
                "missing_info": "report_goal",
                "message": "Falta el objetivo del reporte. Pregunta al usuario: 'Que debe mostrar este reporte? (ej. ventas por region, inventario por almacen, headcount por area).'",
            }

        return {
            "theme": _build_theme(),
            "layout": _suggest_pages(model, report_goal),
            "canvas_guidelines": {
                "max_fixed_size": None,
                "adaptive": True,
                "description": "El canvas no tiene un maximo fijo de 1280x720; sus dimensiones y altura se adecuan dinamicamente al numero y disposicion de los visuales para garantizar claridad y evitar sobreposiciones.",
            },
            "notes": [
                "theme.json es valido para importar en Power BI Desktop (Vista > Temas > Buscar tema).",
                "El layout y la altura del canvas se adecuan dinamicamente al volumen de visuales requeridos (scroll vertical cuando sea necesario).",
            ],
        }
