from __future__ import annotations

from pathlib import Path
from server.tools.encoding_helper import (
    UTF8_BOM,
    has_utf8_bom,
    read_text_utf8,
    scan_and_fix_pbip_encoding,
    write_text_utf8,
)


def test_bom_detection_and_fix(tmp_path: Path):
    file_with_bom = tmp_path / "table.tmdl"
    file_with_bom.write_bytes(UTF8_BOM + "table Test".encode("utf-8"))

    file_clean = tmp_path / "clean.json"
    file_clean.write_bytes("{\"key\": \"val\"}".encode("utf-8"))

    assert has_utf8_bom(file_with_bom) is True
    assert has_utf8_bom(file_clean) is False

    # Lectura limpia
    assert read_text_utf8(file_with_bom) == "table Test"

    # Escaneo y reparación
    scan_res = scan_and_fix_pbip_encoding(tmp_path, fix=True)
    assert scan_res["success"] is True
    assert scan_res["files_with_bom_count"] == 1
    assert len(scan_res["fixed_files"]) == 1

    # Verificar que ya no tenga BOM
    assert has_utf8_bom(file_with_bom) is False


def test_write_text_utf8_guarantees_no_bom(tmp_path: Path):
    target = tmp_path / "subdir" / "new.tmdl"
    write_text_utf8(target, "measure 'X' = 1\n")

    assert target.exists()
    assert has_utf8_bom(target) is False
    assert target.read_bytes().startswith(b"measure")
