from __future__ import annotations


def _model(tools, semantic_model_path, report_path):
    return tools["read_pbip"](semantic_model_path, report_path)


def test_returns_missing_info_without_goal(tools, semantic_model_path, report_path):
    result = tools["generate_design"](_model(tools, semantic_model_path, report_path), report_goal=None)
    assert "missing_info" in result
    assert result["missing_info"] == "report_goal"


def test_returns_theme_and_layout_with_goal(tools, semantic_model_path, report_path):
    result = tools["generate_design"](_model(tools, semantic_model_path, report_path), report_goal="ventas por region")
    assert "theme" in result
    assert "layout" in result
    assert result["theme"]["name"]
    assert isinstance(result["theme"]["dataColors"], list)
    assert len(result["theme"]["dataColors"]) >= 4
    assert len(result["layout"]) >= 1


def test_picks_visual_types_for_known_goal(tools, semantic_model_path, report_path):
    result = tools["generate_design"](_model(tools, semantic_model_path, report_path), report_goal="ventas por region")
    types = [v["type"] for page in result["layout"] for v in page["visuals"]]
    assert "card" in types


def test_handles_unknown_goal(tools, semantic_model_path, report_path):
    result = tools["generate_design"](_model(tools, semantic_model_path, report_path), report_goal="metricas custom raras")
    assert "theme" in result
    assert "layout" in result


def test_canvas_adapts_to_visuals_without_rigid_max_720(tools, semantic_model_path, report_path):
    """El canvas no debe tener un máximo rígido de 1280x720, sino adecuarse a los visuales."""
    result = tools["generate_design"](_model(tools, semantic_model_path, report_path), report_goal="ventas por region")
    assert "canvas_guidelines" in result
    assert result["canvas_guidelines"]["max_fixed_size"] is None
    assert result["canvas_guidelines"]["adaptive"] is True

    for page in result["layout"]:
        assert "canvas" in page
        canvas = page["canvas"]
        assert canvas["is_adaptive"] is True
        assert canvas["height"] >= 720
        assert "displayOption" in canvas

