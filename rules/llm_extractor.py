"""Extractor LLM de reglas desde el documento completo de buenas practicas.

Usa `litellm` para compatibilidad multi-provider (Anthropic, OpenAI, Gemini, Ollama, MiniMax, etc.).
No hay fallback a un parser regex: si el LLM no esta disponible o falla, `compile_rules.py`
falla con un mensaje claro (ver `is_available()`).

Proveedores soportados (por orden de prioridad en `is_available()`):
1. Gemini / Google    -> GOOGLE_API_KEY / GEMINI_API_KEY
2. OpenAI             -> OPENAI_API_KEY
3. Anthropic          -> ANTHROPIC_API_KEY
4. MiniMax            -> MINIMAX_API_KEY (OpenAI-compatible en api.minimax.io/v1)
5. Custom OpenAI-like -> MODEL_API_KEY + MODEL_API_BASE / LITELLM_API_BASE
6. Ollama (local)     -> OLLAMA_API_BASE o http://localhost:11434 accesible
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import sys
import time
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

try:
    import litellm
except ImportError:
    litellm = None

from .prompts import build_document_messages


LOG = logging.getLogger(__name__)


DEFAULT_MODEL = "ollama/gemma3:4b"
DEFAULT_TIMEOUT = 180.0
DEFAULT_MAX_TOKENS = 4000
DEFAULT_NUM_CTX = 4096
DEFAULT_CHUNK_CHARS = 1500
OLLAMA_DEFAULT_BASE = "http://localhost:11434"
MINIMAX_DEFAULT_BASE = "https://api.minimax.io/v1"
MINIMAX_CHINA_BASE = "https://api.minimaxi.com/v1"


def _resolve_model() -> str:
    return os.environ.get("POWERBI_MCP_LLM_MODEL", DEFAULT_MODEL)


def _resolve_timeout() -> float:
    return float(os.environ.get("POWERBI_MCP_LLM_TIMEOUT", DEFAULT_TIMEOUT))


def _resolve_max_tokens() -> int:
    return int(os.environ.get("POWERBI_MCP_LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS))


def _resolve_num_ctx() -> int:
    return int(os.environ.get("POWERBI_MCP_LLM_NUM_CTX", DEFAULT_NUM_CTX))


def _resolve_chunk_chars() -> int:
    return int(os.environ.get("POWERBI_MCP_LLM_CHUNK_CHARS", DEFAULT_CHUNK_CHARS))


def _is_ollama_model(model: str) -> bool:
    """True si el model string apunta a un Ollama local."""
    return model.startswith("ollama/") or "localhost:11434" in model


def _is_minimax_model(model: str) -> bool:
    """True si el model string apunta a MiniMax (OpenAI-compatible)."""
    return model.startswith("minimax/") or model.startswith("MiniMax/")


def _ollama_reachable(base_url: str = OLLAMA_DEFAULT_BASE, timeout: float = 2.0) -> bool:
    """Hace un HEAD/GET a /api/tags. True si Ollama responde."""
    try:
        urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout).read()
        return True
    except (URLError, socket.timeout, ConnectionError, OSError):
        return False


def _resolve_ollama_base() -> str:
    """Devuelve la base URL del Ollama (env var o default localhost)."""
    return os.environ.get("OLLAMA_API_BASE", OLLAMA_DEFAULT_BASE).rstrip("/")


def _resolve_minimax_api_key() -> str | None:
    """Devuelve la API key de MiniMax (env var)."""
    return os.environ.get("MINIMAX_API_KEY") or os.environ.get("MINIMAX_GROUP_ID")


def _resolve_minimax_api_base() -> str:
    """Devuelve la base URL de MiniMax.

    Orden de prioridad:
    1. MINIMAX_API_BASE (env var explicita)
    2. Si MINIMAX_USE_CHINA=1, usa api.minimaxi.com
    3. Default: api.minimax.io (internacional)
    """
    explicit = os.environ.get("MINIMAX_API_BASE")
    if explicit:
        return explicit.rstrip("/")
    if os.environ.get("MINIMAX_USE_CHINA") == "1":
        return MINIMAX_CHINA_BASE
    return MINIMAX_DEFAULT_BASE


CATEGORIES = {
    "modelo_datos", "medidas_dax", "reporte_visual", "rendimiento",
    "nomenclatura", "seguridad", "documentacion",
}
SEVERITIES = {"alta", "media", "baja"}
CHECK_TYPES = {"automatico", "llm"}
SCOPES = {"tables", "columns", "measures", "relationships", "pages", "visuals", "dataset"}
_ID_RE = re.compile(r"^BP-\d{2,}$", re.IGNORECASE)

DEFAULT_CHUNK_CHARS = 1500


def _split_into_chunks(text: str, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Divide el texto en trozos de hasta `max_chars`, cortando solo entre lineas.

    No es un parser de reglas: no busca palabras clave ni intenta adivinar donde
    empieza o termina una regla (eso genero los bugs del regex anterior). Solo
    acota el tamano de cada llamada al LLM para que responda rapido incluso en
    CPU local. Si una regla queda partida justo en el borde de un trozo, el LLM
    de cada mitad puede devolver una version parcial; es un costo aceptable
    comparado con perder reglas enteras por una heuristica de limites fragil.
    """
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return [c for c in chunks if c.strip()]


