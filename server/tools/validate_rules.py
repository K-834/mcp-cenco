from __future__ import annotations

import re
from typing import Callable


def _eval_by_category(rule: dict, model: dict) -> tuple[str, str]:
    category = rule.get("category", "")
    title_low = (rule.get("title") or "").lower()
    desc_low = (rule.get("description") or "").lower()
    full = title_low + " " + desc_low

    tables = {t["name"].lower(): t for t in model.get("tables", [])}
    measures = model.get("measures", [])
    relationships = model.get("relationships", [])
    pages = model.get("pages", [])

    if (
        "bidireccional" in full
        or "bothdirections" in full
        or "esquema copo" in full
        or "esquema en estrella" in full
        or "esquema estrella" in full
        or "esquemas en estrella" in full
        or "esquema de copo" in full
        or "star schema" in full
        or "snowflake" in full
        or "cross filter" in full
    ):
        return _check_bidirectional(relationships)

    if category == "medidas_dax" or any(kw in full for kw in ["formatstring", "format string", "var ", "filter", "earlier", "iteracion", "iteración"]):
        return _check_measures(measures, full)
    if category == "modelo_datos" or any(kw in full for kw in ["fecha", "date table", "isDateTable"]):
        return _check_date_table(tables)
    if "rl" in full and ("rls" in full or "row-level" in full):
        return _check_rls(measures, full)

    if category == "rendimiento":
        return _check_performance_signals(model, full)
    if category == "nomenclatura":
        return _check_naming(model, full)
    if category == "reporte_visual":
        return _check_pages(pages, model)
    if category == "seguridad":
        return "skipped", "Verificacion de seguridad requiere analisis de RLS en el modelo."
    if category == "documentacion":
        return "skipped", "Verificacion de descripcion por columna requiere lectura TMDL ampliada."

    return "skipped", "Regla sin evaluador automatico especifico."


def _check_date_table(tables: dict[str, dict]) -> tuple[str, str]:
    if not tables:
        return "warning", "No hay tablas en el modelo extraido."
    candidates = [t for t in tables.values() if t.get("is_date_table") or t["name"].lower() in {
        "date", "dimdate", "dim_date", "calendar", "calendario",
        "dimfecha", "dim_fecha", "fechas", "datetable", "datetabletemplate", "localdatetable",
    }]
    if not candidates:
        return "warning", f"Sin Date Table marcada. Tablas: {', '.join(tables.keys())}."
    flagged = [t["name"] for t in candidates if t.get("is_date_table")]
    return "pass", f"Date Table(s): {', '.join(t['name'] for t in candidates)}. Marcada: {flagged or 'solo por nombre'}."


def _check_measures(measures: list[dict], full_text: str) -> tuple[str, str]:
    if any(kw in full_text for kw in ["formatstring", "format string", "formato"]):
        sin_formato = [m["name"] for m in measures if not m.get("format_string")]
        if not sin_formato:
            return "pass", f"Todas las {len(measures)} medida(s) tienen formatString."
        return "warning", f"Medidas sin formatString ({len(sin_formato)}): {', '.join(sin_formato)}."
    if any(kw in full_text for kw in ["var ", "variable", "var(", "pre calcular", "precalcular"]):
        sin_var = [m["name"] for m in measures if not re.search(r"\bVAR\b", m.get("expression", ""), re.IGNORECASE)]
        return "warning" if sin_var else "pass", f"Medidas sin VAR declaradas: {', '.join(sin_var[:5])}." if sin_var else "Todas las medidas usan VAR."
    if any(kw in full_text for kw in ["filter", "calculat", "earlier", "sumx", "iteracion", "iteración"]):
        suspect = []
        for m in measures:
            expr = m.get("expression", "")
            if re.search(r"\bFILTER\b\s*\(", expr, re.IGNORECASE) and "CALCULATE" in expr.upper():
                suspect.append(m["name"])
            if re.search(r"\bEARLIER\s*\(", expr, re.IGNORECASE):
                suspect.append(m["name"])
        return "warning" if suspect else "pass", f"Medidas con patrones a revisar: {', '.join(suspect[:5])}." if suspect else "Sin patrones problematicos detectados en DAX."
    sin_formato = [m["name"] for m in measures if not m.get("format_string")]
    if not measures:
        return "pass", "Sin medidas para evaluar."
    return "warning" if sin_formato else "pass", f"Medidas sin formatString: {', '.join(sin_formato[:5])}." if sin_formato else f"Todas las medidas tienen formatString."


def _check_bidirectional(relationships: list[dict]) -> tuple[str, str]:
    bidir = [r for r in relationships if (r.get("cross_filter", "") or "").lower() == "bothdirections"]
    if not bidir:
        return "pass", "Sin relaciones bidireccionales declaradas."
    return "warning", f"Relaciones bidireccionales ({len(bidir)}): " + "; ".join(f"{r.get('from')}->{r.get('to')}" for r in bidir[:5])


