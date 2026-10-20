from __future__ import annotations

from pathlib import Path
from server.converters.pbix_converter import (
    convert_pbix_to_pbip,
    get_manual_conversion_instructions,
    find_pbi_desktop,
)


def test_find_pbi_desktop():
    # Verify find_pbi_desktop executes without exception and returns Path or None
    exe = find_pbi_desktop()
    if exe is not None:
        assert isinstance(exe, Path)
        assert exe.exists()


def test_get_manual_conversion_instructions(tmp_path: Path):
    fake_pbix = tmp_path / "MiReporte.pbix"
    target_dir = tmp_path / "proyectos" / "MiReporte"
    instructions = get_manual_conversion_instructions(fake_pbix, target_dir)

    assert "INSTRUCCIONES DE CONVERSIÓN MANUAL" in instructions
    assert "MiReporte.pbix" in instructions
    assert "Formato de proyecto de Power BI (*.pbip)" in instructions
    assert "MiReporte.SemanticModel" in instructions
    assert "MiReporte.Report" in instructions


def test_convert_pbix_missing_file():
    res = convert_pbix_to_pbip("C:/no/existe/reporte.pbix")
    assert res["ok"] is False
    assert res["status"] == "error"
    assert "No se encontró el archivo" in res["message"]


def test_convert_pbix_already_converted(tmp_path: Path):
    # Simulate an already converted project in target_dir
    fake_pbix = tmp_path / "Ventas.pbix"
    fake_pbix.write_bytes(b"fake-pbix-data")

    target_dir = tmp_path / "proyectos" / "Ventas"
    sm_dir = target_dir / "Ventas.SemanticModel"
    (sm_dir / "definition").mkdir(parents=True, exist_ok=True)
    (target_dir / "Ventas.Report").mkdir(parents=True, exist_ok=True)

    res = convert_pbix_to_pbip(fake_pbix, output_dir=target_dir)
    assert res["ok"] is True
    assert res["status"] == "already_converted"
    assert "SemanticModel" in res["semantic_model"]


def test_convert_pbix_fallback_manual(tmp_path: Path):
    fake_pbix = tmp_path / "Finanzas.pbix"
    fake_pbix.write_bytes(b"fake-pbix-data")
    target_dir = tmp_path / "out" / "Finanzas"

    # Running with short timeout in non-interactive / test mode triggers clean fallback
    res = convert_pbix_to_pbip(fake_pbix, output_dir=target_dir, timeout_seconds=1)
    assert res["status"] == "manual_action_required"
    assert "instructions" in res
    assert "Finanzas" in res["instructions"]
    assert Path(res["target_folder"]).exists()


def test_mcp_tool_convert_pbix_to_pbip(tools, tmp_path: Path):
    assert "convert_pbix_to_pbip" in tools
    fake_pbix = tmp_path / "Marketing.pbix"
    fake_pbix.write_bytes(b"marketing-pbix")

    res = tools["convert_pbix_to_pbip"](
        pbix_path=str(fake_pbix),
        output_dir=str(tmp_path / "proyectos" / "Marketing"),
        timeout_seconds=1,
    )
    assert res["status"] in ("manual_action_required", "success", "already_converted")
    if res["status"] == "manual_action_required":
        assert "instructions" in res
