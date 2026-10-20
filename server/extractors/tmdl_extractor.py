from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# TMDL Regex Patterns
TABLE_DEF_PATTERN = re.compile(
    r"^\s*(?:createOrReplace\s+)?table\s+`?([^\s`'\n]+)`?",
    re.MULTILINE | re.IGNORECASE,
)

COLUMN_BLOCK_PATTERN = re.compile(
    r"^\s*column\s+(?:'([^']+)'|`([^`]+)`|([^\s=\n]+))(?:\s*=\s*(.+?))?(?=\n\s*(?:column|measure|partition|hierarchy|annotation|\Z))",
    re.MULTILINE | re.DOTALL,
)

MEASURE_BLOCK_PATTERN = re.compile(
    r"^\s*measure\s+(?:'([^']+)'|`([^`]+)`|([^\s=\n]+))\s*=\s*(.+?)(?=\n\s*(?:measure|column|partition|hierarchy|annotation|\Z))",
    re.MULTILINE | re.DOTALL,
)

PARTITION_BLOCK_PATTERN = re.compile(
    r"^\s*partition\s+(?:'([^']+)'|`([^`]+)`|([^\s=\n]+))\s*=\s*(\w+)\s*\n((?:\t+.+\n?|\s{2,}.+\n?)+?)(?=^\s*(?:partition|table|column|measure|annotation)|\Z)",
    re.MULTILINE,
)

RELATIONSHIP_BLOCK_PATTERN = re.compile(
    r"^\s*relationship\s+`?([^`\n]+)`?\s*\n((?:\t+.+\n?|\s{2,}.+\n?)+?)(?=^\s*relationship|\Z)",
    re.MULTILINE,
)

ROLE_BLOCK_PATTERN = re.compile(
    r"^\s*role\s+(?:'([^']+)'|`([^`]+)`|([^\s=\n]+))\s*\n((?:\t+.+\n?|\s{2,}.+\n?)+?)(?=^\s*role|\Z)",
    re.MULTILINE,
)

# Property extractors inside blocks
DATA_TYPE_PATTERN = re.compile(r"dataType\s*:\s*(\w+)", re.IGNORECASE)
FORMAT_STRING_PATTERN = re.compile(r"formatString\s*:\s*[\"']?([^\"'\n]+)[\"']?", re.IGNORECASE)
DISPLAY_FOLDER_PATTERN = re.compile(r"displayFolder\s*:\s*[\"']?([^\"'\n]+)[\"']?", re.IGNORECASE)
SUMMARIZE_BY_PATTERN = re.compile(r"summarizeBy\s*:\s*(\w+)", re.IGNORECASE)
IS_HIDDEN_PATTERN = re.compile(r"isHidden\s*:\s*true", re.IGNORECASE)
IS_DATE_TABLE_PATTERN = re.compile(r"isDateTable\s*:\s*true", re.IGNORECASE)
SOURCE_COLUMN_PATTERN = re.compile(r"sourceColumn\s*:\s*([^\n\r]+)", re.IGNORECASE)
MODE_PATTERN = re.compile(r"mode\s*:\s*(\w+)", re.IGNORECASE)
SOURCE_PROP_PATTERN = re.compile(r"source\s*=\s*\n?((?:\t+.+\n?|\s{4,}.+\n?)+)", re.MULTILINE)

