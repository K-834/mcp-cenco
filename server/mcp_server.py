from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from server.prompts import dashboard_prompts
from server.resources import agent_guide, best_practices, html_content_reference, power_bi_reference
from server.tools import (
    check_pbi_desktop,
    consult_skill,
    convert_pbix,
    detect_format,
    encoding_helper,
    fix_dax_linter,
    generate_design,
    generate_pbip_docx,
    query_dax,
    read_pbip,
    validate_rules,
    write_dax_measure,
    write_pbir_layout,
    write_tmdl_model,
)

import argparse
import os

RULES_PATH = Path(__file__).parent.parent / "rules" / "rules.json"

SERVER_INSTRUCTIONS = """Eres un Agente Especialista en Power BI y Microsoft Fabric.
Este servidor MCP te provee un pipeline integral para auditar, disenar, planificar y modificar proyectos Power BI en formato PBIP (TMDL para modelos semanticos y PBIR para reportes).

REGLAS DE ACTIVACION Y FLUJO OPERATIVO MEJORADO:
1. ACTIVACION AUTOMATICA:
   - Activa tus herramientas siempre que el usuario mencione Power BI, archivos .pbip o .pbix, reportes, dashboards, DAX, modelos semanticos o KPIs.
2. PREVENCION DE CONFLICTOS EN DISCO ("Desktop pisa el disco"):
   - Antes de modificar TMDL o PBIR en disco, ejecuta `check_pbi_desktop_status`. Si Desktop tiene el archivo abierto, advierte al usuario o solicita guardar/cerrar Desktop para evitar que al guardar Desktop sobreescriba los cambios del agente.
3. DATOS EN VIVO (NO ADIVINAR DAX):
   - Nunca adivines DAX ni pidas capturas manuales de datos si Desktop está abierto. Usa `query_dax` para inspeccionar en vivo valores de columnas (VALUES/DISTINCT), rangos de fecha (MIN/MAX) y resultados de medidas.
4. MODELADO Y AUTO DATE/TIME:
   - Antes de relacionar tablas de fecha/calendario, ejecuta `disable_auto_date_time` para fijar `__PBI_TimeIntelligenceEnabled = 0` y evitar crashes en DateTableSubsystem.
   - Crea relaciones con `write_tmdl_relationship` (genera sintaxis TMDL oficial sin corchetes en columnas y con IDs UUID).
5. ESCRITURA Y VERIFICACION DE CODIFICACION:
   - Escribe medidas con `write_dax_measure` (garantiza colocación antes de particiones y preserva lineageTag).
   - Ejecuta `verify_and_fix_pbip_encoding` para asegurar que ningún archivo contenga BOM UTF-8.
6. AUDITORIA Y DISENO:
   - Auditoria: read_pbip -> validate_rules.
   - Diseno: read_pbip -> generate_design -> write_pbir_layout.
"""

mcp = MCPServer("powerbi-mcp-agent", instructions=SERVER_INSTRUCTIONS)

_RULES_CACHE: dict | None = None


def load_rules() -> dict:
    global _RULES_CACHE
    if _RULES_CACHE is None:
        _RULES_CACHE = __import__("json").loads(RULES_PATH.read_text(encoding="utf-8"))
    return _RULES_CACHE


check_pbi_desktop.register(mcp)
consult_skill.register(mcp)
convert_pbix.register(mcp)
detect_format.register(mcp, load_rules)
encoding_helper.register(mcp)
fix_dax_linter.register(mcp)
generate_design.register(mcp)
generate_pbip_docx.register(mcp, load_rules)
query_dax.register(mcp)
read_pbip.register(mcp)
validate_rules.register(mcp, load_rules)
write_dax_measure.register(mcp)
write_pbir_layout.register(mcp)
write_tmdl_model.register(mcp)
best_practices.register(mcp, load_rules)
power_bi_reference.register(mcp)
html_content_reference.register(mcp)
agent_guide.register(mcp)
dashboard_prompts.register(mcp)


def main() -> None:
    parser = argparse.ArgumentParser(description="Power BI MCP Agent Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.environ.get("POWERBI_MCP_TRANSPORT", "stdio"),
        help="Transport type (stdio, streamable-http, sse)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("POWERBI_MCP_HOST", "0.0.0.0"),
        help="Host address for HTTP/SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("POWERBI_MCP_PORT", 8000)),
        help="Port for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("POWERBI_MCP_PATH", "/mcp"),
        help="Path endpoint for HTTP/SSE transport (default: /mcp)",
    )

    args, _ = parser.parse_known_args()

    load_rules()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path=args.path,
        )
    elif args.transport == "sse":
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            sse_path=args.path,
        )



if __name__ == "__main__":
    main()

