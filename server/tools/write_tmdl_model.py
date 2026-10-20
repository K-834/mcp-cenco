from __future__ import annotations

import re
import uuid
from pathlib import Path

from server.tools.encoding_helper import read_text_utf8, write_text_utf8


def _format_col_tmdl(table: str, column: str) -> str:
    """Formatea la referencia a columna en TMDL sin corchetes ([]).
    
    Ejemplos:
        Ventas, FechaID -> Ventas.FechaID
        Fact Ventas, Fecha ID -> 'Fact Ventas'.'Fecha ID'
    """
    tbl = f"'{table}'" if " " in table or "-" in table else table
    col = f"'{column}'" if " " in column or "-" in column else column
    return f"{tbl}.{col}"


def add_or_update_relationship(
    rel_file: Path,
    from_table: str,
    from_column: str,
    to_table: str,
    to_column: str,
    cardinality: str = "oneToMany",
    cross_filtering: str = "oneWay",
    is_active: bool = True,
    join_on_date_behavior: str | None = None,
) -> dict:
    """Añade o actualiza una relación en relationships.tmdl con sintaxis TMDL válida."""
    from_ref = _format_col_tmdl(from_table, from_column)
    to_ref = _format_col_tmdl(to_table, to_column)

    content = read_text_utf8(rel_file) if rel_file.exists() else ""

    # Buscar si ya existe una relación entre estas columnas
    # Nota: la relación puede estar escrita con o sin comillas
    escaped_from = re.escape(from_table)
    escaped_from_col = re.escape(from_column)
    escaped_to = re.escape(to_table)
    escaped_to_col = re.escape(to_column)

    rel_pattern = re.compile(
        rf"(^relationship\s+([a-f0-9\-]+|[a-zA-Z0-9_]+)\b.*?"
        rf"fromColumn:\s*(?:'{escaped_from}'|{escaped_from})\.(?:'{escaped_from_col}'|{escaped_from_col}|\[{escaped_from_col}\]).*?"
        rf"toColumn:\s*(?:'{escaped_to}'|{escaped_to})\.(?:'{escaped_to_col}'|{escaped_to_col}|\[{escaped_to_col}\]).*?"
        rf"(?=\nrelationship|\Z))",
        re.DOTALL | re.MULTILINE,
    )

    match = rel_pattern.search(content)
    existing_id = match.group(2) if match else str(uuid.uuid4())

    # Construir bloque TMDL estándar
    lines = [f"relationship {existing_id}"]
    if not is_active:
        lines.append("\tisActive: false")
    if join_on_date_behavior:
        lines.append(f"\tjoinOnDateBehavior: {join_on_date_behavior}")
    lines.append(f"\tfromColumn: {from_ref}")
    lines.append(f"\ttoColumn: {to_ref}")
    if cardinality != "oneToMany":
        lines.append(f"\tcardinality: {cardinality}")
    if cross_filtering != "oneWay":
        lines.append(f"\tcrossFilteringBehavior: {cross_filtering}")

    rel_block = "\n".join(lines) + "\n"

    if match:
        updated = content[: match.start()] + rel_block.rstrip("\n") + content[match.end() :]
        action = "updated"
    else:
        updated = (content.rstrip() + "\n\n" + rel_block).lstrip("\n")
        action = "created" if not content else "appended"

    write_text_utf8(rel_file, updated)
    return {
        "action": action,
        "relationship_id": existing_id,
        "file": str(rel_file),
        "from": from_ref,
        "to": to_ref,
    }


def set_time_intelligence_disabled(model_tmdl: Path) -> dict:
    """Configura annotation __PBI_TimeIntelligenceEnabled = 0 en model.tmdl para prevenir crashes."""
    if not model_tmdl.exists():
        return {"error": f"No se encontró el archivo: {model_tmdl}"}

    content = read_text_utf8(model_tmdl)

    pattern = re.compile(r"^annotation\s+__PBI_TimeIntelligenceEnabled\s*=.*$", re.MULTILINE)
    target_annotation = "annotation __PBI_TimeIntelligenceEnabled = 0"

    if pattern.search(content):
        updated = pattern.sub(target_annotation, content)
        action = "updated"
    else:
        # Insertar después del bloque dataAccessOptions o después de cabecera
        data_acc_match = re.search(r"(\tdataAccessOptions(?:\n\t\t[^\n]+)*)", content)
        if data_acc_match:
            pos = data_acc_match.end()
            updated = content[:pos] + f"\n\n{target_annotation}" + content[pos:]
        else:
            updated = content.rstrip() + f"\n\n{target_annotation}\n"
        action = "added"

    write_text_utf8(model_tmdl, updated)
    return {
        "success": True,
        "action": action,
        "file": str(model_tmdl),
        "message": "Auto Date/Time desactivado (__PBI_TimeIntelligenceEnabled = 0). Evita tablas de fecha ocultas y errores en DateTableSubsystem.",
    }