def _ollama_native_call(messages: list[dict], model: str, timeout: float) -> str:
    """Llama a Ollama directamente via HTTP nativo (evita la latencia de litellm).

    Mucho mas rapido que `litellm.completion(model="ollama/...")` porque no usa el
    adaptador OpenAI-compatible de litellm, que añade ~3x de latencia con Ollama.

    El extractor manda el documento en trozos de ~2500 caracteres (ver
    `_split_into_chunks`), no el documento entero de una sola vez — un intento con
    el documento completo (num_ctx=8192, num_predict=8000) tardo >15 min en CPU y
    dio timeout. Con trozos chicos, estos valores alcanzan sobrados:
    - num_ctx: ver `POWERBI_MCP_LLM_NUM_CTX` (default 4096).
    - keep_alive=10m — evita que Ollama descargue el modelo entre llamadas.
    - num_predict: ver `POWERBI_MCP_LLM_MAX_TOKENS` (default 3000).

    El formato `ollama/<nombre>` se mapea a `nombre` para el endpoint `/api/generate`.
    El system prompt se concatena al prompt del usuario (Ollama native no distingue roles).
    """
    import urllib.request

    base = _resolve_ollama_base()
    model_name = model[len("ollama/"):] if model.startswith("ollama/") else model
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"<system>\n{content}\n</system>\n")
        else:
            parts.append(content)
    prompt = "\n".join(parts)
    payload = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": _resolve_num_ctx(),
            "num_predict": _resolve_max_tokens(),
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read()).get("response", "")


def _default_call(messages: list[dict], model: str, timeout: float) -> str:
    """Llama al LLM y devuelve el contenido textual.

    Para Ollama local: usa HTTP nativo (mas rapido que litellm).
    Para MiniMax y otros cloud: usa litellm con la API key correspondiente.

    Para Ollama local no se requiere API key; el resto de providers si.
    Nota: NO se hace health check dentro de esta funcion. Ollama procesa requests
    serialmente en CPU, asi que durante una llamada no responde al health check.
    El check de disponibilidad se hace una sola vez en `is_available()`.
    """
    if _is_ollama_model(model):
        return _ollama_native_call(messages, model, timeout)

    if litellm is None:
        raise RuntimeError(
            "litellm no esta instalado. Agregalo con `uv add litellm`."
        )

    if _is_minimax_model(model):
        api_key = _resolve_minimax_api_key()
        if not api_key:
            raise RuntimeError(
                "Modelo MiniMax detectado pero falta MINIMAX_API_KEY. "
                "Define la env var con tu key de MiniMax (https://api.minimax.io)."
            )
        return litellm.completion(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=_resolve_max_tokens(),
            timeout=timeout,
            api_key=api_key,
            api_base=_resolve_minimax_api_base(),
        ).choices[0].message.content or ""

    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("MODEL_API_KEY")
        or os.environ.get("LITELLM_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "No se encontro API key para un provider cloud. "
            "Define GOOGLE_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY / MINIMAX_API_KEY o usá un Ollama local."
        )
    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=_resolve_max_tokens(),
        timeout=timeout,
        api_key=api_key,
    )
    return response.choices[0].message.content or ""


def _strip_json_fences(raw: str) -> str:
    """Quita fences tipo ```json ... ``` si el modelo los agrega."""
    s = raw.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


