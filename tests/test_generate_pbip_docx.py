from __future__ import annotations

from pathlib import Path
import docx

from server.extractors.tmdl_extractor import parse_complete_pbip
from server.generators.docx_report_generator import generate_pbip_documentation_docx
from server.tools.generate_pbip_docx import _resolve_paths


def test_resolve_paths_from_semantic_model(semantic_model_path, report_path):
    sm, rep, err = _resolve_paths(semantic_model_path, report_path)
    assert sm.exists()
    assert rep.exists()
    assert err is None


def test_extract_complete_pbip_metadata(semantic_model_path, report_path):
    sm = Path(semantic_model_path)
    rep = Path(report_path)
    data = parse_complete_pbip(sm, rep)

    assert "tables" in data
    assert "measures" in data
    assert "relationships" in data
    assert "roles" in data
    assert "pages" in data

    # Verify tables have columns and partitions
    assert len(data["tables"]) > 0
    for tbl in data["tables"]:
        assert "name" in tbl
        assert "columns" in tbl
        assert "partitions" in tbl

    # Find table with SQL or Redshift
    redshift_tables = [
        t for t in data["tables"]
        if any(p.get("connector") == "AmazonRedshift.Database" for p in t.get("partitions", []))
    ]
    assert len(redshift_tables) >= 1
    # Check that SQL query was extracted
    p0 = redshift_tables[0]["partitions"][0]
    assert p0.get("native_query") is not None
    assert "select" in p0["native_query"].lower()


def test_generate_pbip_docx_creates_functional_and_technical_doc(semantic_model_path, report_path, tmp_path):
    sm = Path(semantic_model_path)
    rep = Path(report_path)
    data = parse_complete_pbip(sm, rep)
    out_docx = tmp_path / "test_report_full.docx"

    audit_findings = [
        {"rule_id": "REG01", "severity": "warning", "category": "Modelo", "message": "Relacion bidireccional detectada"}
    ]

    result_path = generate_pbip_documentation_docx(
        model_data=data,
        output_path=out_docx,
        audit_findings=audit_findings,
        include_functional=True,
    )
    assert result_path.exists()
    assert result_path.stat().st_size > 5000

    # Open with docx to verify functional and technical structure
    doc = docx.Document(str(result_path))
    headings = [p.text for p in doc.paragraphs]
    
    # Verify Functional Headings
    assert any("DOCUMENTACIÓN FUNCIONAL" in h for h in headings)
    assert any("Objetivos y Alcance" in h for h in headings)
    assert any("Diccionario Funcional de Indicadores (KPIs)" in h for h in headings)
    assert any("Guía de Navegación y Uso por Pantalla" in h for h in headings)
    assert any("Reglas de Negocio y Gobierno" in h for h in headings)

    # Verify Technical Headings
    assert any("ESPECIFICACIÓN TÉCNICA" in h for h in headings)
    assert any("Arquitectura y Orígenes de Datos" in h for h in headings)
    assert any("Diccionario Técnico de Datos" in h for h in headings)
    assert any("Catálogo Técnico de Medidas DAX" in h for h in headings)
    assert any("Matriz de Relaciones del Modelo" in h for h in headings)


def test_mcp_tool_generate_pbip_docx(tools, semantic_model_path, report_path, tmp_path):
    assert "generate_pbip_docx" in tools
    out_docx = tmp_path / "mcp_tool_output.docx"

    res = tools["generate_pbip_docx"](
        semantic_model_path=semantic_model_path,
        report_path=report_path,
        output_path=str(out_docx),
        include_audit=True,
        include_functional=True,
    )

    assert res["status"] == "success"
    assert "output_file" in res
    assert res.get("has_functional_docs") is True
    assert res["tables_count"] > 0
    assert res["measures_count"] > 0
    assert res["data_sources_count"] > 0
    assert out_docx.exists()
