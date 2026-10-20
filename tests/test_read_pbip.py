from __future__ import annotations


def _parsed(tools, semantic_model_path, report_path) -> dict:
    return tools["read_pbip"](semantic_model_path, report_path)


def test_extracts_at_least_one_table(tools, semantic_model_path, report_path):
    model = _parsed(tools, semantic_model_path, report_path)
    assert len(model["tables"]) >= 1
    assert all("name" in t for t in model["tables"])


def test_extracts_measures_with_format_metadata(tools, semantic_model_path, report_path):
    model = _parsed(tools, semantic_model_path, report_path)
    for m in model["measures"]:
        assert "name" in m
        assert "format_string" in m


def test_extracts_relationships(tools, semantic_model_path, report_path):
    model = _parsed(tools, semantic_model_path, report_path)
    for r in model["relationships"]:
        assert "from" in r
        assert "to" in r
        assert "cross_filter" in r


def test_extracts_pages(tools, semantic_model_path, report_path):
    model = _parsed(tools, semantic_model_path, report_path)
    assert len(model["pages"]) >= 1
    for p in model["pages"]:
        assert "name" in p
        assert "page_id" in p


def test_missing_semantic_model(tools, report_path, tmp_path):
    result = tools["read_pbip"](str(tmp_path / "no_existe"), report_path)
    assert "error" in result