def _check_rls(measures: list[dict], full_text: str) -> tuple[str, str]:
    if "filter" in full_text or "filtro" in full_text:
        return _check_measures(measures, full_text)
    return "skipped", "Verificacion de RLS requiere analisis del modelo de seguridad."


def _check_performance_signals(model: dict, full_text: str) -> tuple[str, str]:
    tables = model.get("tables", [])
    measures = model.get("measures", [])
    relationships = model.get("relationships", [])

    if "cardinalidad" in full_text or "alta granularidad" in full_text:
        return "warning", "Verificacion manual: revisar relaciones con campos de alta cardinalidad (timestamps, ids)."
    if "agregacion" in full_text or "agregación" in full_text:
        return "warning", "Verificar si existen tablas agregadas para mejorar performance en modelos grandes."
    if any(kw in full_text for kw in ["filtro", "filtros", "filtro automatico", "fecha automatica", "fecha/hor", "time intelligence"]):
        if model.get("time_intelligence_enabled") is True or any(
            "datetabletemplate" in t.get("name", "").lower() or "localdatetable" in t.get("name", "").lower()
            for t in tables
        ):
            return "fail", "Auto Date/Time está HABILITADO o existen tablas de fecha automáticas (LocalDateTable/DateTableTemplate). Causa colisiones (InvalidOperationException) con calendarios propios. Ejecuta `disable_auto_date_time`."
        return "pass", "Auto Date/Time no detectado o deshabilitado correctamente (__PBI_TimeIntelligenceEnabled = 0)."
    if "ranking" in full_text or "top" in full_text:
        calc_ranking_cols = []
        for t in tables:
            for c in t.get("columns", []):
                if c.get("is_calculated") and ("rank" in c.get("name", "").lower() or "top" in c.get("name", "").lower() or (c.get("expression") and "RANKX" in c.get("expression", ""))):
                    calc_ranking_cols.append(f"{t.get('name')}[{c.get('name')}]")
        if calc_ranking_cols:
            return "warning", f"Ranking/Top N como columna calculada ({', '.join(calc_ranking_cols)}). Es estático en refresh y no reacciona a segmentadores. Usa medida DAX con ALLSELECTED o tabla desconectada."
        return "pass", "No se detectaron columnas calculadas estáticas de ranking."
    if "relacion" in full_text and "bidirec" in full_text:
        return _check_bidirectional(relationships)
    if "measure" in full_text or "medida" in full_text:
        return _check_measures(measures, full_text)
    if "columna duplicada" in full_text or "duplicad" in full_text:
        return "warning", "Verificar manualmente columnas duplicadas o sin uso en el modelo."
    return "skipped", "Senal de performance detectada en regla; sin parser dedicado."


def _check_naming(model: dict, full_text: str) -> tuple[str, str]:
    if "tipo" in full_text or "dato" in full_text:
        return "warning", "Verificar que columnas de tipo texto no almacenen valores numericos o fechas."
    if "ocult" in full_text or "hidden" in full_text:
        return "skipped", "Verificacion de campos ocultos requiere inspeccion de TMDL extendida."
    return "skipped", "Verificacion de nomenclatura requiere inspeccion manual."


def _check_pages(pages: list[dict], model: dict) -> tuple[str, str]:
    if not pages:
        return "warning", "Sin paginas detectadas en el reporte."
    descriptivos = [p for p in pages if p.get("name") and not re.match(r"^(page|hoja|pagina|página)\s*\d*$", p["name"], re.IGNORECASE)]
    if len(descriptivos) == len(pages):
        return "pass", f"Las {len(pages)} pagina(s) tienen titulos descriptivos."
    return "warning", f"Paginas con titulo poco descriptivo: {[p['name'] for p in pages if p not in descriptivos]}"


def register(mcp, load_rules: Callable[[], dict]) -> None:
    @mcp.tool()
    def validate_rules(model: dict, rules: list[dict] | None = None) -> dict:
        """Aplica las reglas automaticas al modelo extraido por `read_pbip`.

        Args:
            model: Salida de la tool `read_pbip`.
            rules: opcional, lista de reglas a evaluar. Si es None, usa las reglas de
                   rules.json (cargadas via load_rules). Util para tests con reglas
                   sinteticas.

        Returns:
            Dict con `findings` (reglas automaticas evaluadas) y `pending_llm_review`
            (reglas que requieren criterio humano o del LLM).
        """
        if rules is None:
            rules_doc = load_rules()
            rules = rules_doc.get("rules", [])

        findings: list[dict] = []
        pending: list[dict] = []

        for rule in rules:
            entry = {
                "rule_id": rule["id"],
                "title": rule["title"],
                "category": rule["category"],
                "severity": rule["severity"],
            }
            if rule.get("check_type") == "automatico":
                status, evidence = _eval_by_category(rule, model)
                findings.append({**entry, "status": status, "evidence": evidence})
            else:
                pending.append({**entry, "reason": rule.get("detection", "Requiere criterio.")})

        return {"findings": findings, "pending_llm_review": pending}
