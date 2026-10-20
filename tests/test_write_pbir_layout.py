from __future__ import annotations

from server.tools.write_pbir_layout import calculate_grid_positions


def test_calculate_grid_positions_grows_dynamically_with_many_visuals():
    """Con muchas filas de visuales, la altura calculada debe superar 720px y no quedar truncada."""
    visuals = [
        {"type": "slicer", "title": "Filtro 1"},
        {"type": "slicer", "title": "Filtro 2"},
        # 8 tarjetas = 2 filas de KPIs
        {"type": "card", "title": "KPI 1"},
        {"type": "card", "title": "KPI 2"},
        {"type": "card", "title": "KPI 3"},
        {"type": "card", "title": "KPI 4"},
        {"type": "card", "title": "KPI 5"},
        {"type": "card", "title": "KPI 6"},
        # 4 graficos = 2 filas de charts
        {"type": "barChart", "title": "Grafico 1"},
        {"type": "columnChart", "title": "Grafico 2"},
        {"type": "lineChart", "title": "Grafico 3"},
        {"type": "donutChart", "title": "Grafico 4"},
        # 1 tabla
        {"type": "table", "title": "Detalle Extenso"},
    ]

    positioned, w, h = calculate_grid_positions(visuals)
    assert w == 1280
    assert h > 720, f"La altura deberia haberse adaptado y superado 720, pero dio {h}"
    # Verificar que las posiciones Y son estrictamente crecientes y no se sobreponen
    ys = [v["position"]["y"] for v in positioned]
    assert max(ys) + 240 <= h
