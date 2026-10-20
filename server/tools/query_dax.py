from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from server.tools.check_pbi_desktop import get_active_as_ports, get_running_pbi_desktop_instances


def normalize_dax_query(query: str) -> str:
    """Normaliza una expresión DAX para que sea una consulta EVALUATE ejecutable por VertiPaq."""
    trimmed = query.strip()
    upper = trimmed.upper()

    # Si ya contiene EVALUATE o DEFINE, usar tal cual
    if upper.startswith("EVALUATE") or upper.startswith("DEFINE"):
        return trimmed

    # Si es una expresión tabular típica
    tabular_prefixes = ("VALUES", "DISTINCT", "TOPN", "FILTER", "ALL", "ALLSELECTED", "SUMMARIZE", "CALCULATETABLE", "SELECTCOLUMNS", "ADDCOLUMNS", "UNION", "DATATABLE", "INTERSECT", "EXCEPT")
    for pref in tabular_prefixes:
        if upper.startswith(pref):
            return f"EVALUATE\n{trimmed}"

    # Si parece una tabla directa por comillas o nombre sin corchetes
    if (trimmed.startswith("'") and trimmed.endswith("'")) or ("[" not in trimmed and " " not in trimmed and "(" not in trimmed):
        return f"EVALUATE\n{trimmed}"

    # Si es una expresión escalar (suma, medida, cálculo), envolver en ROW(...)
    return f"EVALUATE\nROW(\"Resultado\", {trimmed})"


def execute_dax_via_adodb(port: int, query: str, max_rows: int = 50, catalog: str | None = None) -> dict:
    """Ejecuta una consulta DAX conectándose por ADODB (MSOLAP) al puerto local de Analysis Services."""
    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        $conn = New-Object -ComObject ADODB.Connection
        $connStr = "Provider=MSOLAP;Data Source=localhost:{port};"
        {"$connStr += 'Initial Catalog=' + " + repr(catalog) + " + ';'" if catalog else ""}
        $conn.Open($connStr)

        $dax = @'
{query}
'@

        $rs = $conn.Execute($dax)
        $cols = @()
        for ($i = 0; $i -lt $rs.Fields.Count; $i++) {{
            $cols += $rs.Fields.Item($i).Name
        }}

        $rows = @()
        $count = 0
        $max = {max_rows}
        while (-not $rs.EOF -and ($max -le 0 -or $count -lt $max)) {{
            $row = [ordered]@{{}}
            foreach ($col in $cols) {{
                $val = $rs.Fields.Item($col).Value
                if ($val -eq $null) {{
                    $row[$col] = $null
                }} elseif ($val -is [System.DateTime]) {{
                    $row[$col] = $val.ToString("yyyy-MM-dd HH:mm:ss")
                }} else {{
                    $row[$col] = $val
                }}
            }}
            $rows += [pscustomobject]$row
            $rs.MoveNext()
            $count++
        }}

        $conn.Close()

        [pscustomobject]@{{
            success = $true
            columns = $cols
            row_count = $rows.Count
            rows = $rows
        }} | ConvertTo-Json -Depth 5 -Compress
    }} catch {{
        [pscustomobject]@{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json -Depth 3 -Compress
    }}
    """

    # Guardar script temporal para evitar problemas de escape en la linea de comandos
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
        f.write(ps_script)
        temp_ps1 = f.name

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", temp_ps1],
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = res.stdout.strip()
        if not stdout:
            return {"success": False, "error": f"PowerShell no retornó salida. Stderr: {res.stderr}"}
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "La consulta DAX excedió el tiempo límite de 30 segundos."}
    except Exception as e:
        return {"success": False, "error": f"Fallo al ejecutar DAX: {str(e)}"}
    finally:
        try:
            Path(temp_ps1).unlink(missing_ok=True)
        except Exception:
            pass


def query_dax_model(
    dax_query: str,
    pbip_path: str | None = None,
    port: int | None = None,
    max_rows: int = 50,
    catalog: str | None = None,
) -> dict:
    """Busca la instancia activa de Power BI Desktop y ejecuta una consulta DAX en vivo."""
    target_port = port

    if not target_port:
        active_ports = get_active_as_ports()
        if not active_ports:
            return {
                "success": False,
                "error": (
                    "No se encontró ninguna instancia activa de Power BI Desktop con Analysis Services local en ejecución. "
                    "Para consultar datos reales en vivo, abre el archivo .pbip en Power BI Desktop primero."
                ),
                "suggestion": "Abre el reporte en Desktop o especifica un puerto explícito si usas una instancia externa.",
            }
        # Si hay un pbip_path, intentar empatar con la instancia
        if len(active_ports) == 1:
            target_port = active_ports[0]["port"]
        else:
            # Seleccionar la primera o la correspondiente
            target_port = active_ports[0]["port"]

    normalized_query = normalize_dax_query(dax_query)
    result = execute_dax_via_adodb(
        port=target_port,
        query=normalized_query,
        max_rows=max_rows,
        catalog=catalog,
    )

    result["target_port"] = target_port
    result["query_executed"] = normalized_query
    return result


def register(mcp) -> None:
    @mcp.tool()
    def query_dax(
        dax_query: str,
        pbip_path: str | None = None,
        port: int | None = None,
        max_rows: int = 50,
        catalog: str | None = None,
    ) -> dict:
        """Ejecuta una consulta DAX en vivo contra el motor VertiPaq local de Power BI Desktop.
        
        Permite consultar datos reales (rango de fechas, valores únicos, distribución de columnas,
        resultados de medidas calculadas) sin necesidad de pedir capturas manuales de pantalla al usuario.
        Requiere que el reporte esté abierto en Power BI Desktop.

        Args:
            dax_query: Expresión o consulta DAX (ej. "EVALUATE TOPN(10, 'fact_bonus_canje_2026')",
                       "VALUES('fact_bonus_canje_2026'[nombre_promo])",
                       "ROW('MinFecha', MIN(fact[fecha]), 'MaxFecha', MAX(fact[fecha]))").
            pbip_path: Ruta opcional al archivo .pbip para identificar la instancia correspondiente.
            port: Puerto local explícito de Analysis Services si se conoce.
            max_rows: Límite de filas a devolver (por defecto 50, 0 para ilimitado).
            catalog: Catálogo inicial opcional.

        Returns:
            Dict con columnas, lista de filas en JSON, conteo de filas y metadatos de ejecución.
        """
        return query_dax_model(
            dax_query=dax_query,
            pbip_path=pbip_path,
            port=port,
            max_rows=max_rows,
            catalog=catalog,
        )
