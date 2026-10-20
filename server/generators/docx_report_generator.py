from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

# Corporate Palette (Power BI Modern Professional Theme)
COLOR_PRIMARY = RGBColor(0, 90, 158)      # #005A9E Power BI Deep Blue
COLOR_SECONDARY = RGBColor(16, 110, 190)  # #106EBE Accent Blue
COLOR_DARK = RGBColor(37, 36, 35)         # #252423 Charcoal Body Text
COLOR_MUTED = RGBColor(102, 102, 102)     # #666666 Muted Gray
COLOR_BG_HEADER = "005A9E"
COLOR_BG_SUBHEADER = "106EBE"
COLOR_BG_ZEBRA = "F8F9FA"
COLOR_BG_CODE = "F3F2F1"
COLOR_BORDER = "D2D0CE"


def _set_cell_background(cell, hex_color: str) -> None:
    """Sets the background fill color of a table cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150) -> None:
    """Sets internal padding for a cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color: str = COLOR_BORDER) -> None:
    """Sets subtle corporate table borders."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BG_HEADER}"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def _add_super_heading(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text.upper())
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = COLOR_PRIMARY


def _add_heading_1(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = COLOR_PRIMARY


def _add_heading_2(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = COLOR_SECONDARY


def _add_heading_3(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    run.font.bold = True
    run.font.color.rgb = COLOR_DARK


def _add_code_block(doc: docx.Document, code_text: str, language_label: str = "CODE") -> None:
    """Renders a shaded code block with fixed-width font."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    _set_cell_background(cell, COLOR_BG_CODE)
    _set_cell_margins(cell, top=100, bottom=100, left=160, right=160)

    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{COLOR_BG_HEADER}"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)

    lbl_run = p.add_run(f"[{language_label}]\n")
    lbl_run.font.size = Pt(8.5)
    lbl_run.font.bold = True
    lbl_run.font.color.rgb = COLOR_SECONDARY

    run = p.add_run(code_text.strip() if code_text else "-- (Sin código)")
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = COLOR_DARK

    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)