def _coerce_rule(parsed: dict) -> dict | None:
    """Normaliza una regla individual devuelta por el LLM al formato del schema.

    Devuelve None si el objeto no tiene lo minimo para ser una regla valida
    (titulo o descripcion vacios/demasiado cortos) — el caller debe descartarlo.
    """
    if not isinstance(parsed, dict):
        return None

    title = str(parsed.get("title") or "").strip()
    description = str(parsed.get("description") or "").strip()
    if len(title) < 5 or len(description) < 10:
        return None

    category = str(parsed.get("category") or "").strip().lower()
    severity = str(parsed.get("severity") or "").strip().lower()
    check_type = str(parsed.get("check_type") or "").strip().lower()
    if category not in CATEGORIES:
        category = "modelo_datos"
    if severity not in SEVERITIES:
        severity = "media"
    if check_type not in CHECK_TYPES:
        check_type = "automatico"

    raw_scope = parsed.get("scope") or []
    if isinstance(raw_scope, str):
        raw_scope = [s.strip() for s in raw_scope.split(",") if s.strip()]
    scope = [s for s in raw_scope if s in SCOPES]

    raw_keywords = parsed.get("keywords") or []
    if isinstance(raw_keywords, str):
        raw_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    keywords = [str(k).strip() for k in raw_keywords if str(k).strip()][:10]

    source_id = str(parsed.get("source_id") or "").strip().upper()
    if not _ID_RE.match(source_id):
        source_id = ""

    rule = {
        "title": title[:160],
        "description": description[:500],
        "category": category,
        "severity": severity,
        "check_type": check_type,
        "detection": str(parsed.get("detection") or "").strip()[:300],
        "rationale": str(parsed.get("rationale") or "").strip()[:300],
        "scope": scope,
        "keywords": keywords,
        "example_violation": str(parsed.get("example_violation") or "").strip()[:300],
        "source_chunk": str(parsed.get("source_chunk") or "").strip()[:400],
        "compiled_by": "llm",
    }
    if source_id:
        rule["_source_id"] = source_id
    return rule


def _extract_rules_from_piece(
    piece: str,
    call: Callable,
    model: str,
    timeout: float,
    max_retries: int,
    label: str,
) -> list[dict]:
    """Llama al LLM para UN trozo de texto y devuelve sus reglas. Reintenta hasta `max_retries`."""
    messages = build_document_messages(piece)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = call(messages, model, timeout)
        except Exception as exc:
            last_error = str(exc)
            LOG.warning("%s intento %d/%d fallo: %s", label, attempt, max_retries, exc)
            continue

        cleaned = _strip_json_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            last_error = f"json decode: {exc}"
            LOG.warning("%s intento %d/%d devolvio JSON invalido: %s", label, attempt, max_retries, exc)
            continue

        raw_rules = parsed.get("rules") if isinstance(parsed, dict) else parsed
        if not isinstance(raw_rules, list):
            last_error = f"respuesta sin campo 'rules' (lista): {type(parsed).__name__}"
            LOG.warning("%s intento %d/%d: %s", label, attempt, max_retries, last_error)
            continue

        # Lista vacia es legitima (chunks de headers/intro sin reglas).
        if not raw_rules:
            return []

        valid_rules = [r for r in (_coerce_rule(item) for item in raw_rules) if r is not None]
        if not valid_rules:
            last_error = f"respuesta con 'rules' pero todas invalidas (recibi {len(raw_rules)} items, 0 validos)"
            LOG.warning("%s intento %d/%d: %s", label, attempt, max_retries, last_error)
            continue

        return valid_rules

    raise RuntimeError(f"{label} fallo tras {max_retries} intentos: {last_error or 'error desconocido'}")


