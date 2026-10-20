from __future__ import annotations

import re
import uuid
from pathlib import Path

from server.tools.encoding_helper import read_text_utf8, write_text_utf8
from server.tools.fix_dax_linter import refactor_dax_expression


def format_tmdl_measure(
    measure_name: str,
    dax_code: str,
    format_string: str | None = None,
    display_folder: str | None = None,
    description: str | None = None,
    lineage_tag: str | None = None,
) -> str:
    """Formatea una medida DAX respetando la sintaxis y tabulación estándar de TMDL."""
    clean_name = measure_name.strip().strip("'")
    clean_dax = dax_code.strip()
    tag = lineage_tag or str(uuid.uuid4())

    dax_lines = clean_dax.split("\n")
    if len(dax_lines) == 1:
        measure_lines = [f"\tmeasure '{clean_name}' = {dax_lines[0]}"]
    else:
        measure_lines = [f"\tmeasure '{clean_name}' ="]
        for line in dax_lines:
            # Preservar indentación interna o agregar 3 tabs estándar TMDL
            stripped = line.rstrip()
            if stripped:
                measure_lines.append(f"\t\t\t{stripped}")
            else:
                measure_lines.append("")

    if format_string:
        measure_lines.append(f"\t\tformatString: {format_string}")
    if display_folder:
        measure_lines.append(f"\t\tdisplayFolder: {display_folder}")
    if description:
        clean_desc = description.replace('"', '\\"')
        measure_lines.append(f'\t\tdescription: "{clean_desc}"')
    if tag:
        measure_lines.append(f"\t\tlineageTag: {tag}")

    return "\n".join(measure_lines) + "\n"


def extract_lineage_tag(measure_block: str) -> str | None:
    """Extrae el lineageTag de un bloque de medida TMDL si existe."""
    match = re.search(r"^\t\tlineageTag:\s*([a-f0-9\-]+)", measure_block, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else None


def add_or_update_measure_in_tmdl(
    tmdl_path: Path,
    measure_name: str,
    dax_code: str,
    format_string: str | None = None,
    display_folder: str | None = None,
    description: str | None = None,
    auto_refactor_dax: bool = False,
) -> dict:
    """Modifica o inyecta una medida en sintaxis TMDL garantizando la estructura válida de la tabla."""
    if not tmdl_path.exists():
        return {"error": f"No se encontró el archivo TMDL de la tabla en: {tmdl_path}"}

    clean_name = measure_name.strip().strip("'")

    # 1. Refactorizar DAX solo si se solicitó explícitamente
    dax_to_use = dax_code
    linter_res = {}
    if auto_refactor_dax:
        linter_res = refactor_dax_expression(dax_code)
        dax_to_use = linter_res.get("refactored", dax_code)

    content = read_text_utf8(tmdl_path)

    # 2. Buscar si la medida ya existe (con comillas o sin comillas)
    escaped_name = re.escape(clean_name)
    measure_pattern = re.compile(
        rf"(^\tmeasure\s+(?:'{escaped_name}'|{escaped_name})\s*=.*?"
        rf"(?=\n\t(?:measure|column|partition|hierarchy|annotation)\b|\Z))",
        re.DOTALL | re.MULTILINE,
    )

    match = measure_pattern.search(content)
    if match:
        existing_block = match.group(1)
        existing_tag = extract_lineage_tag(existing_block)
        new_block = format_tmdl_measure(
            measure_name=clean_name,
            dax_code=dax_to_use,
            format_string=format_string,
            display_folder=display_folder,
            description=description,
            lineage_tag=existing_tag,
        )
        updated_content = content[: match.start()] + new_block.rstrip("\n") + content[match.end() :]
        action = "updated"
    else:
        # Medida nueva: determinar posición de inserción adecuada (antes de column/partition/annotation)
        new_block = format_tmdl_measure(
            measure_name=clean_name,
            dax_code=dax_to_use,
            format_string=format_string,
            display_folder=display_folder,
            description=description,
            lineage_tag=str(uuid.uuid4()),
        )

        # Buscar el final de la última medida existente
        last_measure_matches = list(
            re.finditer(
                r"^\tmeasure\s+.*?=(?:.|\n)*?(?=\n\t(?:measure|column|partition|hierarchy|annotation)\b|\Z)",
                content,
                re.MULTILINE,
            )
        )

        if last_measure_matches:
            insert_pos = last_measure_matches[-1].end()
            updated_content = content[:insert_pos].rstrip() + "\n\n" + new_block + content[insert_pos:].lstrip("\n")
        else:
            # Si no hay medidas, buscar el primer elemento de tabla (column, partition, annotation)
            first_element_match = re.search(
                r"(^\t(?:column|partition|hierarchy|annotation)\b)", content, re.MULTILINE
            )
            if first_element_match:
                insert_pos = first_element_match.start()
                updated_content = content[:insert_pos].rstrip() + "\n\n" + new_block + "\n" + content[insert_pos:].lstrip("\n")
            else:
                # Si la tabla solo tiene propiedades de cabecera
                updated_content = content.rstrip() + "\n\n" + new_block

        action = "added"

    write_text_utf8(tmdl_path, updated_content)

    return {
        "success": True,
        "action": action,
        "measure_name": clean_name,
        "file_updated": str(tmdl_path),
        "dax_used": dax_to_use,
        "linter_info": linter_res if auto_refactor_dax else None,
    }


def register(mcp) -> None:
    @mcp.tool()
    def write_dax_measure(
        pbip_path: str,
        table_name: str,
        measure_name: str,
        dax_code: str,
        format_string: str | None = None,
        display_folder: str | None = None,
        description: str | None = None,
        auto_refactor_dax: bool = False,
    ) -> dict:
        """Crea o actualiza una medida DAX en el modelo semántico TMDL del proyecto PBIP.

        Garantiza la sintaxis TMDL correcta, inserta la medida en la posición estructural
        válida (antes de particiones), preserva lineageTag y escribe en UTF-8 sin BOM.

        Args:
            pbip_path: Ruta a la carpeta .pbip o al archivo manifiesto del proyecto.
            table_name: Nombre de la tabla en el modelo donde residirá la medida.
            measure_name: Nombre de la medida DAX.
            dax_code: Expresión o fórmula DAX exacta.
            format_string: Formato de número/moneda (ej. "$#,##0.00", "0.0%", "#,##0").
            display_folder: Carpeta organizadora en Power BI (ej. "KPIs\\Ventas").
            description: Descripción clara del propósito del indicador.
            auto_refactor_dax: Si es True, aplica linter sobre la expresión DAX (por defecto False para respetar DAX exacto).

        Returns:
            Dict confirmando la escritura en el archivo TMDL de la tabla.
        """
        p = Path(pbip_path)
        if p.is_file():
            p = p.parent

        sem_models = list(p.glob("*.SemanticModel"))
        if not sem_models:
            return {"error": "No se encontró la carpeta *.SemanticModel en la ruta proporcionada."}

        table_tmdl = sem_models[0] / "definition" / "tables" / f"{table_name}.tmdl"
        return add_or_update_measure_in_tmdl(
            tmdl_path=table_tmdl,
            measure_name=measure_name,
            dax_code=dax_code,
            format_string=format_string,
            display_folder=display_folder,
            description=description,
            auto_refactor_dax=auto_refactor_dax,
        )
