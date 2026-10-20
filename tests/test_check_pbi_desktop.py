from __future__ import annotations

from unittest.mock import patch
from server.tools.check_pbi_desktop import check_desktop_status


def test_check_desktop_status_when_not_running():
    with patch("server.tools.check_pbi_desktop.get_running_pbi_desktop_instances", return_value=[]), \
         patch("server.tools.check_pbi_desktop.get_active_as_ports", return_value=[]):
        status = check_desktop_status("C:/Proyectos/Ventas.pbip")
        assert status["desktop_running"] is False
        assert status["safe_to_edit_disk"] is True
        assert status["risk_warning"] is None


def test_check_desktop_status_when_matching_instance_running():
    mock_instances = [
        {
            "pid": 1234,
            "process_name": "PBIDesktop",
            "window_title": "Dashboard Puntos Bonus - Canje - Power BI Desktop",
            "memory_mb": 450.0,
        }
    ]
    mock_ports = [{"port": 54321, "workspace": "AnalysisServicesWorkspace_abc"}]

    with patch("server.tools.check_pbi_desktop.get_running_pbi_desktop_instances", return_value=mock_instances), \
         patch("server.tools.check_pbi_desktop.get_active_as_ports", return_value=mock_ports):
        status = check_desktop_status("Dashboard Puntos Bonus - Canje.pbip")
        assert status["desktop_running"] is True
        assert status["safe_to_edit_disk"] is False
        assert status["matching_instance"] is not None
        assert "SOBREESCRIBIRÁ los cambios de disco" in status["risk_warning"]