# Power Query M / Connector Detectors
CONNECTOR_PATTERNS = [
    ("AmazonRedshift.Database", r'AmazonRedshift\.Database\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'),
    ("Sql.Database", r'Sql\.Database\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'),
    ("PostgreSQL.Database", r'PostgreSQL\.Database\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'),
    ("GoogleBigQuery.Database", r'GoogleBigQuery\.Database\s*\('),
    ("Snowflake.Databases", r'Snowflake\.Databases\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'),
    ("Databricks.Catalogs", r'Databricks\.(?:Catalogs|Query)\s*\(\s*["\']([^"\']+)["\']'),
    ("Excel.Workbook", r'Excel\.Workbook\s*\(\s*(?:File\.Contents|Web\.Contents)\s*\(\s*["\']([^"\']+)["\']'),
    ("Csv.Document", r'Csv\.Document\s*\(\s*(?:File\.Contents|Web\.Contents)\s*\(\s*["\']([^"\']+)["\']'),
    ("SharePoint.Files", r'SharePoint\.Files\s*\(\s*["\']([^"\']+)["\']'),
    ("SharePoint.Tables", r'SharePoint\.Tables\s*\(\s*["\']([^"\']+)["\']'),
    ("OData.Feed", r'OData\.Feed\s*\(\s*["\']([^"\']+)["\']'),
    ("Web.Contents", r'Web\.Contents\s*\(\s*["\']([^"\']+)["\']'),
    ("AzureBlobs.Contents", r'AzureBlobs\.Contents\s*\(\s*["\']([^"\']+)["\']'),
    ("AzureStorage.DataLake", r'AzureStorage\.DataLake\s*\(\s*["\']([^"\']+)["\']'),
    ("SapHana.Database", r'SapHana\.Database\s*\(\s*["\']([^"\']+)["\']'),
    ("Oracle.Database", r'Oracle\.Database\s*\(\s*["\']([^"\']+)["\']'),
]


def _clean_code(text: str) -> str:
    """Removes leading tabs/indents uniformly to format code nicely."""
    if not text:
        return ""
    lines = text.strip().splitlines()
    if not lines:
        return ""
    # Filter out empty lines for finding min indent
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return ""
    min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)
    cleaned_lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
    return "\n".join(cleaned_lines)


def _extract_native_sql(text: str) -> str | None:
    """Extracts SQL query from Power Query M code (e.g. Value.NativeQuery)."""
    # Look for Value.NativeQuery and extract quoted SQL statement
    if "NativeQuery" in text or "select" in text.lower() or "with" in text.lower():
        sql_match = re.search(
            r'["\']\s*((?:SELECT|WITH|EXEC|CALL)\s+[\s\S]+?)["\']\s*(?:,|\)|\])',
            text,
            re.IGNORECASE,
        )
        if sql_match:
            return sql_match.group(1).replace('""', '"').strip()
    return None


def _extract_source_info(partition_type: str, mode: str, source_code: str) -> dict[str, Any]:
    """Analyzes partition source code to determine connectors, databases, SQL, and human summary."""
    clean_src = _clean_code(source_code)
    # Remove leading 'source =' if captured
    if clean_src.startswith("source ="):
        clean_src = _clean_code(clean_src[8:])
    # Remove leading 'mode:' line if captured
    cleaned_lines = []
    for line in clean_src.splitlines():
        if line.strip().startswith("mode:"):
            continue
        cleaned_lines.append(line)
    clean_src = "\n".join(cleaned_lines).strip()

    info: dict[str, Any] = {
        "partition_type": partition_type,
        "storage_mode": mode or "import",
        "connector": None,
        "server": None,
        "database": None,
        "schema": None,
        "native_query": None,
        "source_code": clean_src,
        "summary": "Origen de datos no especificado",
    }

    if partition_type == "calculated":
        info["connector"] = "DAX (Tabla Calculada)"
        first_line = clean_src.splitlines()[0] if clean_src else "Expresión DAX"
        info["summary"] = f"Tabla calculada en DAX ({first_line[:60]}...)" if len(first_line) > 60 else f"Tabla calculada en DAX ({first_line})"
        return info

    # Look for connectors
    for conn_name, pattern in CONNECTOR_PATTERNS:
        match = re.search(pattern, clean_src, re.IGNORECASE)
        if match:
            info["connector"] = conn_name
            groups = match.groups()
            if len(groups) >= 1:
                info["server"] = groups[0]
            if len(groups) >= 2:
                info["database"] = groups[1]
            break

    # Look for Native SQL Query
    native_sql = _extract_native_sql(clean_src)
    if native_sql:
        info["native_query"] = native_sql
        schema_match = re.search(r'from\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', native_sql, re.IGNORECASE)
        if schema_match:
            info["schema"] = schema_match.group(1)

    # Build human summary
    if info["connector"]:
        conn_label = info["connector"].replace(".Database", "").replace(".Contents", "").replace(".Workbook", "").replace(".Files", "")
        if info["server"] and info["database"]:
            info["summary"] = f"{conn_label}: {info['server']} / {info['database']}"
        elif info["server"]:
            info["summary"] = f"{conn_label}: {info['server']}"
        else:
            info["summary"] = f"Conector {conn_label}"
    elif partition_type == "m":
        info["connector"] = "Power Query (M)"
        info["summary"] = "Consulta Power Query (M personalizada)"
    else:
        info["summary"] = f"Partición {partition_type}"

    return info


