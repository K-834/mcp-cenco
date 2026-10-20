from __future__ import annotations


def test_end_to_end_pipeline(tools, project_path):
    fmt = tools["detect_format"](project_path)
    assert fmt["ok"] is True, f"detect_format fallo: {fmt}"

    model = tools["read_pbip"](fmt["semantic_model"], fmt["report"])
    assert len(model["tables"]) >= 1
    assert len(model["pages"]) >= 1

    validation = tools["validate_rules"](model)
    assert len(validation["findings"]) >= 1
    assert "findings" in validation and "pending_llm_review" in validation

    design = tools["generate_design"](model, report_goal="indicadores prime vs no prime")
    assert "theme" in design
    assert "layout" in design
    assert len(design["layout"]) >= 1


def test_pipeline_handles_missing_goal(tools, project_path):
    fmt = tools["detect_format"](project_path)
    model = tools["read_pbip"](fmt["semantic_model"], fmt["report"])
    design = tools["generate_design"](model, report_goal=None)
    assert design.get("missing_info") == "report_goal"
