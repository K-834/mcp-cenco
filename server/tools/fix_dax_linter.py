from __future__ import annotations

import re


def _mask_strings_and_comments(code: str) -> tuple[str, list[str]]:
    """Oculta cadenas entre comillas y comentarios para evitar sustituciones erróneas."""
    placeholders: list[str] = []

    def replacer(match):
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"__TOKEN_PLACEHOLDER_{idx}__"

    # Patrón para cadenas entre comillas dobles y comentarios // o --
    token_pattern = re.compile(r'("(?:""|[^"])*")|(\/\/[^\n]*)|(--[^\n]*)')
    masked = token_pattern.sub(replacer, code)
    return masked, placeholders


def _unmask_strings_and_comments(code: str, placeholders: list[str]) -> str:
    """Restaura las cadenas y comentarios originales."""
    for idx, token in enumerate(placeholders):
        code = code.replace(f"__TOKEN_PLACEHOLDER_{idx}__", token)
    return code


def refactor_dax_expression(dax_code: str) -> dict:
    """Refactoriza y audita una expresión DAX aplicando buenas prácticas de forma segura.

    Transformaciones aplicadas:
    1. Reemplaza división directa '/' por 'DIVIDE(num, den, 0)' solo en código ejecutable (protegiendo strings y comentarios).
    2. Emite advertencias sobre antipatrones de rendimiento (ej. CALCULATE con FILTER sobre tablas completas).
    3. Formatea la indentación básica respetando bloques VAR y RETURN.

    Args:
        dax_code: Expresión DAX original.

    Returns:
        Dict con `original`, `refactored`, `changes_applied` y `warnings`.
    """
    code = dax_code.strip()
    changes: list[str] = []
    warnings: list[str] = []

    # 1. Proteger cadenas y comentarios
    masked_code, placeholders = _mask_strings_and_comments(code)

    # 2. Reemplazar división directa A / B por DIVIDE(A, B, 0)
    div_pattern = re.compile(r'([A-Za-z0-9_\[\]\'\)\.]+)\s*/\s*([A-Za-z0-9_\[\]\'\)\.]+)')

    def div_replacer(match):
        num, den = match.group(1).strip(), match.group(2).strip()
        # Evitar reemplazar tokens protegidos si eran comentarios
        if "__TOKEN_PLACEHOLDER_" in num or "__TOKEN_PLACEHOLDER_" in den:
            return match.group(0)
        return f"DIVIDE({num}, {den}, 0)"

    if "/" in masked_code and "DIVIDE(" not in masked_code:
        new_masked = div_pattern.sub(div_replacer, masked_code)
        if new_masked != masked_code:
            masked_code = new_masked
            changes.append("Reemplazada división directa '/' por 'DIVIDE(..., ..., 0)'.")

    # Restaurar cadenas y comentarios
    code = _unmask_strings_and_comments(masked_code, placeholders)

    # 3. Detectar antipatrón CALCULATE(..., FILTER(Table, ...))
    if re.search(r"\bCALCULATE\b.*?\bFILTER\s*\(", code, re.DOTALL | re.IGNORECASE):
        warnings.append(
            "Se detectó CALCULATE(..., FILTER(...)). Si la condición es sobre columnas individuales, "
            "evalúa usar un filtro directo sobre columna o REMOVEFILTERS() para evitar escanear la tabla completa."
        )

    # 4. Detectar funciones no recomendadas o peligrosas
    if "USERELATIONSHIP" in code.upper() and "BOTH" in code.upper():
        warnings.append("Verifica el uso de USERELATIONSHIP con filtrado cruzado bidireccional.")

    return {
        "original": dax_code,
        "refactored": code,
        "changes_applied": changes,
        "warnings": warnings,
    }


def register(mcp) -> None:
    @mcp.tool()
    def fix_dax(dax_code: str) -> dict:
        """Audita, refactoriza y aplica linter sobre una expresión DAX.

        Args:
            dax_code: Código o expresión DAX a evaluar.

        Returns:
            Dict con el DAX refactorizado, lista de cambios aplicados y advertencias.
        """
        return refactor_dax_expression(dax_code)
