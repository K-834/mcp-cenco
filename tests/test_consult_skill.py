from __future__ import annotations

from server.mcp_server import mcp


def test_consult_skill_registered():
    assert "consult_skill" in mcp._tool_manager._tools


def test_consult_skill_returns_guidance():
    tool = mcp._tool_manager._tools["consult_skill"]
    res = tool.fn(topic="design")
    assert res["ok"] is True
    assert "powerbi-report-design" in res["skill_slug"]
    assert len(res["guidance"]) > 100


def test_consult_skill_audit_topic():
    tool = mcp._tool_manager._tools["consult_skill"]
    res = tool.fn(topic="audit")
    assert res["ok"] is True
    assert "logica-bi-pbip-cenco" in res["skill_slug"]


def test_server_has_instructions():
    assert mcp.instructions
    assert "Power BI" in mcp.instructions
    assert "ACTIVACION AUTOMATICA" in mcp.instructions