def _format_table_headers(table, headers: list[str], col_widths: list[float] | None = None) -> None:
    """Styles table header row."""
    hdr_cells = table.rows[0].cells
    for idx, title in enumerate(headers):
        cell = hdr_cells[idx]
        _set_cell_background(cell, COLOR_BG_HEADER)
        _set_cell_margins(cell, top=120, bottom=120, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(title)
        run.font.bold = True
        run.font.size = Pt(9.0)
        run.font.color.rgb = RGBColor(255, 255, 255)
        if col_widths and idx < len(col_widths):
            cell.width = Inches(col_widths[idx])


def _infer_kpi_metadata(m: dict[str, Any]) -> dict[str, str]:
    """Infers functional metadata, business definitions, and unit of measurement for a DAX measure."""
    name = str(m.get("name") or "")
    expr = str(m.get("expression") or "")
    fmt = str(m.get("format_string") or "")
    name_lower = name.lower()
    expr_lower = expr.lower()

    # 1. Indicator Type & Unit
    if "%" in name or "%" in fmt or any(w in name_lower for w in ["porc", "pct", "tasa", "ratio", "share", "margen", "yoy", "mom", "var"]):
        kpi_type = "Porcentual / Ratio"
        unit = "Porcentaje (%)"
        if "yoy" in name_lower or "año" in name_lower:
            meaning = "Mide la variación relativa interanual (Year-over-Year) contra el mismo periodo del año anterior."
        elif "mom" in name_lower or "mes" in name_lower:
            meaning = "Mide la variación relativa mensual (Month-over-Month) contra el mes inmediatamente anterior."
        elif "margen" in name_lower:
            meaning = "Indica la rentabilidad porcentual sobre los ingresos o costo de ventas."
        else:
            meaning = "Permite evaluar la proporción o tasa de eficiencia respecto al total o base de comparación."
    elif any(w in name_lower for w in ["s/", "monto", "venta", "ingreso", "costo", "ticket", "importe", "precio", "soles", "val"]) or "$" in fmt or "s/" in fmt.lower():
        kpi_type = "Financiero / Monetario"
        unit = "Moneda Local (S/.)"
        if "ticket" in name_lower:
            meaning = "Representa el importe monetario promedio generado por cada transacción o canje."
        elif "costo" in name_lower:
            meaning = "Cuantifica el desembolso económico total atribuido a la operación o programa."
        else:
            meaning = "Refleja el volumen económico consolidado en moneda local para el periodo evaluado."
    elif any(w in name_lower for w in ["canje", "trx", "transacc", "cantidad", "q", "conteo", "count", "clientes", "socios", "puntos", "total"]):
        kpi_type = "Volumen / Operativo"
        unit = "Unidades / Registros"
        if "canje" in name_lower:
            meaning = "Cuantifica el número total de transacciones de canje efectuadas por los clientes/socios."
        elif "clientes" in name_lower or "socios" in name_lower:
            meaning = "Mide la cantidad única de clientes o socios participantes en el periodo seleccionado."
        elif "puntos" in name_lower:
            meaning = "Acumula la cantidad total de puntos generados, acumulados o redimidos."
        else:
            meaning = "Mide la frecuencia o conteo absoluto de registros transaccionales procesados."
    else:
        kpi_type = "Gestión / Analítico"
        unit = "Escalar / Numérico"
        meaning = "Indicador de control y seguimiento operativo para segmentación o filtrado dimensional."

    # 2. Business Description
    if "divide" in expr_lower:
        desc = f"Calcula el ratio o porcentaje dividiendo la métrica base entre el total de referencia, manejando divisiones entre cero de forma segura."
    elif "calculate" in expr_lower and ("sameperiodlastyear" in expr_lower or "dateadd" in expr_lower):
        desc = f"Evalúa el comportamiento temporal de la métrica aplicando filtros de inteligencia de tiempo en el calendario."
    elif "distinctcount" in expr_lower:
        desc = f"Calcula el conteo de elementos únicos (sin duplicados) para asegurar la fidelidad del indicador."
    elif "sum(" in expr_lower:
        desc = f"Suma acumulada del campo transaccional base en la tabla {m.get('table_name', '')}."
    else:
        desc = f"Cálculo de negocio sobre la entidad {m.get('table_name', '')}."

    return {
        "kpi_type": kpi_type,
        "unit": unit,
        "business_definition": desc,
        "interpretation": meaning,
    }


def _infer_page_functional_purpose(page: dict[str, Any], project_name: str) -> dict[str, Any]:
    """Derives functional purpose, business questions, and visual guide for a report page."""
    name = page.get("name", "Página")
    name_l = name.lower()

    if any(w in name_l for w in ["resumen", "overview", "ejecutivo", "general", "kpi", "principal", "dashboard"]):
        purpose = "Tablero ejecutivo y estratégico. Proporciona una visión integral de los KPIs macro del negocio, facilitando la toma rápida de decisiones para la dirección."
        questions = [
            "¿Cuál es el desempeño global de los indicadores clave en el periodo actual?",
            "¿Cómo se comparan los resultados consolidados frente a periodos previos?",
            "¿Qué canales o áreas concentran la mayor participación del negocio?",
        ]
    elif any(w in name_l for w in ["canje", "transacc", "operacion", "venta", "detalle"]):
        purpose = "Análisis transaccional y operativo. Permite profundizar en el comportamiento detallado de las operaciones, canjes y transacciones realizadas."
        questions = [
            "¿Cuál es el volumen total de transacciones registradas por tienda o canal?",
            "¿Qué productos, categorías o tipos de canje presentan mayor demanda?",
            "¿Existen desviaciones u oportunidades de optimización en la operación?",
        ]
    elif any(w in name_l for w in ["canal", "tienda", "local", "sucursal", "geograf"]):
        purpose = "Análisis dimensional por canales y puntos de contacto. Evalúa la penetración, participación y rendimiento geográfico/comercial."
        questions = [
            "¿Qué canal o sucursal lidera el volumen transaccional y cumplimiento?",
            "¿Cómo varía la participación porcentual entre canales digitales y presenciales?",
            "¿Dónde se concentran las mayores oportunidades de crecimiento territorial?",
        ]
    elif any(w in name_l for w in ["evoluc", "tendencia", "historico", "mensual", "temporal"]):
        purpose = "Análisis de tendencias temporales e inteligencia de tiempo. Facilita la identificación de estacionalidades, picos de demanda y evolución histórica."
        questions = [
            "¿Cómo ha evolucionado la métrica mes a mes o día a día durante el año?",
            "¿Se observan patrones estacionales en días específicos o campañas comerciales?",
            "¿Cuál es la tasa de crecimiento o variación contra el año anterior (YoY)?",
        ]
    else:
        purpose = f"Vista de análisis focalizado sobre la dimensión '{name}'. Diseñada para usuarios de negocio que requieren seguimiento puntual y diagnóstico del área."
        questions = [
            f"¿Cuál es el comportamiento de los indicadores clave en la vista de {name}?",
            "¿Qué factores explican las variaciones observadas en esta sección?",
            "¿Cómo interactúan las variables de corte sobre este módulo?",
        ]

    return {
        "purpose": purpose,
        "questions": questions,
    }


def generate_pbip_documentation_docx(
    model_data: dict[str, Any],
    output_path: Path,
    audit_findings: list[dict[str, Any]] | None = None,
    include_functional: bool = True,
) -> Path:
    """Generates a complete Word document containing both Functional Business Documentation and Technical Architecture."""
    doc = docx.Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base Typography
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Segoe UI"
    style_normal.font.size = Pt(9.5)
    style_normal.font.color.rgb = COLOR_DARK

    project_name = model_data.get("project_name", "Proyecto Power BI")
    tables = model_data.get("tables", [])
    measures = model_data.get("measures", [])
    relationships = model_data.get("relationships", [])
    roles = model_data.get("roles", [])
    pages = model_data.get("pages", [])

    user_tables = [t for t in tables if not t.get("is_date_table", False)]
    date_tables = [t for t in tables if t.get("is_date_table", False)]

    # =========================================================================
    # PORTADA CORPORATIVA
    # =========================================================================
    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.space_before = Pt(30)
    run_pre = p_pre.add_run("POWER BI · ESPECIFICACIÓN FUNCIONAL Y TÉCNICA")
    run_pre.font.size = Pt(11)
    run_pre.font.bold = True
    run_pre.font.color.rgb = COLOR_SECONDARY

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(10)
    run_title = p_title.add_run(project_name)
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    p_desc = doc.add_paragraph(
        "Documento integral de arquitectura de Business Intelligence que consolida la "
        "perspectiva funcional de negocio (objetivos, catálogo de KPIs, preguntas clave y guía de usuario) "
        "junto con la especificación técnica completa del modelo semántico (TMDL), orígenes de datos, "
        "consultas M/SQL, formulaciones DAX, relaciones y auditoría de calidad."
    )
    p_desc.paragraph_format.space_after = Pt(20)

    # Metadata Summary Card
    meta_table = doc.add_table(rows=6, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(meta_table)
    
    meta_info = [
        ("Fecha de Emisión", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Nombre del Proyecto / Tablero", project_name),
        ("Páginas del Reporte Funcional", f"{len(pages)} páginas diseñadas"),
        ("Catálogo de Indicadores (KPIs / DAX)", f"{len(measures)} medidas implementadas"),
        ("Tablas del Modelo Semántico", f"{len(tables)} ({len(user_tables)} de negocio, {len(date_tables)} de calendario/sistema)"),
        ("Relaciones y Seguridad RLS", f"{len(relationships)} relaciones activas | {len(roles)} roles de seguridad"),
    ]
    for row_idx, (k, v) in enumerate(meta_info):
        cell_k = meta_table.cell(row_idx, 0)
        cell_v = meta_table.cell(row_idx, 1)
        cell_k.width = Inches(2.6)
        cell_v.width = Inches(3.9)
        _set_cell_margins(cell_k, 70, 70, 100, 100)
        _set_cell_margins(cell_v, 70, 70, 100, 100)
        if row_idx % 2 == 1:
            _set_cell_background(cell_k, COLOR_BG_ZEBRA)
            _set_cell_background(cell_v, COLOR_BG_ZEBRA)

        p_k = cell_k.paragraphs[0]
        run_k = p_k.add_run(k)
        run_k.font.bold = True
        run_k.font.size = Pt(9.0)
        run_k.font.color.rgb = COLOR_PRIMARY

        p_v = cell_v.paragraphs[0]
        run_v = p_v.add_run(v)
        run_v.font.size = Pt(9.0)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN I: DOCUMENTACIÓN FUNCIONAL Y DE NEGOCIO
    # =========================================================================
    if include_functional:
        _add_super_heading(doc, "SECCIÓN I: DOCUMENTACIÓN FUNCIONAL Y DE NEGOCIO")
        doc.add_paragraph(
            "Esta sección establece el marco conceptual y de uso del tablero, detallando los objetivos "
            "empresariales, la audiencia destinataria, el catálogo funcional de KPIs, la guía de navegación "
            "por pantalla y las reglas de negocio aplicadas."
        )

        # ---------------------------------------------------------------------
        # CAPÍTULO 1: OBJETIVOS Y ALCANCE DE NEGOCIO
        # ---------------------------------------------------------------------
        _add_heading_1(doc, "1. Objetivos y Alcance del Dashboard")
        
        _add_heading_2(doc, "1.1. Propósito General de Negocio")
        doc.add_paragraph(
            f"El reporte '{project_name}' tiene como objetivo central proporcionar a los equipos de negocio, "
            f"gerenciales y operativos una herramienta analítica interactiva y confiable para el monitoreo, "
            f"diagnóstico y seguimiento del rendimiento. El tablero consolida información transaccional "
            f"y dimensional para facilitar la toma de decisiones basada en datos (Data-Driven Decision Making)."
        )

        _add_heading_2(doc, "1.2. Audiencia Objetivo y Perfiles de Usuario")
        doc.add_paragraph(
            "El reporte está estructurado para atender diferentes niveles de análisis en la organización:"
        )
        p_aud = doc.add_paragraph()
        p_aud.add_run("• Nivel Ejecutivo (C-Level / Gerencias): ").font.bold = True
        p_aud.add_run("Consumo de KPIs macro, ratios consolidados, cumplimiento de metas globales y evolución periódica.\n")
        p_aud.add_run("• Nivel Táctico (Jefaturas / Product Owners): ").font.bold = True
        p_aud.add_run("Diagnóstico dimensional por canales, tiendas, segmentos de clientes y comparativas YoY / MoM.\n")
        p_aud.add_run("• Nivel Operativo (Analistas / Especialistas): ").font.bold = True
        p_aud.add_run("Exploración profunda, análisis transaccional detallado, identificación de anomalías y exportación de datos.\n")

        _add_heading_2(doc, "1.3. Preguntas Clave de Negocio Resueltas")
        doc.add_paragraph(
            "El diseño visual y analítico del modelo responde directamente a las siguientes interrogantes estratégicas:"
        )
        
        # Build smart business questions
        smart_questions = [
            f"¿Cuál es el volumen total acumulado de las operaciones y canjes en el periodo analizado?",
            f"¿Cómo se distribuye la participación de los indicadores clave entre los distintos canales de atención y tiendas?",
            f"¿Qué tendencia temporal y estacionalidad presentan las transacciones a lo largo de los meses y semanas?",
            f"¿Qué variación porcentual se observa en comparación con el mismo periodo del año anterior (YoY)?",
            f"¿Cuáles son los principales segmentos o categorías con mayor y menor rendimiento relativo?",
        ]
        for q in smart_questions:
            p_q = doc.add_paragraph()
            p_q.paragraph_format.space_before = Pt(1)
            p_q.paragraph_format.space_after = Pt(2)
            p_q.add_run(f"• {q}")

        # ---------------------------------------------------------------------
        # CAPÍTULO 2: DICCIONARIO FUNCIONAL DE KPIS
        # ---------------------------------------------------------------------
        _add_heading_1(doc, "2. Diccionario Funcional de Indicadores (KPIs)")
        doc.add_paragraph(
            "A continuación se presenta el catálogo de indicadores de negocio implementados en el modelo, "
            "describiendo su propósito funcional, unidad de medida, tipo de métrica y guía de interpretación:"
        )

        if measures:
            headers_kpi = ["Indicador / KPI", "Tipo Métrica", "Unidad", "Definición Funcional de Negocio", "Interpretación"]
            col_widths_kpi = [1.5, 1.1, 0.9, 1.8, 1.2]

            table_kpi = doc.add_table(rows=1 + len(measures), cols=5)
            table_kpi.alignment = WD_TABLE_ALIGNMENT.CENTER
            _set_table_borders(table_kpi)
            _format_table_headers(table_kpi, headers_kpi, col_widths_kpi)

            for m_idx, m in enumerate(measures, start=1):
                meta = _infer_kpi_metadata(m)
                cells = table_kpi.rows[m_idx].cells
                if m_idx % 2 == 0:
                    for c in cells:
                        _set_cell_background(c, COLOR_BG_ZEBRA)
                for c in cells:
                    _set_cell_margins(c, 60, 60, 80, 80)

                cells[0].paragraphs[0].add_run(f"[{m['name']}]").font.bold = True
                cells[1].paragraphs[0].add_run(meta["kpi_type"])
                cells[2].paragraphs[0].add_run(meta["unit"])
                cells[3].paragraphs[0].add_run(meta["business_definition"])
                cells[4].paragraphs[0].add_run(meta["interpretation"])
        else:
            doc.add_paragraph("No se detectaron medidas explícitas en el modelo semántico.")

        # ---------------------------------------------------------------------
        # CAPÍTULO 3: GUÍA FUNCIONAL DE NAVEGACIÓN POR PANTALLA
        # ---------------------------------------------------------------------
        _add_heading_1(doc, "3. Guía de Navegación y Uso por Pantalla (User Guide)")
        doc.add_paragraph(
            "Esta guía describe la experiencia de usuario y el objetivo analítico de cada una de las "
            "pantallas que componen el reporte Power BI:"
        )

        if pages:
            for p_idx, page in enumerate(pages, start=1):
                p_meta = _infer_page_functional_purpose(page, project_name)
                _add_heading_2(doc, f"3.{p_idx}. Pantalla: {page.get('name', 'Página')}")
                
                p_pdesc = doc.add_paragraph()
                p_pdesc.add_run("• Propósito Funcional: ").font.bold = True
                p_pdesc.add_run(f"{p_meta['purpose']}\n")

                doc.add_paragraph("Preguntas Clave que responde esta vista:").runs[0].font.bold = True
                for pq in p_meta["questions"]:
                    doc.add_paragraph(f"  - {pq}")

                # Visual breakdown
                visuals = page.get("visuals", [])
                if visuals:
                    _add_heading_3(doc, f"Componentes Visuales y Estructura ({len(visuals)} visuales)")
                    headers_v = ["Visual", "Tipo de Gráfico", "Objetivo / Interpretación de Negocio"]
                    col_widths_v = [1.8, 1.5, 3.2]

                    t_v = doc.add_table(rows=1 + len(visuals), cols=3)
                    t_v.alignment = WD_TABLE_ALIGNMENT.CENTER
                    _set_table_borders(t_v)
                    _format_table_headers(t_v, headers_v, col_widths_v)

                    for v_idx, vis in enumerate(visuals, start=1):
                        v_cells = t_v.rows[v_idx].cells
                        if v_idx % 2 == 0:
                            for c in v_cells:
                                _set_cell_background(c, COLOR_BG_ZEBRA)
                        for c in v_cells:
                            _set_cell_margins(c, 50, 50, 70, 70)

                        v_title = vis.get("title") or vis.get("id") or f"Visual {v_idx}"
                        v_type = vis.get("type", "visual")
                        v_cells[0].paragraphs[0].add_run(str(v_title)).font.bold = True
                        v_cells[1].paragraphs[0].add_run(v_type)

                        # Interpret visual type
                        v_l = v_type.lower()
                        if "card" in v_l or "kpi" in v_l:
                            v_meaning = "Tarjeta de KPI directo para visualización rápida del total acumulado."
                        elif "line" in v_l or "area" in v_l:
                            v_meaning = "Gráfico temporal para identificar tendencias, picos y evolución periódica."
                        elif "bar" in v_l or "column" in v_l:
                            v_meaning = "Gráfico de barras/columnas para ranking y comparación entre categorías o canales."
                        elif "table" in v_l or "matrix" in v_l or "pivot" in v_l:
                            v_meaning = "Matriz tabular con desglose detallado para auditoría, cruce dimensional y exportación."
                        elif "slicer" in v_l or "filter" in v_l:
                            v_meaning = "Segmentador interactivo para filtrar y recortar dinámicamente los datos de la pantalla."
                        else:
                            v_meaning = "Elemento visual interactivo de apoyo al análisis de datos."

                        v_cells[2].paragraphs[0].add_run(v_meaning)
                
                p_sp = doc.add_paragraph()
                p_sp.paragraph_format.space_before = Pt(4)
        else:
            doc.add_paragraph("No se detectaron definiciones PBIR de páginas en la carpeta Report.")

        # ---------------------------------------------------------------------
        # CAPÍTULO 4: REGLAS DE NEGOCIO Y GOBERNANZA FUNCIONAL
        # ---------------------------------------------------------------------
        _add_heading_1(doc, "4. Reglas de Negocio y Gobierno Funcional")
        doc.add_paragraph(
            "Criterios de consistencia, gobierno de datos y políticas de seguridad aplicadas:"
        )

        p_gov = doc.add_paragraph()
        p_gov.add_run("• Modelo Estrella (Star Schema): ").font.bold = True
        p_gov.add_run("El modelo separa rigurosamente las tablas de hechos transaccionales de las dimensiones maestras, garantizando consistencia analítica y alto rendimiento en consultas.\n")
        p_gov.add_run("• Tabla de Calendario Canónica: ").font.bold = True
        p_gov.add_run("La inteligencia de tiempo se basa en una dimensión de fechas continua, permitiendo comparativas homogéneas sin saltos temporales.\n")
        p_gov.add_run("• Seguridad y Confidencialidad: ").font.bold = True
        if roles:
            p_gov.add_run(f"Se definen {len(roles)} perfiles de seguridad RLS para restringir la visibilidad de datos confidenciales según el rol del usuario.\n")
        else:
            p_gov.add_run("Acceso corporativo global sin restricciones de fila (RLS) a nivel de modelo.\n")

        doc.add_page_break()

    # =========================================================================
    # SECCIÓN II: ESPECIFICACIÓN TÉCNICA Y ARQUITECTURA DEL MODELO
    # =========================================================================
    _add_super_heading(doc, "SECCIÓN II: ESPECIFICACIÓN TÉCNICA Y ARQUITECTURA")
    doc.add_paragraph(
        "Esta sección documenta la arquitectura técnica del modelo semántico (TMDL), orígenes de datos, "
        "consultas de extracción (Power Query M / SQL nativo), catálogo de fórmulas DAX, matriz de relaciones "
        "y diagnóstico de calidad bajo las 36 reglas de modelado MCP."
    )

    # =========================================================================
    # CAPÍTULO 5: ARQUITECTURA Y ORÍGENES DE DATOS
    # =========================================================================
    _add_heading_1(doc, "5. Arquitectura y Orígenes de Datos")
    doc.add_paragraph(
        "Detalle de la procedencia de cada tabla del modelo semántico, conectores utilizados, "
        "servidores, bases de datos y consultas de extracción (SQL nativo o Power Query M)."
    )

    _add_heading_2(doc, "5.1. Matriz de Conexiones y Almacenamiento")
    headers_sources = ["Tabla", "Tipo Origen", "Conector / Fuente", "Modo", "Consulta SQL / Detalle"]
    col_widths_sources = [1.6, 1.2, 1.5, 0.8, 1.4]
    
    table_sources = doc.add_table(rows=1 + len(user_tables), cols=5)
    table_sources.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table_sources)
    _format_table_headers(table_sources, headers_sources, col_widths_sources)

    for row_idx, tbl in enumerate(user_tables, start=1):
        parts = tbl.get("partitions", [])
        p0 = parts[0] if parts else {}
        cells = table_sources.rows[row_idx].cells
        
        if row_idx % 2 == 0:
            for c in cells:
                _set_cell_background(c, COLOR_BG_ZEBRA)
        for c in cells:
            _set_cell_margins(c, 70, 70, 90, 90)

        cells[0].paragraphs[0].add_run(tbl["name"]).font.bold = True
        cells[1].paragraphs[0].add_run(p0.get("partition_type", "m"))
        cells[2].paragraphs[0].add_run(p0.get("connector") or "Power Query")
        cells[3].paragraphs[0].add_run(p0.get("storage_mode", "import"))
        
        sql_note = "SQL Nativo" if p0.get("native_query") else ("DAX" if p0.get("partition_type") == "calculated" else "M Query")
        cells[4].paragraphs[0].add_run(sql_note)

    # Detalle por cada tabla
    _add_heading_2(doc, "5.2. Ficha Técnica de Extracción por Tabla")

    for tbl in user_tables:
        _add_heading_3(doc, f"Tabla: {tbl['name']}")
        parts = tbl.get("partitions", [])
        if not parts:
            doc.add_paragraph("No se detectaron particiones explícitas para esta tabla.")
            continue

        for p in parts:
            p_desc = doc.add_paragraph()
            p_desc.paragraph_format.space_before = Pt(2)
            p_desc.paragraph_format.space_after = Pt(4)
            p_desc.add_run("• Modo de Almacenamiento: ").font.bold = True
            p_desc.add_run(f"{p.get('storage_mode', 'import').capitalize()}\n")
            p_desc.add_run("• Conector / Motor: ").font.bold = True
            p_desc.add_run(f"{p.get('connector') or 'Power Query M'}\n")
            if p.get("server"):
                p_desc.add_run("• Servidor / Host: ").font.bold = True
                p_desc.add_run(f"{p.get('server')}\n")
            if p.get("database"):
                p_desc.add_run("• Base de Datos: ").font.bold = True
                p_desc.add_run(f"{p.get('database')}\n")
            if p.get("schema"):
                p_desc.add_run("• Esquema: ").font.bold = True
                p_desc.add_run(f"{p.get('schema')}\n")

            if p.get("native_query"):
                doc.add_paragraph("Consulta SQL Nativa de Extracción:").runs[0].font.bold = True
                _add_code_block(doc, p["native_query"], language_label="SQL NATIVO")

            if p.get("source_code") and p.get("partition_type") == "m":
                doc.add_paragraph("Código Power Query M completo:").runs[0].font.bold = True
                _add_code_block(doc, p["source_code"], language_label="POWER QUERY M")
            elif p.get("source_code") and p.get("partition_type") == "calculated":
                doc.add_paragraph("Expresión DAX de la Tabla Calculada:").runs[0].font.bold = True
                _add_code_block(doc, p["source_code"], language_label="DAX CALCULATED TABLE")

    # =========================================================================
    # CAPÍTULO 6: DICCIONARIO TÉCNICO DE DATOS
    # =========================================================================
    _add_heading_1(doc, "6. Diccionario Técnico de Datos (Columnas y VertiPaq)")
    doc.add_paragraph(
        "Detalle de las columnas de cada tabla, tipos de datos en el motor VertiPaq, "
        "formatos numéricos/fechas, carpetas de visualización y agregaciones por defecto."
    )

    for tbl in user_tables:
        cols = tbl.get("columns", [])
        _add_heading_2(doc, f"Estructura de Columnas: {tbl['name']} ({len(cols)} columnas)")

        if not cols:
            doc.add_paragraph("Esta tabla no posee columnas físicas declaradas (ej. tabla contenedora de medidas).")
            continue

        headers_cols = ["Columna", "Tipo Dato", "Formato", "Carpeta", "¿Oculta?", "SummarizeBy"]
        col_widths_cols = [1.8, 1.1, 1.3, 1.1, 0.6, 0.6]

        table_cols = doc.add_table(rows=1 + len(cols), cols=6)
        table_cols.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(table_cols)
        _format_table_headers(table_cols, headers_cols, col_widths_cols)

        for c_idx, col in enumerate(cols, start=1):
            cells = table_cols.rows[c_idx].cells
            if c_idx % 2 == 0:
                for c in cells:
                    _set_cell_background(c, COLOR_BG_ZEBRA)
            for c in cells:
                _set_cell_margins(c, 50, 50, 70, 70)

            cells[0].paragraphs[0].add_run(col["name"]).font.bold = True
            cells[1].paragraphs[0].add_run(col.get("data_type", "unknown"))
            cells[2].paragraphs[0].add_run(col.get("format_string") or "-")
            cells[3].paragraphs[0].add_run(col.get("display_folder") or "-")
            cells[4].paragraphs[0].add_run("Sí" if col.get("is_hidden") else "No")
            cells[5].paragraphs[0].add_run(col.get("summarize_by", "none"))

        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(4)

    # =========================================================================
    # CAPÍTULO 7: CATÁLOGO TÉCNICO DE MEDIDAS DAX
    # =========================================================================
    _add_heading_1(doc, "7. Catálogo Técnico de Medidas DAX")
    doc.add_paragraph(
        f"Inventario completo de las {len(measures)} medidas DAX implementadas en el modelo semántico, "
        "organizadas por tabla y carpetas de visualización con su formulación técnica completa."
    )

    measures_by_table: dict[str, list[dict[str, Any]]] = {}
    for m in measures:
        tname = m.get("table_name", "Otras")
        measures_by_table.setdefault(tname, []).append(m)

    for tname, m_list in measures_by_table.items():
        _add_heading_2(doc, f"Tabla: {tname} ({len(m_list)} medidas)")

        for m in m_list:
            _add_heading_3(doc, f"Medida: [{m['name']}]")
            p_m_info = doc.add_paragraph()
            p_m_info.paragraph_format.space_before = Pt(1)
            p_m_info.paragraph_format.space_after = Pt(2)
            if m.get("display_folder"):
                p_m_info.add_run("• Carpeta: ").font.bold = True
                p_m_info.add_run(f"{m['display_folder']}  ")
            if m.get("format_string"):
                p_m_info.add_run("• Formato: ").font.bold = True
                p_m_info.add_run(f"{m['format_string']}  ")
            if m.get("is_hidden"):
                p_m_info.add_run("• Estado: ").font.bold = True
                p_m_info.add_run("Oculta  ")

            _add_code_block(doc, m.get("expression", ""), language_label=f"DAX · [{m['name']}]")

    # =========================================================================
    # CAPÍTULO 8: MATRIZ DE RELACIONES DEL MODELO
    # =========================================================================
    _add_heading_1(doc, "8. Matriz de Relaciones del Modelo")
    doc.add_paragraph(
        f"El modelo semántico define {len(relationships)} relaciones entre tablas. "
        "A continuación se detalla la dirección de filtrado y cardinalidad:"
    )

    if relationships:
        headers_rel = ["Desde (From)", "Hacia (To)", "Filtro Cruzado", "¿Activa?", "Archivo Origen"]
        col_widths_rel = [2.0, 2.0, 1.1, 0.6, 0.8]

        table_rel = doc.add_table(rows=1 + len(relationships), cols=5)
        table_rel.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(table_rel)
        _format_table_headers(table_rel, headers_rel, col_widths_rel)

        for r_idx, rel in enumerate(relationships, start=1):
            cells = table_rel.rows[r_idx].cells
            if r_idx % 2 == 0:
                for c in cells:
                    _set_cell_background(c, COLOR_BG_ZEBRA)
            for c in cells:
                _set_cell_margins(c, 70, 70, 90, 90)

            cells[0].paragraphs[0].add_run(rel.get("from", "-")).font.bold = True
            cells[1].paragraphs[0].add_run(rel.get("to", "-")).font.bold = True
            cells[2].paragraphs[0].add_run(rel.get("cross_filter", "oneDirection"))
            cells[3].paragraphs[0].add_run("Sí" if rel.get("is_active", True) else "No")
            cells[4].paragraphs[0].add_run(rel.get("source_file", "relationships.tmdl"))
    else:
        doc.add_paragraph("No se detectaron relaciones explícitas en el modelo.")

    # =========================================================================
    # CAPÍTULO 9: SEGURIDAD TÉCNICA A NIVEL DE FILA (RLS)
    # =========================================================================
    _add_heading_1(doc, "9. Seguridad Técnica a Nivel de Fila (RLS)")
    if roles:
        doc.add_paragraph(f"Se identificaron {len(roles)} roles de seguridad configurados:")
        for r in roles:
            _add_heading_2(doc, f"Rol: {r.get('role_name', 'Sin Nombre')}")
            for tp in r.get("table_permissions", []):
                doc.add_paragraph(f"• Filtro sobre tabla '{tp.get('table_name')}':").runs[0].font.bold = True
                _add_code_block(doc, tp.get("filter_expression", ""), language_label="RLS DAX FILTER")
    else:
        doc.add_paragraph("No se registran roles de seguridad a nivel de fila (RLS) en el modelo semántico.")

    # =========================================================================
    # CAPÍTULO 10: AUDITORÍA DE CALIDAD Y REGLAS MCP
    # =========================================================================
    if audit_findings is not None:
        _add_heading_1(doc, "10. Diagnóstico de Calidad y Reglas MCP")
        doc.add_paragraph(
            "Resultado de la auditoría automática contra las 36 reglas de modelado y buenas prácticas de Power BI:"
        )

        if audit_findings:
            headers_audit = ["Regla", "Severidad", "Categoría", "Detalle / Hallazgo"]
            col_widths_audit = [1.2, 0.9, 1.2, 3.2]

            table_audit = doc.add_table(rows=1 + len(audit_findings), cols=4)
            table_audit.alignment = WD_TABLE_ALIGNMENT.CENTER
            _set_table_borders(table_audit)
            _format_table_headers(table_audit, headers_audit, col_widths_audit)

            for a_idx, finding in enumerate(audit_findings, start=1):
                cells = table_audit.rows[a_idx].cells
                if a_idx % 2 == 0:
                    for c in cells:
                        _set_cell_background(c, COLOR_BG_ZEBRA)
                for c in cells:
                    _set_cell_margins(c, 70, 70, 90, 90)

                cells[0].paragraphs[0].add_run(finding.get("rule_id", "REG")).font.bold = True
                
                sev = finding.get("severity", "WARNING").upper()
                r_sev = cells[1].paragraphs[0].add_run(sev)
                r_sev.font.bold = True
                if sev == "ERROR":
                    r_sev.font.color.rgb = RGBColor(196, 43, 28)
                else:
                    r_sev.font.color.rgb = RGBColor(183, 123, 0)

                cells[2].paragraphs[0].add_run(finding.get("category", "General"))
                cells[3].paragraphs[0].add_run(finding.get("message", "-"))
        else:
            doc.add_paragraph("✓ El modelo cumple con todas las reglas automáticas de validación sin observaciones.")

    # Ensure output directory exists and save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
