from __future__ import annotations

import json
from pathlib import Path


def calculate_grid_positions(
    visuals: list[dict],
    canvas_w: int = 1280,
    canvas_h: int | None = None,
) -> tuple[list[dict], int, int]:
    """Calcula coordenadas y dimensiones en grilla adaptativa que se ajusta a los visuales."""
    padding = 15

    cards = [v for v in visuals if v.get("type") in ["card", "multiRowCard", "kpi"]]
    charts = [v for v in visuals if v.get("type") in ["barChart", "columnChart", "lineChart", "areaChart", "pieChart", "donutChart", "clusteredColumnChart"]]
    tables = [v for v in visuals if v.get("type") in ["table", "matrix"]]
    slicers = [v for v in visuals if v.get("type") in ["slicer"]]
    other = [v for v in visuals if v not in cards and v not in charts and v not in tables and v not in slicers]

    positioned_visuals = []
    current_y = padding

    # 1. Posicionar Slicers en la parte superior
    if slicers:
        slicer_w = (canvas_w - (padding * (len(slicers) + 1))) // len(slicers)
        for i, s in enumerate(slicers):
            x = padding + i * (slicer_w + padding)
            s["position"] = {"x": x, "y": current_y, "width": slicer_w, "height": 60, "tabOrder": 100 + i}
            positioned_visuals.append(s)
        current_y += 60 + padding

    # 2. Posicionar Cards (KPIs)
    if cards:
        cols = min(len(cards), 4)
        card_w = (canvas_w - (padding * (cols + 1))) // cols
        for i, c in enumerate(cards):
            col = i % 4
            row = i // 4
            x = padding + col * (card_w + padding)
            y = current_y + row * (110 + padding)
            c["position"] = {"x": x, "y": y, "width": card_w, "height": 110, "tabOrder": 200 + i}
            positioned_visuals.append(c)
        current_y += (110 + padding) * ((len(cards) - 1) // 4 + 1)

    # 3. Posicionar Gráficos Principales
    if charts:
        cols = min(len(charts), 2)
        chart_w = (canvas_w - (padding * (cols + 1))) // cols
        chart_h = 280
        for i, ch in enumerate(charts):
            col = i % 2
            row = i // 2
            x = padding + col * (chart_w + padding)
            y = current_y + row * (chart_h + padding)
            ch["position"] = {"x": x, "y": y, "width": chart_w, "height": chart_h, "tabOrder": 300 + i}
            positioned_visuals.append(ch)
        current_y += (chart_h + padding) * ((len(charts) - 1) // 2 + 1)

    # 4. Posicionar Tablas / Matrices en la parte inferior
    if tables or other:
        table_h = 240
        t_list = tables + other
        t_w = (canvas_w - (padding * (len(t_list) + 1))) // len(t_list)
        for i, t in enumerate(t_list):
            x = padding + i * (t_w + padding)
            t["position"] = {"x": x, "y": current_y, "width": t_w, "height": table_h, "tabOrder": 400 + i}
            positioned_visuals.append(t)
        current_y += table_h + padding

    # La altura se adecúa a los visuales colocados (mínimo base 720 si hay pocos visuales, pero crece libremente)
    calculated_h = current_y + padding
    final_canvas_h = canvas_h if canvas_h is not None else max(720, calculated_h)

    return positioned_visuals, canvas_w, final_canvas_h


def register(mcp) -> None:
    @mcp.tool()
    def write_pbir_layout(
        pbip_path: str,
        page_display_name: str,
        visuals: list[dict],
        canvas_width: int = 1280,
        canvas_height: int | None = None,
    ) -> dict:
        """Escribe archivos reales de reporte PBIR (page.json y visual.json) con posicionamiento adaptativo a los visuales.

        El canvas no tiene un máximo rígido de 1280x720: la altura se adecúa dinámicamente
        a la cantidad y disposición de visuales para evitar solapamientos y permitir scroll vertical si se requiere.

        Args:
            pbip_path: Ruta a la carpeta .pbip o manifiesto del proyecto.
            page_display_name: Nombre visible de la página (ej. "Resumen Ejecutivo").
            visuals: Lista de especificaciones de visuales (ej. [{"type": "card", "title": "Ventas"}, ...]).
            canvas_width: Ancho base del canvas (por defecto 1280).
            canvas_height: Altura del canvas (opcional; si no se indica, se calcula dinámicamente según los visuales).

        Returns:
            Dict con las rutas de la página, visuales creados y dimensiones del canvas adaptado.
        """
        p = Path(pbip_path)
        if p.is_file():
            p = p.parent

        reports = list(p.glob("*.Report"))
        if not reports:
            return {"error": "No se encontró la carpeta *.Report en la ruta del proyecto."}

        pages_dir = reports[0] / "definition" / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        # Generar ID sanitized para la página
        page_id = "page_" + "".join([c if c.isalnum() else "_" for c in page_display_name.lower()])
        page_dir = pages_dir / page_id
        page_dir.mkdir(parents=True, exist_ok=True)

        # 1. Posicionar e instanciar visuales adecuando el canvas
        positioned_visuals, final_w, final_h = calculate_grid_positions(
            visuals,
            canvas_w=canvas_width or 1280,
            canvas_h=canvas_height,
        )

        # 2. Crear page.json adaptado a la altura calculada
        page_json = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.3.0/schema.json",
            "name": page_id,
            "displayName": page_display_name,
            "displayOption": "FitToWidth" if final_h > 720 else "FitToPage",
            "height": final_h,
            "width": final_w,
        }
        (page_dir / "page.json").write_text(json.dumps(page_json, indent=2, ensure_ascii=False), encoding="utf-8")

        # 3. Guardar visual.json de cada visual
        visuals_dir = page_dir / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)
        created_visuals = []

        for i, vis_spec in enumerate(positioned_visuals):
            v_type = vis_spec.get("type", "card")
            v_title = vis_spec.get("title", f"Visual {i+1}")
            v_id = f"visual_{i+1}_{v_type}"
            v_dir = visuals_dir / v_id
            v_dir.mkdir(parents=True, exist_ok=True)

            visual_json = {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.3.0/schema.json",
                "name": v_id,
                "position": vis_spec["position"],
                "visual": {
                    "visualType": v_type,
                    "title": v_title,
                    "dataBinding": vis_spec.get("dataBinding", {}),
                },
            }
            (v_dir / "visual.json").write_text(json.dumps(visual_json, indent=2, ensure_ascii=False), encoding="utf-8")
            created_visuals.append(str(v_dir / "visual.json"))

        return {
            "success": True,
            "page": str(page_dir / "page.json"),
            "visuals_created": len(created_visuals),
            "visual_files": created_visuals,
            "canvas": {
                "width": final_w,
                "height": final_h,
                "displayOption": page_json["displayOption"],
                "adaptive": True,
            },
        }
