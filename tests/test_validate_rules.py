from __future__ import annotations


def _model(tools, semantic_model_path, report_path):
    return tools["read_pbip"](semantic_model_path, report_path)


def _synthetic_rule(rule_id: str, **overrides) -> dict:
    base = {
        "id": rule_id,
        "title": "Evitar relaciones bidireccionales innecesarias",
        "category": "rendimiento",
        "severity": "alta",
        "check_type": "automatico",
    }
    base.update(overrides)
    return base


def test_bidirectional_relationship_warning(tools):
    model = {
        "tables": [{"name": "A"}, {"name": "B"}],
        "measures": [],
        "relationships": [
            {"from": "A.x", "to": "B.y", "cross_filter": "bothDirections"},
        ],
        "pages": [],
    }
    rules = [_synthetic_rule("TEST-001", title="Evitar relaciones bidireccionales")]
    result = tools["validate_rules"](model, rules=rules)
    bidir = [f for f in result["findings"] if "bidireccional" in f.get("evidence", "").lower() and f["status"] == "warning"]
    assert bidir, f"Esperaba un WARNING de bidireccional. Findings: {[(f['title'][:50], f['status']) for f in result['findings']]}"


def test_measures_check_against_format(tools):
    model = {
        "tables": [],
        "measures": [
            {"name": "X", "format_string": "#,##0", "expression": "1", "source_file": "x.tmdl"},
        ],
        "relationships": [],
        "pages": [],
    }
    rules = [_synthetic_rule("TEST-002", title="Usar formatString en medidas DAX")]
    result = tools["validate_rules"](model, rules=rules)
    formato = [f for f in result["findings"] if "formatstring" in f.get("evidence", "").lower() or "formato" in f.get("evidence", "").lower()]
    assert formato
    for f in formato:
        assert f["status"] in {"pass", "warning"}


def test_measures_warn_when_missing_format(tools):
    model = {
        "tables": [],
        "measures": [
            {"name": "X", "format_string": "#,##0", "expression": "1", "source_file": "x.tmdl"},
            {"name": "Y", "format_string": None, "expression": "2", "source_file": "x.tmdl"},
        ],
        "relationships": [],
        "pages": [],
    }
    rules = [_synthetic_rule("TEST-003", title="Usar formatString en medidas DAX")]
    result = tools["validate_rules"](model, rules=rules)
    formato_warn = [f for f in result["findings"] if "Y" in f.get("evidence", "") and f["status"] == "warning"]
    assert formato_warn, f"Esperaba un WARNING mencionando Y; obtuve: {[f['evidence'] for f in result['findings']]}"


def test_only_unidirectional_passes(tools):
    model = {
        "tables": [{"name": "A"}, {"name": "B"}],
        "measures": [],
        "relationships": [
            {"from": "A.x", "to": "B.y", "cross_filter": "oneDirection"},
        ],
        "pages": [],
    }
    rules = [_synthetic_rule("TEST-004", title="Evitar relaciones bidireccionales")]
    result = tools["validate_rules"](model, rules=rules)
    bidir_pass = [f for f in result["findings"]
                  if "bidireccional" in f.get("evidence", "").lower()
                  and ("sin relaciones" in f.get("evidence", "").lower() or "0" in f.get("evidence", ""))
                  and f["status"] == "pass"]
    assert bidir_pass, f"Esperaba al menos un pass para sin relaciones bidireccionales; obtuve: {[(f['status'], f['evidence'][:80]) for f in result['findings']]}"


def test_all_findings_have_required_fields(tools, semantic_model_path, report_path):
    model = _model(tools, semantic_model_path, report_path)
    result = tools["validate_rules"](model)
    assert len(result["findings"]) > 0, "Sin hallazgos automaticos"
    for f in result["findings"]:
        for key in ("rule_id", "title", "category", "severity", "status", "evidence"):
            assert key in f, f"Falta campo {key} en {f.get('rule_id')}"


def test_pending_review_uses_categories(tools):
    model = {
        "tables": [{"name": "A"}],
        "measures": [{"name": "X", "format_string": "0", "expression": "1", "source_file": "a.tmdl"}],
        "relationships": [],
        "pages": [],
    }
    result = tools["validate_rules"](model)
    categories_in_findings = {f["category"] for f in result["findings"]}
    valid = {"modelo_datos", "medidas_dax", "reporte_visual", "rendimiento", "nomenclatura", "seguridad", "documentacion"}
    assert categories_in_findings.issubset(valid), f"Categorias invalidas: {categories_in_findings - valid}"


def test_date_table_check_when_present(tools, semantic_model_path, report_path):
    model = _model(tools, semantic_model_path, report_path)
    rules = [
        _synthetic_rule("TEST-DT", title="Marcar tabla de fechas como Date Table"),
    ]
    result = tools["validate_rules"](model, rules=rules)
    date_findings = [f for f in result["findings"] if "date" in f.get("evidence", "").lower() or "fecha" in f.get("evidence", "").lower()]
    assert date_findings, "Esperaba al menos un hallazgo relacionado a Date Table"