def extract_table_from_tmdl(text: str, filename: str) -> dict[str, Any] | None:
    """Parses a single table .tmdl file and extracts detailed metadata."""
    tbl_match = TABLE_DEF_PATTERN.search(text)
    if not tbl_match:
        return None

    table_name = tbl_match.group(1)
    name_lower = table_name.lower()
    is_date = bool(IS_DATE_TABLE_PATTERN.search(text) or name_lower.startswith(("datetable_", "datetabletemplate_", "localdatetable_")))

    # Columns
    columns: list[dict[str, Any]] = []
    for match in COLUMN_BLOCK_PATTERN.finditer(text):
        col_name = match.group(1) or match.group(2) or match.group(3)
        calc_expr = match.group(4)
        block = match.group(0)

        dt = DATA_TYPE_PATTERN.search(block)
        fmt = FORMAT_STRING_PATTERN.search(block)
        folder = DISPLAY_FOLDER_PATTERN.search(block)
        sum_by = SUMMARIZE_BY_PATTERN.search(block)
        hidden = bool(IS_HIDDEN_PATTERN.search(block))
        src_col = SOURCE_COLUMN_PATTERN.search(block)

        columns.append({
            "name": col_name,
            "data_type": dt.group(1) if dt else "unknown",
            "format_string": fmt.group(1) if fmt else None,
            "display_folder": folder.group(1) if folder else None,
            "summarize_by": sum_by.group(1) if sum_by else "none",
            "is_hidden": hidden,
            "is_calculated": bool(calc_expr),
            "expression": _clean_code(calc_expr) if calc_expr else None,
            "source_column": src_col.group(1).strip() if src_col else None,
        })

    # Measures
    measures: list[dict[str, Any]] = []
    for match in MEASURE_BLOCK_PATTERN.finditer(text):
        m_name = match.group(1) or match.group(2) or match.group(3)
        expr_full = match.group(4)
        block = match.group(0)

        fmt = FORMAT_STRING_PATTERN.search(block)
        folder = DISPLAY_FOLDER_PATTERN.search(block)
        hidden = bool(IS_HIDDEN_PATTERN.search(block))

        # Split expression from annotations/format inside measure block
        expr_lines = []
        for line in expr_full.splitlines():
            stripped = line.strip()
            if stripped.startswith(("formatString:", "displayFolder:", "lineageTag:", "annotation", "isHidden:")):
                break
            expr_lines.append(line)
        cleaned_expr = _clean_code("\n".join(expr_lines))

        measures.append({
            "name": m_name,
            "expression": cleaned_expr,
            "format_string": fmt.group(1) if fmt else None,
            "display_folder": folder.group(1) if folder else None,
            "is_hidden": hidden,
            "table_name": table_name,
            "source_file": filename,
        })

    # Partitions & Data Sources
    partitions: list[dict[str, Any]] = []
    for match in PARTITION_BLOCK_PATTERN.finditer(text):
        p_name = match.group(1) or match.group(2) or match.group(3)
        p_type = match.group(4)
        p_body = match.group(5)

        mode_match = MODE_PATTERN.search(p_body)
        mode_val = mode_match.group(1) if mode_match else "import"

        src_match = SOURCE_PROP_PATTERN.search(p_body)
        raw_source = src_match.group(1) if src_match else p_body

        src_info = _extract_source_info(p_type, mode_val, raw_source)
        src_info["partition_name"] = p_name
        partitions.append(src_info)

    return {
        "name": table_name,
        "source_file": filename,
        "is_date_table": is_date,
        "columns": columns,
        "measures": measures,
        "partitions": partitions,
    }


