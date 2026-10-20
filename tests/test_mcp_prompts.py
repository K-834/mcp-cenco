from __future__ import annotations

import pytest
from server.mcp_server import mcp

EXPECTED_PROMPTS = {
    "audit_powerbi_report",
    "design_powerbi_dashboard",
    "optimize_dax_expression",
    "create_pbir_page",
    "plan_dashboard_from_mockup",
}


def test_all_expected_prompts_registered():
    registered = set(mcp._prompt_manager._prompts.keys())
    assert EXPECTED_PROMPTS.issubset(registered), (
        f"Faltan prompts: {EXPECTED_PROMPTS - registered}"
    )


def test_audit_prompt_renders_content():
    prompt = mcp._prompt_manager._prompts["audit_powerbi_report"]
    res = prompt.fn(pbip_path="proyectos/test.pbip")
    assert "proyectos/test.pbip" in res
    assert "detect_format" in res
    assert "validate_rules" in res


def test_design_prompt_renders_content():
    prompt = mcp._prompt_manager._prompts["design_powerbi_dashboard"]
    res = prompt.fn(pbip_path="proyectos/test.pbip", goal="Ventas mensuales", target_audience="Directorio")
    assert "Ventas mensuales" in res
    assert "Directorio" in res
    assert "1280x720" in res


def test_optimize_dax_prompt_renders_content():
    prompt = mcp._prompt_manager._prompts["optimize_dax_expression"]
    res = prompt.fn(dax_code="Total = [A] / [B]")
    assert "Total = [A] / [B]" in res
    assert "fix_dax" in res


def test_create_pbir_page_prompt_renders_content():
    prompt = mcp._prompt_manager._prompts["create_pbir_page"]
    res = prompt.fn(pbip_path="proyectos/test.pbip", page_display_name="Resumen")
    assert "Resumen" in res
    assert "write_pbir_layout" in res


def test_plan_dashboard_from_mockup_prompt_renders_content():
    prompt = mcp._prompt_manager._prompts["plan_dashboard_from_mockup"]
    res = prompt.fn(
        mockup_description="Mockup con 3 tarjetas de KPI arriba y un gráfico de líneas abajo",
        pbip_path="proyectos/ventas.pbip",
        target_audience="Gerencia",
    )
    assert "Mockup con 3 tarjetas de KPI" in res
    assert "proyectos/ventas.pbip" in res
    assert "DISCREPANCIAS" in res
    assert "write_dax_measure" in res
    assert "write_pbir_layout" in res

