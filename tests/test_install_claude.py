from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.install_claude as install_claude  # noqa: E402


def test_server_entry_has_uv():
    entry = install_claude._server_entry()
    assert entry["command"] == "uv"
    assert "--project" in entry["args"]
    # Antes: `python server/mcp_server.py` (path relativo, requeria cwd correcto).
    # Ahora: `powerbi-mcp` (entry point de pyproject.toml, no depende del cwd).
    assert entry["args"][-1] == "powerbi-mcp"
    assert "python" not in entry["args"]
    assert not any("server/mcp_server.py" in a for a in entry["args"])


def test_server_entry_for_code_includes_env():
    entry = install_claude._server_entry_code()
    assert "env" in entry
    assert entry["env"] == {}


def test_claude_desktop_config_path_is_resolved():
    path = install_claude._claude_desktop_config_path()
    if sys.platform.startswith("win"):
        assert "AppData" in str(path) or "APPDATA" in str(path) or str(path).endswith("claude_desktop_config.json")
    assert path.name == "claude_desktop_config.json"


def test_write_then_read_json_roundtrip(tmp_path: Path):
    target = tmp_path / "sub" / "config.json"
    payload = {"mcpServers": {"powerbi-mcp": install_claude._server_entry()}}
    install_claude._write_json(target, payload)
    loaded = install_claude._read_json(target)
    assert loaded["mcpServers"]["powerbi-mcp"]["command"] == "uv"


def test_read_json_returns_empty_for_missing_file(tmp_path: Path):
    fake = tmp_path / "nope.json"
    assert install_claude._read_json(fake) == {}


def test_read_json_handles_corrupt_file(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    result = install_claude._read_json(bad)
    assert result == {}
    assert (bad.parent / "bad.json.bak").exists()


def test_uninstall_removes_powerbi_from_existing_config(tmp_path: Path):
    target = tmp_path / "config.json"
    install_claude._write_json(target, {
        "mcpServers": {
            "powerbi-mcp": install_claude._server_entry(),
            "other": {"command": "x", "args": []},
        }
    })
    config = install_claude._read_json(target)
    del config["mcpServers"]["powerbi-mcp"]
    install_claude._write_json(target, config)
    loaded = install_claude._read_json(target)
    assert "powerbi-mcp" not in loaded["mcpServers"]
    assert "other" in loaded["mcpServers"]


def test_installed_entry_matches_clients_file():
    """El bloque que escribe install_claude debe ser el mismo que clients/claude_desktop.mcp.json."""
    installed = install_claude._server_entry()
    clients_path = Path(__file__).resolve().parent.parent / "clients" / "claude_desktop.mcp.json"
    clients_data = json.loads(clients_path.read_text(encoding="utf-8"))
    clients_entry = clients_data["mcpServers"]["powerbi-mcp"]
    assert installed["command"] == clients_entry["command"]
    assert installed["args"] == clients_entry["args"]