def extract_relationships_from_tmdl(text: str, filename: str) -> list[dict[str, Any]]:
    """Extracts all relationships defined in relationships.tmdl or table files."""
    relationships: list[dict[str, Any]] = []
    from_col_pattern = re.compile(r"fromColumn\s*:\s*'?([^'\s\n\r]+)'?", re.IGNORECASE)
    to_col_pattern = re.compile(r"toColumn\s*:\s*'?([^'\s\n\r]+)'?", re.IGNORECASE)
    cross_filter_pattern = re.compile(r"crossFilteringBehavior\s*:\s*(\w+)", re.IGNORECASE)
    is_active_pattern = re.compile(r"isActive\s*:\s*(false|true)", re.IGNORECASE)

    for match in RELATIONSHIP_BLOCK_PATTERN.finditer(text):
        rel_id = match.group(1)
        block = match.group(2)

        fc = from_col_pattern.search(block)
        tc = to_col_pattern.search(block)
        if not (fc and tc):
            continue

        from_full = fc.group(1)
        to_full = tc.group(1)

        from_parts = from_full.split(".", 1)
        to_parts = to_full.split(".", 1)

        from_tbl = from_parts[0]
        from_col = from_parts[1] if len(from_parts) > 1 else ""
        to_tbl = to_parts[0]
        to_col = to_parts[1] if len(to_parts) > 1 else ""

        cross = cross_filter_pattern.search(block)
        active_match = is_active_pattern.search(block)
        is_active = active_match.group(1).lower() == "true" if active_match else True

        relationships.append({
            "id": rel_id,
            "from": from_full,
            "to": to_full,
            "from_table": from_tbl,
            "from_column": from_col,
            "to_table": to_tbl,
            "to_column": to_col,
            "cross_filter": cross.group(1) if cross else "oneDirection",
            "is_active": is_active,
            "source_file": filename,
        })
    return relationships


def extract_roles_from_tmdl(text: str, filename: str) -> list[dict[str, Any]]:
    """Extracts RLS roles and expressions from role TMDL files."""
    roles: list[dict[str, Any]] = []
    table_perm_pattern = re.compile(
        r"tablePermission\s+(?:'([^']+)'|`([^`]+)`|([^\s=\n]+))\s*=\s*(.+?)(?=\n\s*(?:tablePermission|annotation|\Z))",
        re.MULTILINE | re.DOTALL,
    )

    for match in ROLE_BLOCK_PATTERN.finditer(text):
        role_name = match.group(1) or match.group(2) or match.group(3)
        body = match.group(4)

        table_perms = []
        for tp in table_perm_pattern.finditer(body):
            tbl = tp.group(1) or tp.group(2) or tp.group(3)
            filter_expr = _clean_code(tp.group(4))
            table_perms.append({
                "table_name": tbl,
                "filter_expression": filter_expr,
            })

        roles.append({
            "role_name": role_name,
            "table_permissions": table_perms,
            "source_file": filename,
        })
    return roles


def _extract_visual_title(visual_obj: dict[str, Any]) -> str | None:
    try:
        title_props = visual_obj.get("visualContainerObjects", {}).get("title", [])
        for entry in title_props:
            value = (
                entry.get("properties", {})
                .get("text", {})
                .get("expr", {})
                .get("Literal", {})
                .get("Value")
            )
            if isinstance(value, str):
                return value.strip("'")
    except AttributeError:
        pass
    return None


