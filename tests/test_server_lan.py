from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from server.mcp_server import main


def test_server_lan_default_stdio():
    with patch("sys.argv", ["mcp_server.py"]), patch("server.mcp_server.mcp.run") as mock_run:
        main()
        mock_run.assert_called_once_with(transport="stdio")


def test_server_lan_custom_args():
    with patch(
        "sys.argv",
        [
            "mcp_server.py",
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "--path",
            "/custom-mcp",
        ],
    ), patch("server.mcp_server.mcp.run") as mock_run:
        main()
        mock_run.assert_called_once_with(
            transport="streamable-http",
            host="0.0.0.0",
            port=8080,
            streamable_http_path="/custom-mcp",
        )


def test_server_lan_env_vars(monkeypatch):
    monkeypatch.setenv("POWERBI_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("POWERBI_MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("POWERBI_MCP_PORT", "9000")
    monkeypatch.setenv("POWERBI_MCP_PATH", "/mcp-lan")

    with patch("sys.argv", ["mcp_server.py"]), patch("server.mcp_server.mcp.run") as mock_run:
        main()
        mock_run.assert_called_once_with(
            transport="streamable-http",
            host="127.0.0.1",
            port=9000,
            streamable_http_path="/mcp-lan",
        )



def test_clients_lan_json_exists():
    path = Path(__file__).parent.parent / "clients" / "lan.mcp.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "powerbi-mcp-lan" in data["mcpServers"]
    assert "url" in data["mcpServers"]["powerbi-mcp-lan"]
