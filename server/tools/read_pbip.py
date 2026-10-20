from __future__ import annotations

from pathlib import Path
from server.extractors.tmdl_extractor import parse_complete_pbip


def register(mcp) -> None:
    @mcp.tool()
    def read_pbip(semantic_model_path: str, report_path: str) -> dict:
        """Lee un proyecto .pbip y extrae tablas, particiones, orígenes, medidas, relaciones, roles y páginas.

        Args:
            semantic_model_path: Ruta a la carpeta *.SemanticModel.
            report_path: Ruta a la carpeta *.Report.

        Returns:
            Dict estructurado con `tables` (con particiones y columnas), `measures`, `relationships`, `roles`, `pages`.
        """
        sm_dir = Path(semantic_model_path)
        rep_dir = Path(report_path)
        if not sm_dir.exists():
            return {"error": f"No existe SemanticModel: {semantic_model_path}"}
        if not rep_dir.exists():
            return {"error": f"No existe Report: {report_path}"}

        return parse_complete_pbip(sm_dir, rep_dir)
