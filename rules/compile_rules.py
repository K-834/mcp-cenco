"""Compila el documento de buenas practicas (.docx o .pdf) en rules.json.

Se ejecuta una sola vez (o cuando cambia la guia). El servidor MCP nunca lee
el documento original en tiempo de ejecucion.

El documento puede venir en formato narrativo con IDs tipo "BP-001 ..." (un
parrafo por regla) o en checklist tabular (Ambito/Objetivo/Item/Descripcion/
Requisito/Capacidad). No hay parser regex para esto: el texto completo se le
pasa a un LLM (`rules/llm_extractor.py`) que devuelve todas las reglas como
JSON en una sola llamada. Un parser regex para "donde termina una regla y
empieza la siguiente" resulto fragil en la practica (títulos cortados, filas
enteras tragadas por texto de relleno que matcheaba las mismas keywords) —
el LLM lee el documento completo con contexto y no tiene ese problema.

Requiere un LLM disponible (Ollama local corriendo, gratis, es el default; o
una API key cloud). Sin LLM disponible, el compilado falla con un mensaje
claro en vez de degradar a heuristicas regex.

Uso:
    uv run python rules/compile_rules.py
    uv run python rules/compile_rules.py --input docs/reglas-mcp/mi-guia.pdf
    uv run python rules/compile_rules.py --input docs/reglas-mcp/mi-guia.docx --output rules/rules.json
    uv run python rules/compile_rules.py --llm-model claude-haiku-4-5
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


SCHEMA_PATH = Path(__file__).parent / "schema.json"
DEFAULT_INPUT_DIR = Path(__file__).parent.parent / "docs" / "reglas-mcp"
DEFAULT_OUTPUT = Path(__file__).parent / "rules.json"


def discover_document(input_dir: Path) -> Path | None:
    if not input_dir.exists():
        return None
    candidates = sorted(input_dir.glob("*.pdf")) + sorted(input_dir.glob("*.docx"))
    candidates = [c for c in candidates if not c.name.startswith("~$") and not c.name.startswith(".")]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    print(f"[WARN] Multiples documentos encontrados en {input_dir}:", file=sys.stderr)
    for c in candidates:
        print(f"  - {c.name}", file=sys.stderr)
    print("Pasalo explicitamente con --input <ruta>.", file=sys.stderr)
    return candidates[0]


_MARKITDOWN: "MarkItDown | None" = None

_MD_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
_MD_TABLE_EMPTY_ROW_RE = re.compile(r"^(\|\s*)+$")


def _markitdown_converter() -> "MarkItDown":
    global _MARKITDOWN
    if MarkItDown is None:
        raise RuntimeError('Falta markitdown. Corre: uv add "markitdown[pdf,docx]"')
    if _MARKITDOWN is None:
        _MARKITDOWN = MarkItDown()
    return _MARKITDOWN


def _flatten_markdown_tables(text: str) -> str:
    """Limpieza cosmetica del markdown que emite markitdown (no extrae reglas).

    markitdown reconstruye las tablas del PDF/DOCX como filas `| celda | celda |`.
    Esto solo aplana esa sintaxis a texto separado por espacios y descarta filas
    separadoras (`| --- | --- |`) / vacias, para que el LLM lea texto mas limpio.
    No decide donde empieza o termina una regla — eso lo hace el LLM en `extract_rules()`.
    """
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if _MD_TABLE_SEPARATOR_RE.match(stripped):
            continue
        if stripped.startswith("|") and _MD_TABLE_EMPTY_ROW_RE.match(stripped):
            continue
        if "|" in line:
            cleaned = re.sub(r"^\|", "", line.strip())
            cleaned = re.sub(r"\|$", "", cleaned)
            out.append(cleaned.replace("|", "  "))
        else:
            out.append(line)
    return "\n".join(out)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in {".docx", ".pdf"}:
        raise ValueError(f"Formato no soportado: {suffix}. Usa .docx o .pdf.")
    converter = _markitdown_converter()
    result = converter.convert(str(path))
    return _flatten_markdown_tables(result.text_content)


def assign_ids(rules: list[dict]) -> list[dict]:
    """Asigna el `id` final a cada regla.

    Si el LLM detecto que el documento numeraba la regla explicitamente
    (`_source_id`, ej. "BP-003"), se usa ese ID. Si no, se asigna un ID
    secuencial "PBICHK-XXX". El campo interno `_source_id` no se persiste.
    """
    counter = 1
    result = []
    for rule in rules:
        rule = dict(rule)
        source_id = rule.pop("_source_id", "")
        rule["id"] = source_id or f"PBICHK-{counter:03d}"
        if not source_id:
            counter += 1
        result.append(rule)
    return result


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila buenas practicas en rules.json via LLM.")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--llm-model",
        default=None,
        help="Modelo para litellm/Ollama (default: env POWERBI_MCP_LLM_MODEL o Ollama local).",
    )
    args = parser.parse_args()

    if args.input is None:
        discovered = discover_document(DEFAULT_INPUT_DIR)
        if discovered is None:
            print(f"[ERROR] No se encontro ningun .pdf/.docx en {DEFAULT_INPUT_DIR}/", file=sys.stderr)
            print("Coloca tu guia de buenas practicas ahi (PDF o DOCX).", file=sys.stderr)
            return 1
        args.input = discovered
        print(f"  Documento detectado: {args.input.name}", file=sys.stderr)

    if not args.input.exists():
        print(f"[ERROR] No existe el documento de entrada: {args.input}", file=sys.stderr)
        return 1

    try:
        from rules.llm_extractor import extract_rules, is_available
    except ImportError:
        from llm_extractor import extract_rules, is_available

    if not is_available():
        print("[ERROR] No hay LLM disponible para compilar las reglas.", file=sys.stderr)
        print("        Arranca Ollama local (gratis, ver docs/proyecto/ollama-setup.md) o", file=sys.stderr)
        print("        define una API key: OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY.", file=sys.stderr)
        return 1

    if args.llm_model:
        os.environ["POWERBI_MCP_LLM_MODEL"] = args.llm_model

    print(f"[compile_rules] Leyendo {args.input.name}...", file=sys.stderr)
    text = extract_text(args.input)
    print(f"  Texto extraido: {len(text)} caracteres", file=sys.stderr)

    print(f"[INFO] Extrayendo reglas con LLM (modelo={args.llm_model or 'default'})...", file=sys.stderr)
    try:
        raw_rules = extract_rules(text, strict=True)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    rules = assign_ids(raw_rules)

    payload = {
        "version": "1.0",
        "generated_from": str(args.input),
        "rules_count": len(rules),
        "rules": rules,
    }

    schema = load_schema()
    if jsonschema is not None:
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.ValidationError as exc:
            print(f"[ERROR] Validacion de schema fallo: {exc.message}", file=sys.stderr)
            return 3

    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    auto = sum(1 for r in rules if r["check_type"] == "automatico")
    llm = sum(1 for r in rules if r["check_type"] == "llm")
    print(f"[OK] Reglas compiladas: {len(rules)} (automaticas: {auto}, criterio: {llm})", file=sys.stderr)
    print(f"[OK] Salida: {args.output}", file=sys.stderr)
    print(f"[OK] Origen: {args.input.name}", file=sys.stderr)
    print("[INFO] Compilacion es semiautomatica: revisa manualmente el archivo antes de usar el servidor.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
