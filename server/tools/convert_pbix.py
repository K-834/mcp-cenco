from __future__ import annotations

from typing import Any
from server.converters.pbix_converter import convert_pbix_to_pbip as _convert_pbix_to_pbip


def register(mcp, load_rules=None) -> None:
    @mcp.tool()
    def convert_pbix_to_pbip(
        pbix_path: str,
        output_dir: str = "",
        timeout_seconds: int = 25,
    ) -> dict[str, Any]:
        """Convierte un archivo Power BI (.pbix) a formato de proyecto (.pbip / TMDL + PBIR).

        Intenta la conversión automática en Windows mediante Power BI Desktop.
        Si la automatización encuentra restricciones o requiere confirmación,
        emite las instrucciones guiadas paso a paso para el cambio manual.

        Args:
            pbix_path: Ruta absoluta o relativa al archivo .pbix.
            output_dir: Ruta opcional de destino para el proyecto .pbip (por defecto proyectos/<nombre>).
            timeout_seconds: Segundos máximos para esperar la automatización.

        Returns:
            Dict con el estado, rutas de SemanticModel y Report si tuvo éxito,
            o instrucciones manuales detalladas si se requiere acción del usuario.
        """
        return _convert_pbix_to_pbip(
            pbix_path=pbix_path,
            output_dir=output_dir if output_dir else None,
            timeout_seconds=timeout_seconds,
        )
