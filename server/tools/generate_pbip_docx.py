from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from server.converters.pbix_converter import convert_pbix_to_pbip
from server.extractors.tmdl_extractor import parse_complete_pbip
from server.generators.docx_report_generator import generate_pbip_documentation_docx


def _resolve_paths(target_path: str, report_path_opt: str = "") -> tuple[Path, Path | None, dict[str, Any] | None]:
    """Resolves semantic model and report paths from a pbip file, pbix file, or folder."""
    p = Path(target_path).resolve()
    
    # If path is a .pbix file, attempt conversion or return conversion metadata
    if p.is_file() and p.suffix.lower() == ".pbix":
        conv_res = convert_pbix_to_pbip(p)
        if not conv_res.get("ok"):
            return p, None, conv_res
        sm_path = Path(conv_res["semantic_model"])
        rep_path = Path(conv_res["report"]) if conv_res.get("report") else None
        return sm_path, rep_path, None

    # If path is a .pbip file
    if p.is_file() and p.suffix.lower() == ".pbip":
        parent = p.parent
        stem = p.stem
        sm_candidates = [
            parent / f"{stem}.SemanticModel",
            parent / f"{stem}.Dataset",
        ]
        rep_candidates = [
            parent / f"{stem}.Report",
        ]
        sm_path = next((c for c in sm_candidates if c.exists()), None)
        rep_path = next((c for c in rep_candidates if c.exists()), None)
        if not sm_path:
            raise FileNotFoundError(f"No se encontró la carpeta SemanticModel para {p.name}")
        return sm_path, rep_path, None

    # If path is a folder
    if p.is_dir():
        if p.name.endswith(".SemanticModel") or (p / "definition").exists():
            sm_path = p
            rep_path = None
            if report_path_opt:
                rep_path = Path(report_path_opt).resolve()
            else:
                stem = p.name.replace(".SemanticModel", "").replace(".Dataset", "")
                candidate = p.parent / f"{stem}.Report"
                if candidate.exists():
                    rep_path = candidate
            return sm_path, rep_path, None
        
        # Folder containing .SemanticModel inside
        sms = list(p.glob("*.SemanticModel"))
        if sms:
            sm_path = sms[0]
            stem = sm_path.name.replace(".SemanticModel", "")
            rep_cand = p / f"{stem}.Report"
            rep_path = rep_cand if rep_cand.exists() else None
            return sm_path, rep_path, None

    if report_path_opt and Path(report_path_opt).exists():
        return p, Path(report_path_opt).resolve(), None

    return p, None, None


def register(mcp, load_rules_fn: Callable[[], dict] | None = None) -> None:
    @mcp.tool()
    def generate_pbip_docx(
        semantic_model_path: str,
        report_path: str = "",
        output_path: str = "",
        include_audit: bool = True,
        include_functional: bool = True,
    ) -> dict[str, Any]:
        """Genera un informe integral en formato Word (.docx) que combina Documentación Funcional de Negocio y Especificación Técnica del modelo Power BI (.pbip / TMDL).

        Si se recibe un archivo .pbix, intenta la conversión automática previa o emite instrucciones claras para el guardado manual.

        Incluye:
        - SECCIÓN FUNCIONAL: Propósito general, audiencia, preguntas clave de negocio, catálogo de KPIs con unidades e interpretación, guía de navegación por pantalla y reglas de negocio.
        - SECCIÓN TÉCNICA: Matriz de orígenes de datos, conectores, consultas SQL nativas y Power Query M, diccionario de columnas y VertiPaq, catálogo de medidas DAX con fórmulas, matriz de relaciones, roles RLS y auditoría de calidad de reglas MCP.

        Args:
            semantic_model_path: Ruta a la carpeta *.SemanticModel, archivo *.pbip, archivo *.pbix o carpeta del proyecto.
            report_path: Ruta opcional a la carpeta *.Report.
            output_path: Ruta de salida opcional para el archivo .docx (por defecto outputs/Documentacion_<nombre>.docx).
            include_audit: Si es True, ejecuta la auditoría de reglas MCP y la anexa al documento.
            include_functional: Si es True, genera la documentación funcional y de negocio al inicio del reporte.

        Returns:
            Dict con el estado, ruta del archivo generado, conteos y resumen de orígenes.
        """
        try:
            sm_path, rep_path, conv_err = _resolve_paths(semantic_model_path, report_path)
            if conv_err:
                return {
                    "status": "manual_action_required",
                    "ok": False,
                    "pbix_path": conv_err.get("pbix_path"),
                    "target_folder": conv_err.get("target_folder"),
                    "instructions": conv_err.get("instructions"),
                    "message": conv_err.get("message"),
                }
        except Exception as e:
            return {"status": "error", "error": f"Error resolviendo rutas: {str(e)}"}

        if not sm_path.exists():
            return {"status": "error", "error": f"No existe el modelo semántico en: {semantic_model_path}"}

        # 1. Parse complete PBIP structure
        model_data = parse_complete_pbip(sm_path, rep_path)
        project_name = model_data.get("project_name", "Reporte_PowerBI")

        # 2. Run rule audit if requested
        audit_findings = None
        if include_audit and load_rules_fn:
            try:
                from server.tools.validate_rules import _evaluate_model
                rules_data = load_rules_fn()
                audit_result = _evaluate_model(model_data, rules_data)
                audit_findings = audit_result.get("findings", [])
            except Exception:
                audit_findings = []

        # 3. Determine output path
        if output_path:
            out_file = Path(output_path).resolve()
        else:
            safe_name = re.sub(r'[\\/*?:"<>| ]+', '_', project_name)
            out_file = Path("outputs").resolve() / f"Documentacion_{safe_name}.docx"

        # 4. Generate docx
        try:
            generated_doc = generate_pbip_documentation_docx(
                model_data=model_data,
                output_path=out_file,
                audit_findings=audit_findings,
                include_functional=include_functional,
            )
        except Exception as e:
            return {"status": "error", "error": f"Error generando documento Word: {str(e)}"}

        # Extract data sources summary
        sources_summary = []
        for t in model_data.get("tables", []):
            if not t.get("is_date_table"):
                for p in t.get("partitions", []):
                    sources_summary.append({
                        "table": t["name"],
                        "connector": p.get("connector"),
                        "server": p.get("server"),
                        "storage_mode": p.get("storage_mode"),
                        "has_native_sql": bool(p.get("native_query")),
                    })

        return {
            "status": "success",
            "output_file": str(generated_doc.resolve()),
            "project_name": project_name,
            "has_functional_docs": include_functional,
            "tables_count": len(model_data.get("tables", [])),
            "measures_count": len(model_data.get("measures", [])),
            "relationships_count": len(model_data.get("relationships", [])),
            "roles_count": len(model_data.get("roles", [])),
            "pages_count": len(model_data.get("pages", [])),
            "data_sources_count": len(sources_summary),
            "data_sources": sources_summary,
            "message": f"Documento Word funcional y técnico generado exitosamente: {generated_doc.name} ({len(model_data.get('tables', []))} tablas, {len(model_data.get('measures', []))} medidas, {len(sources_summary)} fuentes de datos).",
        }