def _extract_visuals_from_dir(page_dir: Path) -> list[dict[str, Any]]:
    """Reads visuals stored in the split-file PBIR layout (pages/<id>/visuals/<id>/visual.json)."""
    visuals: list[dict[str, Any]] = []
    visuals_dir = page_dir / "visuals"
    if not visuals_dir.exists():
        return visuals
    for visual_file in sorted(visuals_dir.rglob("visual.json")):
        try:
            data = json.loads(visual_file.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        visual_obj = data.get("visual", {}) if isinstance(data.get("visual"), dict) else {}
        visual_group = data.get("visualGroup") if isinstance(data.get("visualGroup"), dict) else None
        visuals.append({
            "id": data.get("name"),
            "type": "group" if visual_group is not None else visual_obj.get("visualType", "visual"),
            "title": (visual_group.get("displayName") if visual_group else None) or _extract_visual_title(visual_obj),
        })
    return visuals


def parse_complete_pbip(semantic_model_path: Path, report_path: Path | None = None) -> dict[str, Any]:
    """Orchestrates comprehensive parsing of a PBIP project."""
    definition_dir = semantic_model_path / "definition"
    tables: list[dict[str, Any]] = []
    all_measures: list[dict[str, Any]] = []
    all_relationships: list[dict[str, Any]] = []
    all_roles: list[dict[str, Any]] = []

    if definition_dir.exists():
        # Tables
        for tmdl in sorted((definition_dir / "tables").glob("*.tmdl") if (definition_dir / "tables").exists() else []):
            content = tmdl.read_text(encoding="utf-8", errors="replace")
            tbl = extract_table_from_tmdl(content, tmdl.name)
            if tbl:
                tables.append(tbl)
                all_measures.extend(tbl["measures"])

        # Relationships
        rel_file = definition_dir / "relationships.tmdl"
        if rel_file.exists():
            content = rel_file.read_text(encoding="utf-8", errors="replace")
            all_relationships.extend(extract_relationships_from_tmdl(content, rel_file.name))

        # Roles
        roles_dir = definition_dir / "roles"
        if roles_dir.exists():
            for rf in sorted(roles_dir.glob("*.tmdl")):
                content = rf.read_text(encoding="utf-8", errors="replace")
                all_roles.extend(extract_roles_from_tmdl(content, rf.name))

        # Model metadata
        model_file = definition_dir / "model.tmdl"
        time_intelligence_enabled = None
        if model_file.exists():
            m_content = model_file.read_text(encoding="utf-8", errors="replace")
            ti_match = re.search(r"annotation\s+__PBI_TimeIntelligenceEnabled\s*=\s*(\d+)", m_content)
            if ti_match:
                time_intelligence_enabled = (ti_match.group(1) == "1")

    # Pages and Report Visuals
    pages: list[dict[str, Any]] = []
    if report_path and report_path.exists():
        rep_def = report_path / "definition"
        if rep_def.exists():
            seen_ids = set()
            for json_file in sorted(rep_def.rglob("*.json")):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue

                # PBIR Pages
                if "pages" in data and isinstance(data["pages"], list):
                    for page in data["pages"]:
                        pid = page.get("id") or page.get("name")
                        if pid and pid in seen_ids:
                            continue
                        if pid:
                            seen_ids.add(pid)
                        visuals = []
                        if "visuals" in page and isinstance(page["visuals"], list):
                            for v in page["visuals"]:
                                visuals.append({
                                    "id": v.get("name") or v.get("id"),
                                    "type": v.get("visualType") or v.get("type", "visual"),
                                    "title": v.get("title") or (v.get("visual", {}).get("visualContainer", {}).get("title") if isinstance(v.get("visual"), dict) else None),
                                })
                        if not visuals:
                            visuals = _extract_visuals_from_dir(json_file.parent)
                        pages.append({
                            "name": page.get("displayName") or page.get("name"),
                            "page_id": pid,
                            "visual_count": len(visuals),
                            "visuals": visuals,
                            "source_file": str(json_file.relative_to(rep_def)),
                        })
                elif "displayName" in data and "name" in data:
                    pid = data.get("name")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        if isinstance(data.get("visuals"), list) and data.get("visuals"):
                            visuals = data["visuals"]
                        else:
                            visuals = _extract_visuals_from_dir(json_file.parent)
                        pages.append({
                            "name": data.get("displayName") or data.get("name"),
                            "page_id": pid,
                            "visual_count": len(visuals),
                            "visuals": visuals,
                            "source_file": str(json_file.relative_to(rep_def)),
                        })

    return {
        "project_name": semantic_model_path.parent.name or semantic_model_path.name.replace(".SemanticModel", ""),
        "time_intelligence_enabled": time_intelligence_enabled,
        "tables": tables,
        "measures": all_measures,
        "relationships": all_relationships,
        "roles": all_roles,
        "pages": pages,
    }
