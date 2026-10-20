from __future__ import annotations

import re

from server.mcp_server import mcp


EXPECTED_TOOLS = {
    "detect_format",
    "read_pbip",
    "validate_rules",
    "generate_design",
    "generate_pbip_docx",
    "check_pbi_desktop_status",
    "query_dax",
    "verify_and_fix_pbip_encoding",
    "disable_auto_date_time",
    "write_dax_measure",
    "write_tmdl_relationship",
}
EXPECTED_RESOURCES = {
    "rules://best-practices",
    "power-bi://reference",
    "html-content://reference",
    "usage://getting-started",
}


def test_all_expected_tools_registered():
    registered = set(mcp._tool_manager._tools.keys())
    assert EXPECTED_TOOLS.issubset(registered), (
        f"Faltan tools: {EXPECTED_TOOLS - registered}"
    )


def test_all_expected_resources_registered():
    registered = set(mcp._resource_manager._resources.keys())
    assert EXPECTED_RESOURCES.issubset(registered), (
        f"Faltan resources: {EXPECTED_RESOURCES - registered}"
    )


def test_rules_resource_returns_valid_json():
    resource = mcp._resource_manager._resources["rules://best-practices"]
    payload = resource.fn()
    data = json.loads(payload)
    assert "rules" in data
    assert isinstance(data["rules"], list)
    assert len(data["rules"]) > 0


def test_power_bi_reference_resource_returns_skill_content():
    resource = mcp._resource_manager._resources["power-bi://reference"]
    payload = resource.fn()
    assert "Power BI" in payload
    assert "PBIP" in payload or "PBIR" in payload or "TMDL" in payload
    frontmatter_match = re.match(r"---\s*\n(.*?)\n---", payload, re.DOTALL)
    assert frontmatter_match, "El skill debe tener frontmatter YAML"
    fm = frontmatter_match.group(1)
    assert "name:" in fm
    assert "description:" in fm


def test_html_content_knowledge_in_merged_skill():
    """El contenido de HTML Content ahora vive en el skill fusionado (power-bi-pbip)."""
    payload = mcp._resource_manager._resources["power-bi://reference"].fn()
    assert "HTML Content" in payload, "El skill fusionado debe cubrir HTML Content"
    assert "sanitiz" in payload.lower(), "Debe tener la guia de sanitizacion HTML"
    assert "coacervo" in payload, "Debe mencionar el visual coacervo/Daniel Marsh-Patrick"


def test_agent_guide_resource_returns_operational_doc():
    resource = mcp._resource_manager._resources["usage://getting-started"]
    payload = resource.fn()
    assert "detect_format" in payload
    assert "read_pbip" in payload
    assert "validate_rules" in payload
    assert "generate_design" in payload
    assert "usage://getting-started" in payload or "Flujo" in payload


def test_load_rules_returns_cache():
    from server.mcp_server import load_rules

    first = load_rules()
    second = load_rules()
    assert first is second


import json
