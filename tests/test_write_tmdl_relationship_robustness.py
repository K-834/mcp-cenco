from __future__ import annotations

import re
from pathlib import Path
from server.tools.encoding_helper import has_utf8_bom, read_text_utf8
from server.tools.write_tmdl_model import add_or_update_relationship, set_time_intelligence_disabled


def test_add_relationship_generates_valid_tmdl_syntax(tmp_path: Path):
    rel_file = tmp_path / "relationships.tmdl"

    res = add_or_update_relationship(
        rel_file=rel_file,
        from_table="fact_bonus_canje_2026",
        from_column="fecha_real",
        to_table="dim_calendario",
        to_column="Date",
        cardinality="oneToMany",
        cross_filtering="oneWay",
        join_on_date_behavior="datePartOnly",
    )

    assert res["action"] in ("created", "appended")
    content = read_text_utf8(rel_file)

    # NO debe tener corchetes []
    assert "[" not in content and "]" not in content
    assert "fromColumn: fact_bonus_canje_2026.fecha_real" in content
    assert "toColumn: dim_calendario.Date" in content
    assert "joinOnDateBehavior: datePartOnly" in content
    assert re.search(r"relationship [a-f0-9\-]+", content)
    assert not has_utf8_bom(rel_file)


def test_update_existing_relationship(tmp_path: Path):
    rel_file = tmp_path / "relationships.tmdl"
    existing = """relationship 12345678-abcd-ef01-2345-6789abcdef01
\tfromColumn: fact_ventas.fecha
\ttoColumn: dim_fecha.fecha
\tcardinality: oneToMany
"""
    rel_file.write_text(existing, encoding="utf-8")

    res = add_or_update_relationship(
        rel_file=rel_file,
        from_table="fact_ventas",
        from_column="fecha",
        to_table="dim_fecha",
        to_column="fecha",
        join_on_date_behavior="datePartOnly",
    )

    assert res["action"] == "updated"
    assert res["relationship_id"] == "12345678-abcd-ef01-2345-6789abcdef01"
    content = read_text_utf8(rel_file)
    assert "joinOnDateBehavior: datePartOnly" in content


def test_disable_auto_date_time(tmp_path: Path):
    model_file = tmp_path / "model.tmdl"
    model_content = """model Model
\tculture: es-ES
\tdataAccessOptions
\t\tlegacyRedirects

ref table Ventas
"""
    model_file.write_text(model_content, encoding="utf-8")

    res = set_time_intelligence_disabled(model_file)
    assert res["success"] is True

    content = read_text_utf8(model_file)
    assert "annotation __PBI_TimeIntelligenceEnabled = 0" in content
    assert not has_utf8_bom(model_file)
