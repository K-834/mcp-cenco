from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from rules.compile_rules import (
    DEFAULT_INPUT_DIR,
    assign_ids,
    discover_document,
)


def test_discover_document_finds_the_pdf():
    if not DEFAULT_INPUT_DIR.exists():
        return
    discovered = discover_document(DEFAULT_INPUT_DIR)
    assert discovered is not None
    assert discovered.suffix.lower() in {".pdf", ".docx"}


def test_extract_text_reads_the_pdf():
    pdf_path = next(DEFAULT_INPUT_DIR.glob("*.pdf"), None)
    if pdf_path is None:
        return
    from rules.compile_rules import extract_text

    text = extract_text(pdf_path)
    assert len(text) > 1000
    assert "Power BI" in text


def test_assign_ids_uses_source_id_when_present():
    rules = [
        {"title": "a", "_source_id": "BP-005"},
        {"title": "b"},
        {"title": "c"},
    ]
    result = assign_ids(rules)
    assert result[0]["id"] == "BP-005"
    assert result[1]["id"] == "PBICHK-001"
    assert result[2]["id"] == "PBICHK-002"
    assert "_source_id" not in result[0]


def test_assign_ids_sequential_when_no_source_id():
    rules = [{"title": "a"}, {"title": "b"}, {"title": "c"}]
    result = assign_ids(rules)
    assert [r["id"] for r in result] == ["PBICHK-001", "PBICHK-002", "PBICHK-003"]


def test_real_rules_json_validates_against_schema():
    schema = json.loads(Path("rules/schema.json").read_text(encoding="utf-8"))
    payload = json.loads(Path("rules/rules.json").read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def test_rules_json_uses_known_categories():
    rules = json.loads(Path("rules/rules.json").read_text(encoding="utf-8"))["rules"]
    valid = {
        "modelo_datos", "medidas_dax", "reporte_visual",
        "rendimiento", "nomenclatura", "seguridad", "documentacion",
    }
    for r in rules:
        assert r["category"] in valid, f"{r['id']}: categoria invalida {r['category']}"
