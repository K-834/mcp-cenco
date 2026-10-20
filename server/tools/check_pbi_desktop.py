from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def get_running_pbi_desktop_instances() -> list[dict]:
    """Obtiene la lista de procesos de Power BI Desktop y sus títulos de ventana."""
    ps_script = """
    $ErrorActionPreference = 'SilentlyContinue'
    $procs = Get-Process -Name PBIDesktop -ErrorAction SilentlyContinue
    if (-not $procs) {
        Write-Output "[]"
        exit 0
    }
    $list = @()
    foreach ($p in $procs) {
        $list += [pscustomobject]@{
            pid = $p.Id
            process_name = $p.ProcessName
            window_title = $p.MainWindowTitle
            memory_mb = [math]::Round($p.WorkingSet64 / 1MB, 1)
        }
    }
    $list | ConvertTo-Json -Compress
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = res.stdout.strip()
        if not output or output == "[]":
            return []
        parsed = json.loads(output)
        if isinstance(parsed, dict):
            return [parsed]
        return list(parsed)
    except Exception:
        return []


def get_active_as_ports() -> list[dict]:
    """Busca los puertos TCP locales de Analysis Services creados por Power BI Desktop."""
    workspaces_dir = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft"
        / "Power BI Desktop"
        / "AnalysisServicesWorkspaces"
    )
    if not workspaces_dir.exists():
        return []

    results = []
    for port_file in workspaces_dir.glob("*/Data/msmdsrv.port.txt"):
        port = None
        for enc in ("utf-16le", "utf-8", "ascii"):
            try:
                text = port_file.read_text(encoding=enc).strip()
                # Filtrar caracteres nulos o no dígitos
                digits = "".join(ch for ch in text if ch.isdigit())
                if digits:
                    port = int(digits)
                    break
            except Exception:
                continue

        if port:
            results.append({
                "port": port,
                "workspace": port_file.parent.parent.name,
                "port_file": str(port_file),
            })
    return results


def check_desktop_status(pbip_path: str | None = None) -> dict:
    """Verifica si Power BI Desktop está corriendo y evalúa riesgos de conflicto en disco."""
    desktop_instances = get_running_pbi_desktop_instances()
    as_ports = get_active_as_ports()

    is_running = len(desktop_instances) > 0
    project_match = None
    warning = None

    target_name = ""
    if pbip_path:
        p = Path(pbip_path)
        if p.suffix.lower() in (".pbip", ".pbix", ".report", ".semanticmodel"):
            target_name = p.stem
        else:
            target_name = p.stem if p.is_file() else p.name

    if is_running:
        if target_name:
            for inst in desktop_instances:
                title = inst.get("window_title", "")
                if target_name.lower() in title.lower():
                    project_match = inst
                    break

        if project_match:
            warning = (
                f"ALERTA CRÍTICA: Power BI Desktop tiene este proyecto abierto ('{project_match.get('window_title')}'). "
                "Power BI Desktop NO recarga automáticamente cambios realizados en disco. "
                "Si guardas en Desktop después de que un agente o script modifique archivos TMDL o PBIR, "
                "Power BI Desktop SOBREESCRIBIRÁ los cambios de disco perdiéndose el trabajo. "
                "RECOMENDACIÓN: Guarda y cierra Desktop antes de aplicar cambios estructurales en disco, "
                "o descarta cambios en Desktop antes de reabrir."
            )
        else:
            warning = (
                "Power BI Desktop está ejecutándose. Si vas a modificar este modelo en disco, "
                "asegúrate de que no sea el mismo archivo que Desktop tiene abierto para evitar que pise los cambios."
            )

    return {
        "desktop_running": is_running,
        "instance_count": len(desktop_instances),
        "instances": desktop_instances,
        "active_ports": as_ports,
        "target_project": target_name,
        "matching_instance": project_match,
        "risk_warning": warning,
        "safe_to_edit_disk": not is_running or project_match is None,
    }


def register(mcp) -> None:
    @mcp.tool()
    def check_pbi_desktop_status(pbip_path: str | None = None) -> dict:
        """Detecta si Power BI Desktop está abierto, qué reportes tiene cargados y puertos de Analysis Services activos.
        
        Permite evitar la fricción 'Desktop pisa el disco' (cuando Desktop sobrescribe
        cambios realizados por agentes en TMDL/PBIR) y provee los puertos para 'query_dax'.

        Args:
            pbip_path: Ruta opcional al proyecto .pbip para verificar si Desktop lo tiene abierto.

        Returns:
            Dict con estado de Desktop, instancias activas, puertos disponibles y advertencias de seguridad.
        """
        return check_desktop_status(pbip_path=pbip_path)
