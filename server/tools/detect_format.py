from __future__ import annotations

from pathlib import Path
from server.converters.pbix_converter import convert_pbix_to_pbip, get_manual_conversion_instructions

PBIP_EXTENSION = ".pbip"
PBIX_EXTENSION = ".pbix"


def _looks_like_pbip_folder(path: Path) -> tuple[bool, Path | None, Path | None]:
    semantic_models = list(path.glob("*.SemanticModel"))
    reports = list(path.glob("*.Report"))
    if semantic_models and reports:
        return True, semantic_models[0], reports[0]
    return False, None, None


def register(mcp, load_rules) -> None:
    @mcp.tool()
    def detect_format(path: str, auto_convert: bool = False) -> dict:
        """Revisa la ruta y detecta si es .pbix o .pbip.

        Si es .pbix y auto_convert es True (o si se invoca la conversión),
        intenta convertirlo automáticamente a .pbip o emite las instrucciones manuales.

        Args:
            path: Ruta absoluta o relativa a la carpeta del proyecto o al archivo.
            auto_convert: Si es True y se recibe un .pbix, intenta la conversión automática a .pbip.

        Returns:
            Dict con formato detectado, estado, rutas de SemanticModel y Report,
            e instrucciones de conversión si aplica.
        """
        p = Path(path).resolve()
        if not p.exists():
            return {
                "format": "missing",
                "ok": False,
                "message": f"No existe la ruta: {path}",
            }

        if p.is_file():
            suffix = p.suffix.lower()
            if suffix == PBIX_EXTENSION:
                target_dir = Path("proyectos").resolve() / p.stem
                if auto_convert:
                    conv_res = convert_pbix_to_pbip(p, output_dir=target_dir)
                    if conv_res.get("ok"):
                        return {
                            "format": "pbip",
                            "ok": True,
                            "converted_from_pbix": True,
                            "semantic_model": conv_res.get("semantic_model"),
                            "report": conv_res.get("report"),
                            "pbip_path": conv_res.get("pbip_path"),
                            "message": f"Archivo .pbix convertido automáticamente a .pbip: {conv_res.get('semantic_model')}",
                        }
                    else:
                        return {
                            "format": "pbix",
                            "ok": False,
                            "requires_manual_conversion": True,
                            "instructions": conv_res.get("instructions"),
                            "message": (
                                "El archivo es .pbix. Se intentó la conversión automática pero se requiere acción manual. "
                                "Sigue las instrucciones adjuntas para guardarlo como .pbip en Power BI Desktop."
                            ),
                        }

                # Si no se pasó auto_convert=True
                instr = get_manual_conversion_instructions(p, target_dir)
                return {
                    "format": "pbix",
                    "ok": False,
                    "requires_conversion": True,
                    "target_folder": str(target_dir),
                    "instructions": instr,
                    "message": (
                        "El archivo es .pbix. Puedes usar 'convert_pbix_to_pbip' para intentar la conversión automática, "
                        "o realizar el guardado manual en Power BI Desktop como 'Power BI Project (*.pbip)'."
                    ),
                }

            if suffix == PBIP_EXTENSION:
                folder = p.parent
                is_folder, sm, rep = _looks_like_pbip_folder(folder)
                if is_folder:
                    return {
                        "format": "pbip",
                        "ok": True,
                        "semantic_model": str(sm),
                        "report": str(rep),
                        "message": "Proyecto .pbip detectado correctamente.",
                    }
                return {
                    "format": "unknown",
                    "ok": False,
                    "message": "Se encontró el archivo .pbip pero la carpeta no parece un proyecto válido.",
                }
            return {
                "format": "unknown",
                "ok": False,
                "message": f"Extensión no reconocida: {suffix}. Se espera .pbip o .pbix.",
            }

        is_folder, sm, rep = _looks_like_pbip_folder(p)
        if is_folder:
            return {
                "format": "pbip",
                "ok": True,
                "semantic_model": str(sm),
                "report": str(rep),
                "message": "Proyecto .pbip detectado correctamente.",
            }

        return {
            "format": "unknown",
            "ok": False,
            "message": "La ruta no parece un proyecto .pbip válido (faltan carpetas .SemanticModel y .Report).",
        }