def extract_rules(
    text: str,
    llm_callable: Callable | None = None,
    model: str | None = None,
    timeout: float | None = None,
    max_retries: int = 3,
    chunk_chars: int | None = None,
    strict: bool = False,
) -> list[dict]:
    """Extrae TODAS las reglas de buenas practicas de un documento via LLM.

    El documento se divide en trozos de hasta `chunk_chars` (corte solo por lineas,
    sin buscar keywords ni limites de regla — ver `_split_into_chunks`) para que
    cada llamada al LLM sea rapida incluso en CPU local. Cada trozo se manda al
    mismo prompt de documento completo; el LLM decide dentro del trozo cuantas
    reglas hay y donde empiezan/terminan.

    Args:
        text: texto completo del PDF/DOCX (via `extract_text()`).
        llm_callable: opcional, funcion(messages, model, timeout) -> str. Si es None,
                      usa litellm/Ollama nativo. Util para tests mockeados.
        model: nombre del modelo para litellm. Si es None, lee env POWERBI_MCP_LLM_MODEL
               o usa DEFAULT_MODEL.
        timeout: segundos de espera maxima POR TROZO. Si None, lee env
                 POWERBI_MCP_LLM_TIMEOUT o usa DEFAULT_TIMEOUT.
        max_retries: reintentos por trozo si el LLM falla o devuelve JSON invalido.
        chunk_chars: tamano maximo de cada trozo en caracteres.
        strict: si True, levanta RuntimeError cuando algun trozo falla. Default False
                (tolerante: salta trozos fallidos y loguea warning, devuelve las reglas
                que si se pudieron extraer).

    Returns:
        Lista de reglas normalizadas (dict) listas para asignarles `id` y volcarse a
        `rules.json`. Cada dict puede incluir `_source_id` (interno, lo consume
        `compile_rules.py` para decidir el ID final) si el documento numeraba la regla.

    Raises:
        RuntimeError: solo si `strict=True` y algun trozo falla tras `max_retries`.
            Si `strict=False`, los trozos fallidos se saltean y se devuelven las reglas
            de los trozos exitosos.
    """
    call = llm_callable or _default_call
    resolved_model = model or _resolve_model()
    resolved_timeout = timeout or _resolve_timeout()
    resolved_chunk_chars = chunk_chars or _resolve_chunk_chars()

    pieces = _split_into_chunks(text, max_chars=resolved_chunk_chars)
    print(f"  Documento dividido en {len(pieces)} trozo(s) de hasta {resolved_chunk_chars} caracteres.", file=sys.stderr)

    rules: list[dict] = []
    failed_chunks: list[tuple[int, str]] = []
    for idx, piece in enumerate(pieces, start=1):
        label = f"trozo {idx}/{len(pieces)}"
        start = time.time()
        try:
            piece_rules = _extract_rules_from_piece(piece, call, resolved_model, resolved_timeout, max_retries, label)
        except RuntimeError as exc:
            failed_chunks.append((idx, str(exc)))
            print(f"  [{label}] FALLO: {exc} ({time.time() - start:.1f}s)", file=sys.stderr, flush=True)
            if strict:
                raise
            continue
        rules.extend(piece_rules)
        if piece_rules:
            print(f"  [{label}] {len(piece_rules)} regla(s) ({time.time() - start:.1f}s)", file=sys.stderr, flush=True)
        else:
            print(f"  [{label}] 0 reglas (chunk sin contenido relevante) ({time.time() - start:.1f}s)", file=sys.stderr, flush=True)

    if failed_chunks:
        ids = ", ".join(str(i) for i, _ in failed_chunks)
        print(f"  [WARN] {len(failed_chunks)}/{len(pieces)} trozo(s) fallaron: {ids}", file=sys.stderr)
        print(f"  [WARN] Se guardaron {len(rules)} regla(s) de {len(pieces) - len(failed_chunks)} trozo(s) exitoso(s).", file=sys.stderr)
        print(f"  [WARN] Re-corre `compile --llm` para reintentar los trozos fallidos.", file=sys.stderr)

    return rules


def is_available() -> bool:
    """True si el extractor LLM puede ejecutarse.

    Orden de prioridad:
    1. litellm instalado + cualquier API key cloud (GOOGLE/OPENAI/ANTHROPIC/MiniMax/etc.)
    2. litellm instalado + OLLAMA_API_BASE / MODEL_API_BASE / LITELLM_API_BASE seteada (sin verificar)
    3. litellm instalado + Ollama respondiendo en localhost:11434
    """
    if litellm is None:
        return False
    if (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("MODEL_API_KEY")
        or os.environ.get("LITELLM_API_KEY")
        or os.environ.get("LITELLM_API_BASE")
        or os.environ.get("MODEL_API_BASE")
        or os.environ.get("MINIMAX_API_KEY")
        or os.environ.get("MINIMAX_API_BASE")
        or os.environ.get("OLLAMA_API_BASE")
    ):
        return True
    return _ollama_reachable(_resolve_ollama_base(), timeout=1.5)
