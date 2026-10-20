from __future__ import annotations

from pathlib import Path


def test_detect_format_missing_path(tools):
    result = tools["detect_format"]("C:/esta/ruta/no/existe")
    assert result["ok"] is False
    assert result["format"] == "missing"


def test_detect_format_pbix_extension(tools, tmp_path: Path):
    fake_pbix = tmp_path / "modelo.pbix"
    fake_pbix.write_bytes(b"fake content")
    result = tools["detect_format"](str(fake_pbix))
    assert result["ok"] is False
    assert result["format"] == "pbix"
    assert "Power BI Desktop" in result["message"]
    assert ".pbip" in result["message"]


def test_detect_format_unknown_extension(tools, tmp_path: Path):
    fake = tmp_path / "archivo.txt"
    fake.write_text("hola")
    result = tools["detect_format"](str(fake))
    assert result["ok"] is False
    assert result["format"] == "unknown"


def test_detect_format_valid_pbip_folder(tools, project_path):
    result = tools["detect_format"](project_path)
    assert result["ok"] is True
    assert result["format"] == "pbip"
    assert "SemanticModel" in result["semantic_model"]
    assert "Report" in result["report"]
