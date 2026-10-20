from __future__ import annotations

from pathlib import Path

UTF8_BOM = b"\xef\xbb\xbf"


def has_utf8_bom(path: Path) -> bool:
    """Verifica si un archivo inicia con la marca de orden de bytes (BOM) UTF-8."""
    if not path.is_file():
        return False
    with open(path, "rb") as f:
        prefix = f.read(3)
        return prefix == UTF8_BOM


def read_text_utf8(path: Path) -> str:
    """Lee el archivo eliminando cualquier BOM inicial si existe."""
    raw_bytes = path.read_bytes()
    if raw_bytes.startswith(UTF8_BOM):
        raw_bytes = raw_bytes[3:]
    return raw_bytes.decode("utf-8")


def write_text_utf8(path: Path, content: str, newline: str = "\n") -> None:
    """Escribe texto garantizando estrictamente codificación UTF-8 SIN BOM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Normalizar terminaciones de linea si se especifica
    if newline == "\r\n":
        normalized = content.replace("\r\n", "\n").replace("\n", "\r\n")
    else:
        normalized = content.replace("\r\n", "\n")

    encoded = normalized.encode("utf-8")
    with open(path, "wb") as f:
        f.write(encoded)


def scan_and_fix_pbip_encoding(pbip_path: str | Path, fix: bool = True) -> dict:
    """Escanea y opcionalmente repara todos los archivos .tmdl y .json en un PBIP."""
    root = Path(pbip_path)
    if root.is_file():
        root = root.parent

    if not root.exists():
        return {"error": f"La ruta {root} no existe."}

    extensions = {".tmdl", ".json", ".pbip", ".pbir"}
    scanned = []
    files_with_bom = []
    fixed_files = []

    for file_path in root.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            scanned.append(str(file_path.relative_to(root)))
            if has_utf8_bom(file_path):
                files_with_bom.append(str(file_path.relative_to(root)))
                if fix:
                    content = read_text_utf8(file_path)
                    write_text_utf8(file_path, content)
                    fixed_files.append(str(file_path.relative_to(root)))

    return {
        "success": True,
        "scanned_files_count": len(scanned),
        "files_with_bom_count": len(files_with_bom),
        "files_with_bom": files_with_bom,
        "fixed_files": fixed_files if fix else [],
        "message": (
            f"Se escanearon {len(scanned)} archivos. Se detectó BOM en {len(files_with_bom)} archivos."
            + (f" Se corrigieron {len(fixed_files)} archivos a UTF-8 sin BOM." if fix else "")
        ),
    }


def register(mcp) -> None:
    @mcp.tool()
    def verify_and_fix_pbip_encoding(pbip_path: str, fix: bool = True) -> dict:
        """Verifica y opcionalmente corrige la codificación de archivos .tmdl y .json en un proyecto PBIP.
        
        Garantiza que ningún archivo contenga Byte Order Mark (BOM UTF-8), el cual causa
        fallos y comportamiento inestable en Power BI Desktop.

        Args:
            pbip_path: Ruta a la carpeta del proyecto o al archivo .pbip.
            fix: Si es True, reescribe los archivos con BOM a UTF-8 limpio sin BOM.

        Returns:
            Resumen con el conteo de archivos analizados, con BOM y reparados.
        """
        return scan_and_fix_pbip_encoding(pbip_path=pbip_path, fix=fix)
