from __future__ import annotations

import uuid
from pathlib import Path
from server.tools.encoding_helper import has_utf8_bom, read_text_utf8
from server.tools.write_dax_measure import add_or_update_measure_in_tmdl


SAMPLE_TABLE_TMDL = """table Ventas
\tlineageTag: a1b2c3d4-e5f6-7890-abcd-ef1234567890

\tmeasure 'Ventas Totales' = SUM(Ventas[Monto])
\t\tformatString: $#,##0.00
\t\tdisplayFolder: KPIs
\t\tlineageTag: 11111111-2222-3333-4444-555555555555

\tcolumn ID
\t\tdataType: int64
\t\tlineageTag: col-id-123

\tpartition Ventas = m
\t\tmode: import
\t\tsource = ...
"""


def test_add_measure_inserts_before_column_and_partition(tmp_path: Path):
    table_file = tmp_path / "Ventas.tmdl"
    table_file.write_text(SAMPLE_TABLE_TMDL, encoding="utf-8")

    res = add_or_update_measure_in_tmdl(
        tmdl_path=table_file,
        measure_name="Margen",
        dax_code="DIVIDE([Ventas Totales] - [Costo], [Ventas Totales], 0)",
        format_string="0.0%",
        display_folder="KPIs",
    )

    assert res["success"] is True
    assert res["action"] == "added"

    content = read_text_utf8(table_file)

    # La medida debe estar antes de column y partition
    assert content.index("measure 'Margen'") < content.index("column ID")
    assert content.index("measure 'Margen'") < content.index("partition Ventas")
    assert "\t\tformatString: 0.0%" in content
    assert "\t\tlineageTag:" in content
    assert not has_utf8_bom(table_file)


def test_update_existing_measure_preserves_lineage_tag(tmp_path: Path):
    table_file = tmp_path / "Ventas.tmdl"
    table_file.write_text(SAMPLE_TABLE_TMDL, encoding="utf-8")

    res = add_or_update_measure_in_tmdl(
        tmdl_path=table_file,
        measure_name="Ventas Totales",
        dax_code="SUM(Ventas[Monto_Ajustado])",
        format_string="$#,##0.00",
    )

    assert res["success"] is True
    assert res["action"] == "updated"

    content = read_text_utf8(table_file)
    # Debe preservar el lineageTag original
    assert "lineageTag: 11111111-2222-3333-4444-555555555555" in content
    assert "SUM(Ventas[Monto_Ajustado])" in content
    # Columnas y partición no deben haberse borrado
    assert "column ID" in content
    assert "partition Ventas" in content


def test_auto_refactor_false_preserves_exact_dax(tmp_path: Path):
    table_file = tmp_path / "Ventas.tmdl"
    table_file.write_text(SAMPLE_TABLE_TMDL, encoding="utf-8")

    complex_dax = """VAR _A = 1
VAR _B = 2
RETURN
    _A + _B"""

    res = add_or_update_measure_in_tmdl(
        tmdl_path=table_file,
        measure_name="Calculo Complejo",
        dax_code=complex_dax,
        auto_refactor_dax=False,
    )

    assert res["success"] is True
    content = read_text_utf8(table_file)
    assert "VAR _A = 1" in content
    assert "_Resultado" not in content  # No debió envolver artificialmente en _Resultado


def test_add_measure_to_table_without_existing_measures(tmp_path: Path):
    tmdl = """table Clientes
\tlineageTag: abc-123

\tcolumn Codigo
\t\tdataType: string

\tpartition Clientes = m
\t\tsource = ...
"""
    table_file = tmp_path / "Clientes.tmdl"
    table_file.write_text(tmdl, encoding="utf-8")

    res = add_or_update_measure_in_tmdl(
        tmdl_path=table_file,
        measure_name="Total Clientes",
        dax_code="DISTINCTCOUNT(Clientes[Codigo])",
    )

    assert res["success"] is True
    content = read_text_utf8(table_file)
    assert content.index("measure 'Total Clientes'") < content.index("column Codigo")
    assert content.index("measure 'Total Clientes'") < content.index("partition Clientes")