def register(mcp) -> None:
    @mcp.tool()
    def write_tmdl_relationship(
        pbip_path: str,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        cardinality: str = "oneToMany",
        cross_filtering: str = "oneWay",
        is_active: bool = True,
        join_on_date_behavior: str | None = None,
    ) -> dict:
        """Crea o edita una relación entre tablas en el modelo semántico TMDL con sintaxis oficial.

        Usa identificadores UUID estándar, elimina corchetes inválidos en TMDL y
        soporta comportamientos especiales de fecha como 'datePartOnly'.

        Args:
            pbip_path: Ruta a la carpeta .pbip del proyecto.
            from_table: Nombre de la tabla origen (ej. 'fact_bonus_canje_2026').
            from_column: Columna origen (ej. 'fecha_real').
            to_table: Nombre de la tabla destino (ej. 'dim_calendario').
            to_column: Columna destino (ej. 'Date').
            cardinality: Cardinalidad ('oneToMany', 'manyToOne', 'oneToOne', 'manyToMany').
            cross_filtering: Dirección de filtro ('oneWay', 'bothDirections').
            is_active: Si la relación está activa (por defecto True).
            join_on_date_behavior: Comportamiento para fechas (ej. 'datePartOnly' o None).

        Returns:
            Dict confirmando la edición en relationships.tmdl.
        """
        p = Path(pbip_path)
        if p.is_file():
            p = p.parent

        sem_models = list(p.glob("*.SemanticModel"))
        if not sem_models:
            return {"error": "No se encontró la carpeta *.SemanticModel."}

        rel_file = sem_models[0] / "definition" / "relationships.tmdl"
        return add_or_update_relationship(
            rel_file=rel_file,
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column,
            cardinality=cardinality,
            cross_filtering=cross_filtering,
            is_active=is_active,
            join_on_date_behavior=join_on_date_behavior,
        )

    @mcp.tool()
    def disable_auto_date_time(pbip_path: str) -> dict:
        """Desactiva 'Fecha y hora automáticas' en el modelo semántico (model.tmdl).

        Asegura 'annotation __PBI_TimeIntelligenceEnabled = 0', evitando que Power BI Desktop
        genere tablas de calendario automáticas ocultas (LocalDateTable_*) que causan
        InvalidOperationException / crash en DateTableSubsystem al relacionar calendarios.

        Args:
            pbip_path: Ruta a la carpeta .pbip del proyecto o archivo de manifiesto.

        Returns:
            Dict indicando si se añadió o actualizó la anotación en model.tmdl.
        """
        p = Path(pbip_path)
        if p.is_file():
            p = p.parent

        sem_models = list(p.glob("*.SemanticModel"))
        if not sem_models:
            return {"error": "No se encontró la carpeta *.SemanticModel."}

        model_tmdl = sem_models[0] / "definition" / "model.tmdl"
        return set_time_intelligence_disabled(model_tmdl)

    @mcp.tool()
    def write_tmdl_rls_role(
        pbip_path: str,
        role_name: str,
        table_name: str,
        dax_filter: str,
    ) -> dict:
        """Crea o actualiza un rol de seguridad a nivel de fila (RLS) en TMDL.

        Args:
            pbip_path: Ruta a la carpeta .pbip del proyecto.
            role_name: Nombre del rol (ej. "GerenteRegional").
            table_name: Tabla sobre la cual aplicar el filtro RLS.
            dax_filter: Expresión de filtro DAX (ej. "[Region] = USERPRINCIPALNAME()").

        Returns:
            Dict confirmando la creación en roles/<role_name>.tmdl.
        """
        p = Path(pbip_path)
        if p.is_file():
            p = p.parent

        sem_models = list(p.glob("*.SemanticModel"))
        if not sem_models:
            return {"error": "No se encontró la carpeta *.SemanticModel."}

        roles_dir = sem_models[0] / "definition" / "roles"
        roles_dir.mkdir(parents=True, exist_ok=True)
        role_file = roles_dir / f"{role_name}.tmdl"

        role_tmdl_content = f"""role '{role_name}'
\tmodelPermission: read

\ttablePermission '{table_name}' = {dax_filter}
"""
        write_text_utf8(role_file, role_tmdl_content)
        return {"success": True, "role_file": str(role_file), "role_name": role_name}
