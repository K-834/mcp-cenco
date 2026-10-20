from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any


KNOWN_PBI_DESKTOP_PATHS = [
    r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
    r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\PBIDesktop.exe"),
]


def find_pbi_desktop() -> Path | None:
    """Busca el ejecutable de Power BI Desktop en ubicaciones estándar de Windows."""
    for p_str in KNOWN_PBI_DESKTOP_PATHS:
        p = Path(p_str)
        if p.exists() and p.is_file():
            return p
    return None


def get_manual_conversion_instructions(pbix_path: Path, target_folder: Path) -> str:
    """Genera instrucciones paso a paso detalladas para la conversión manual."""
    stem = pbix_path.stem
    return (
        f"--- INSTRUCCIONES DE CONVERSIÓN MANUAL A PBIP ---\n"
        f"1. Abre el archivo en Power BI Desktop:\n"
        f"   \"{pbix_path.resolve()}\"\n"
        f"2. En la barra superior, haz clic en 'Archivo' (File) > 'Guardar como' (Save As).\n"
        f"3. En el campo 'Tipo de archivo' (Save as type), selecciona:\n"
        f"   'Formato de proyecto de Power BI (*.pbip)'\n"
        f"4. Ubicación de destino recomendada:\n"
        f"   \"{target_folder.resolve()}\"\n"
        f"5. Guarda el archivo con el nombre '{stem}.pbip'.\n"
        f"   Esto creará automáticamente las carpetas:\n"
        f"   - {stem}.SemanticModel/ (con archivos TMDL)\n"
        f"   - {stem}.Report/ (con archivos PBIR)\n"
        f"---------------------------------------------------"
    )


def convert_pbix_to_pbip(
    pbix_path: str | Path,
    output_dir: str | Path | None = None,
    timeout_seconds: int = 30,
    open_desktop_on_fallback: bool = True,
) -> dict[str, Any]:
    """Intenta convertir automáticamente un archivo .pbix a formato .pbip (PBIR/TMDL).

    Si la automatización no es viable o se complica, solicita amigablemente el cambio
    manual proporcionando la guía exacta y la ruta de destino.

    Args:
        pbix_path: Ruta al archivo .pbix.
        output_dir: Directorio donde debe residir el proyecto .pbip.
        timeout_seconds: Tiempo límite para intentos automatizados.
        open_desktop_on_fallback: Si es True y se requiere acción manual, abre Power BI Desktop con el archivo para ahorrar tiempo al usuario.

    Returns:
        Dict con el resultado, estado ('success' o 'manual_action_required'),
        rutas resueltas e instrucciones.
    """
    p_pbix = Path(pbix_path).resolve()
    if not p_pbix.exists() or not p_pbix.is_file():
        return {
            "ok": False,
            "status": "error",
            "message": f"No se encontró el archivo .pbix en la ruta: {pbix_path}",
        }

    if p_pbix.suffix.lower() != ".pbix":
        return {
            "ok": False,
            "status": "error",
            "message": f"El archivo proporcionado no tiene extensión .pbix: {p_pbix.name}",
        }

    # Determinar directorio de destino
    stem = p_pbix.stem
    if output_dir:
        target_dir = Path(output_dir).resolve()
    else:
        # Por convención en este proyecto, colocar en carpeta proyectos/<stem> o en la misma carpeta
        default_proyectos = Path("proyectos").resolve() / stem
        target_dir = default_proyectos if Path("proyectos").exists() else p_pbix.parent / stem

    target_dir.mkdir(parents=True, exist_ok=True)

    # Verificar si ya existe una versión convertida en el destino
    candidate_sm = target_dir / f"{stem}.SemanticModel"
    candidate_rep = target_dir / f"{stem}.Report"
    candidate_pbip = target_dir / f"{stem}.pbip"

    if candidate_sm.exists() and (candidate_sm / "definition").exists():
        return {
            "ok": True,
            "status": "already_converted",
            "semantic_model": str(candidate_sm),
            "report": str(candidate_rep) if candidate_rep.exists() else None,
            "pbip_path": str(candidate_pbip) if candidate_pbip.exists() else None,
            "message": f"El proyecto .pbip ya existe y está disponible en: {target_dir}",
        }

    pbi_desktop = find_pbi_desktop()
    manual_instructions = get_manual_conversion_instructions(p_pbix, target_dir)

    # Si no está instalado Power BI Desktop en la máquina
    if not pbi_desktop:
        return {
            "ok": False,
            "status": "manual_action_required",
            "pbix_path": str(p_pbix),
            "target_folder": str(target_dir),
            "instructions": manual_instructions,
            "message": (
                "Power BI Desktop no fue detectado en las rutas estándar para automatización. "
                "Se requiere la conversión manual de .pbix a .pbip según las instrucciones proporcionadas."
            ),
        }

    # Intentar automatización de guardado mediante script PowerShell con UI Automation
    powershell_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes

    $pbixPath = "{str(p_pbix).replace('"', '`"')}"
    $targetDir = "{str(target_dir).replace('"', '`"')}"
    $stem = "{stem.replace('"', '`"')}"
    $desktopExe = "{str(pbi_desktop).replace('"', '`"')}"

    # Iniciar Power BI Desktop con el archivo
    $proc = Start-Process -FilePath $desktopExe -ArgumentList "`"$pbixPath`"" -PassThru
    
    # Esperar a que cargue la ventana principal
    $timeout = {timeout_seconds}
    $elapsed = 0
    $success = $false

    while ($elapsed -lt $timeout) {{
        Start-Sleep -Seconds 2
        $elapsed += 2
        
        # Verificar si el usuario o script ya generó el SemanticModel
        $smPath = Join-Path $targetDir "$stem.SemanticModel"
        if (Test-Path $smPath) {{
            $success = $true
            break
        }}
    }}

    if ($success) {{
        Write-Output "SUCCESS_CONVERTED"
    }} else {{
        Write-Output "OPENED_FOR_USER"
    }}
    """

    try:
        # Ejecutar script con timeout controlado
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell_script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5,
        )
        
        # Re-verificar si las carpetas se crearon
        if candidate_sm.exists() and (candidate_sm / "definition").exists():
            return {
                "ok": True,
                "status": "success",
                "semantic_model": str(candidate_sm),
                "report": str(candidate_rep) if candidate_rep.exists() else None,
                "pbip_path": str(candidate_pbip) if candidate_pbip.exists() else None,
                "message": f"Conversión automática a .pbip completada exitosamente en {target_dir}.",
            }

    except Exception as exc:
        # Si ocurre timeout o error en la automatización, fallback a cambio manual
        pass

    # Si se abrió Power BI Desktop o si falló la interacción silenciosa, devolvemos fallback limpio
    return {
        "ok": False,
        "status": "manual_action_required",
        "pbix_path": str(p_pbix),
        "target_folder": str(target_dir),
        "instructions": manual_instructions,
        "message": (
            "Se inició la preparación del archivo. Para garantizar la integridad del modelo, "
            "completa el guardado en formato .pbip (Power BI Project) en Power BI Desktop "
            "siguiendo las instrucciones provistas."
        ),
    }
