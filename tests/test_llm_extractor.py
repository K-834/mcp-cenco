from __future__ import annotations

import json
from pathlib import Path

import jsonschema


MOCK_RULE = {
    "source_id": None,
    "title": "Uso de tipos de datos correcto",
    "description": "Evitar el uso de tipo texto en campos numericos o de fecha en el modelo.",
    "category": "nomenclatura",
    "severity": "alta",
    "check_type": "automatico",
    "detection": "Revisar tipo de dato de columnas en TMDL.",
    "rationale": "Evita errores de conversion y mejora performance.",
    "scope": ["columns"],
    "keywords": ["dataType", "tipo de dato", "string", "integer", "date"],
    "example_violation": "Columna 'monto' almacenada como STRING en lugar de DECIMAL.",
    "source_chunk": "Uso de tipos de datos correcto: evitar texto en campos numericos.",
}

MOCK_RESPONSE = json.dumps({"rules": [MOCK_RULE]})

MOCK_EMPTY_RESPONSE = json.dumps({"rules": []})


def fake_call_factory(response_json: str):
    """Devuelve una funcion llm_callable que siempre devuelve `response_json`."""
    def fake(messages, model, timeout):
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        return response_json
    return fake


def test_extract_rules_parses_valid_response():
    from rules.llm_extractor import extract_rules

    result = extract_rules("Performance Duplicidad ... Obligatorio MidPerf", llm_callable=fake_call_factory(MOCK_RESPONSE))
    assert len(result) == 1
    rule = result[0]
    assert rule["title"] == "Uso de tipos de datos correcto"
    assert rule["category"] == "nomenclatura"
    assert rule["severity"] == "alta"
    assert rule["scope"] == ["columns"]
    assert "dataType" in rule["keywords"]
    assert rule["compiled_by"] == "llm"


def test_extract_rules_preserves_explicit_source_id():
    from rules.llm_extractor import extract_rules

    with_id = json.dumps({"rules": [{**MOCK_RULE, "source_id": "BP-003"}]})
    result = extract_rules("texto", llm_callable=fake_call_factory(with_id))
    assert result[0]["_source_id"] == "BP-003"


def test_extract_rules_drops_invalid_source_id():
    from rules.llm_extractor import extract_rules

    bad_id = json.dumps({"rules": [{**MOCK_RULE, "source_id": "no es un id"}]})
    result = extract_rules("texto", llm_callable=fake_call_factory(bad_id))
    assert "_source_id" not in result[0]


def test_extract_rules_strips_json_fences():
    from rules.llm_extractor import extract_rules

    fenced = "```json\n" + MOCK_RESPONSE + "\n```"
    result = extract_rules("texto", llm_callable=fake_call_factory(fenced))
    assert len(result) == 1
    assert result[0]["title"] == "Uso de tipos de datos correcto"


def test_extract_rules_accepts_bare_array():
    """Si el LLM devuelve un array JSON pelado (sin envolver en {'rules': [...]}), tambien funciona."""
    from rules.llm_extractor import extract_rules

    bare_array = json.dumps([MOCK_RULE])
    result = extract_rules("texto", llm_callable=fake_call_factory(bare_array))
    assert len(result) == 1


def test_extract_rules_drops_entries_with_short_title_or_description():
    from rules.llm_extractor import extract_rules

    junk = json.dumps({"rules": [MOCK_RULE, {**MOCK_RULE, "title": "x", "description": "corta"}]})
    result = extract_rules("texto", llm_callable=fake_call_factory(junk))
    assert len(result) == 1


def test_extract_rules_coerces_invalid_categories():
    from rules.llm_extractor import extract_rules

    bad_cat = json.dumps({"rules": [{**MOCK_RULE, "category": "no_existe"}]})
    result = extract_rules("texto", llm_callable=fake_call_factory(bad_cat))
    assert result[0]["category"] == "modelo_datos"


def test_extract_rules_raises_on_invalid_json_after_retries():
    from rules.llm_extractor import extract_rules

    with __import__("pytest").raises(RuntimeError):
        extract_rules("texto", llm_callable=fake_call_factory("not json at all"), max_retries=2, strict=True)


def test_extract_rules_tolerates_invalid_json_when_not_strict():
    """Sin strict=True, JSON invalido en un trozo se loguea y el resto se procesa."""
    from rules.llm_extractor import extract_rules

    valid_json = json.dumps({
        "rules": [{
            "title": "Uso de tipos de datos correcto",
            "description": "Evitar texto en campos numericos o de fecha en el modelo.",
            "category": "nomenclatura",
            "severity": "alta",
            "check_type": "automatico",
            "scope": ["columns"],
            "keywords": ["dataType"],
            "example_violation": "Monto como STRING.",
        }]
    })
    calls = {"n": 0}

    def alternating_call(messages, model, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return "no es json"
        return valid_json

    rules = extract_rules("texto", llm_callable=alternating_call, max_retries=2, chunk_chars=100)
    assert any(r["title"] == "Uso de tipos de datos correcto" for r in rules)


def test_extract_rules_raises_when_llm_always_fails():
    from rules.llm_extractor import extract_rules

    def failing_call(messages, model, timeout):
        raise RuntimeError("API timeout")

    with __import__("pytest").raises(RuntimeError):
        extract_rules("texto", llm_callable=failing_call, max_retries=2, strict=True)


def test_extract_rules_raises_when_llm_returns_invalid_rules():
    """Si el LLM devuelve items en 'rules' pero todos son invalidos, levanta RuntimeError."""
    from rules.llm_extractor import extract_rules

    invalid_items = json.dumps({"rules": [
        {"title": "x", "description": "y"},  # demasiado corto, sera invalido
    ]})
    with __import__("pytest").raises(RuntimeError):
        extract_rules("texto", llm_callable=fake_call_factory(invalid_items), max_retries=1, strict=True)


def test_extract_rules_accepts_empty_rules_list():
    """`{"rules": []}` es legitimo (chunk de headers/intro sin reglas). NO debe fallar."""
    from rules.llm_extractor import extract_rules

    rules = extract_rules("texto", llm_callable=fake_call_factory(MOCK_EMPTY_RESPONSE), max_retries=1)
    assert rules == []


def test_extract_rules_splits_long_documents_into_chunks():
    """Un documento mas grande que chunk_chars genera varias llamadas al LLM."""
    from rules.llm_extractor import extract_rules

    calls = {"count": 0}

    def counting_call(messages, model, timeout):
        calls["count"] += 1
        return MOCK_RESPONSE

    long_text = "\n".join(f"linea {i} de contenido de relleno" for i in range(400))
    result = extract_rules(long_text, llm_callable=counting_call, chunk_chars=500)
    assert calls["count"] > 1
    assert len(result) == calls["count"]


def test_split_into_chunks_respects_max_chars():
    from rules.llm_extractor import _split_into_chunks

    text = "\n".join(f"linea {i}" for i in range(100))
    chunks = _split_into_chunks(text, max_chars=200)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 200 + 20  # tolerancia por la ultima linea que entra completa


def test_split_into_chunks_keeps_short_text_as_one_chunk():
    from rules.llm_extractor import _split_into_chunks

    chunks = _split_into_chunks("una linea corta", max_chars=2500)
    assert chunks == ["una linea corta"]


def test_prompts_build_document_messages():
    from rules.prompts import build_document_messages

    msgs = build_document_messages("documento completo de ejemplo")
    assert len(msgs) == 2
    assert "regla" in msgs[0]["content"].lower()
    assert "documento completo de ejemplo" in msgs[1]["content"]


def test_real_rules_json_validates_with_schema():
    schema = json.loads(Path("rules/schema.json").read_text(encoding="utf-8"))
    payload = json.loads(Path("rules/rules.json").read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def test_is_available_returns_false_without_litellm(monkeypatch):
    """Si litellm no esta instalado, is_available() retorna False aunque haya Ollama."""
    from rules import llm_extractor

    monkeypatch.setattr(llm_extractor, "litellm", None)
    assert llm_extractor.is_available() is False


def test_is_available_detects_ollama_via_localhost(monkeypatch):
    """Si no hay API keys pero Ollama responde en localhost, is_available() retorna True."""
    from rules import llm_extractor

    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "MODEL_API_KEY",
        "LITELLM_API_KEY",
        "LITELLM_API_BASE",
        "MODEL_API_BASE",
        "OLLAMA_API_BASE",
    ):
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setattr(llm_extractor, "_ollama_reachable", lambda base, timeout=1.5: True)
    assert llm_extractor.is_available() is True


def test_is_available_detects_ollama_via_env_var(monkeypatch):
    """Si OLLAMA_API_BASE esta seteada, is_available() retorna True sin verificar conectividad."""
    from rules import llm_extractor

    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "MODEL_API_KEY",
        "LITELLM_API_KEY",
        "LITELLM_API_BASE",
        "MODEL_API_BASE",
    ):
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setenv("OLLAMA_API_BASE", "http://example.test:11434")
    called = {"ping": 0}

    def fake_ping(base, timeout=1.5):
        called["ping"] += 1
        return True

    monkeypatch.setattr(llm_extractor, "_ollama_reachable", fake_ping)
    assert llm_extractor.is_available() is True
    assert called["ping"] == 0


def test_is_ollama_model():
    from rules.llm_extractor import _is_ollama_model

    assert _is_ollama_model("ollama/qwen2.5-coder:14b") is True
    assert _is_ollama_model("ollama/gemma3:4b") is True
    assert _is_ollama_model("http://localhost:11434/api/generate") is True
    assert _is_ollama_model("gemini/gemma-4-26b-a4b-it") is False
    assert _is_ollama_model("gpt-4o-mini") is False


def test_default_call_uses_ollama_without_api_key(monkeypatch):
    """_default_call para ollama/* no requiere API key."""
    from rules import llm_extractor

    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "MODEL_API_KEY",
        "LITELLM_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setattr(llm_extractor, "_ollama_reachable", lambda base, timeout=2.0: True)

    captured = {}

    def fake_native(messages, model, timeout):
        captured["model"] = model
        captured["timeout"] = timeout
        captured["messages"] = messages
        return json.dumps({"rules": [MOCK_RULE]})

    monkeypatch.setattr(llm_extractor, "_ollama_native_call", fake_native)
    out = llm_extractor._default_call(
        [{"role": "user", "content": "hi"}],
        "ollama/qwen2.5-coder:14b",
        30.0,
    )
    assert captured["model"] == "ollama/qwen2.5-coder:14b"
    assert captured["timeout"] == 30.0
    assert json.loads(out)["rules"][0]["title"] == MOCK_RULE["title"]


def test_default_call_uses_litellm_for_cloud(monkeypatch):
    """_default_call para cloud (no ollama) usa litellm.completion."""
    from rules import llm_extractor

    monkeypatch.setenv("GOOGLE_API_KEY", "fake-google-key")

    captured = {}

    class Choice:
        class message:
            content = '{"rules": []}'

    class Resp:
        choices = [Choice()]

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return Resp()

    monkeypatch.setattr(llm_extractor.litellm, "completion", fake_completion)
    out = llm_extractor._default_call(
        [{"role": "user", "content": "hi"}],
        "gemini/gemini-2.5-flash",
        30.0,
    )
    assert captured["api_key"] == "fake-google-key"
    assert captured["model"] == "gemini/gemini-2.5-flash"
    assert "api_base" not in captured
    assert json.loads(out)["rules"] == []


def test_default_call_does_not_ping_ollama_per_call(monkeypatch):
    """_default_call NO hace health check de Ollama por llamada (Ollama es serial en CPU).

    Antes habia un ping a /api/tags que fallaba durante una llamada en curso.
    Ahora confiamos en el timeout del request para detectar fallos.
    """
    from rules import llm_extractor

    for k in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    ping_calls = {"count": 0}

    def fake_ping(base, timeout=1.5):
        ping_calls["count"] += 1
        return False  # simular Ollama no respondiendo al ping

    def fake_native(messages, model, timeout):
        return json.dumps({"rules": [MOCK_RULE]})

    monkeypatch.setattr(llm_extractor, "_ollama_reachable", fake_ping)
    monkeypatch.setattr(llm_extractor, "_ollama_native_call", fake_native)

    out = llm_extractor._default_call(
        [{"role": "user", "content": "hi"}],
        "ollama/qwen2.5-coder:14b",
        30.0,
    )
    assert json.loads(out)["rules"][0]["title"] == MOCK_RULE["title"]
    assert ping_calls["count"] == 0  # NO se hizo ping


def test_default_model_points_to_ollama():
    """El default del proyecto es Ollama local (gratis y privado)."""
    from rules.llm_extractor import DEFAULT_MODEL

    assert DEFAULT_MODEL.startswith("ollama/"), f"Expected Ollama default, got: {DEFAULT_MODEL}"


def test_is_minimax_model():
    from rules.llm_extractor import _is_minimax_model

    assert _is_minimax_model("minimax/MiniMax-M3") is True
    assert _is_minimax_model("minimax/MiniMax-M2.5") is True
    assert _is_minimax_model("MiniMax/MiniMax-M3") is True
    assert _is_minimax_model("ollama/gemma3:4b") is False
    assert _is_minimax_model("gemini/gemini-2.5-flash") is False
    assert _is_minimax_model("gpt-4o-mini") is False


def test_is_available_detects_minimax_via_api_key(monkeypatch):
    """Si MINIMAX_API_KEY esta seteada, is_available() retorna True."""
    from rules import llm_extractor

    for k in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY",
        "MODEL_API_KEY", "LITELLM_API_KEY", "LITELLM_API_BASE", "MODEL_API_BASE",
        "OLLAMA_API_BASE",
    ):
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setattr(llm_extractor, "_ollama_reachable", lambda base, timeout=1.5: False)
    monkeypatch.setenv("MINIMAX_API_KEY", "fake-minimax-key")
    assert llm_extractor.is_available() is True


def test_resolve_minimax_api_base_defaults_to_international(monkeypatch):
    """Sin env vars, MiniMax usa api.minimax.io (internacional)."""
    from rules import llm_extractor

    for k in ("MINIMAX_API_BASE", "MINIMAX_USE_CHINA"):
        monkeypatch.delenv(k, raising=False)

    assert llm_extractor._resolve_minimax_api_base() == "https://api.minimax.io/v1"


def test_resolve_minimax_api_base_china(monkeypatch):
    """Si MINIMAX_USE_CHINA=1, usa api.minimaxi.com."""
    from rules import llm_extractor

    monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
    monkeypatch.setenv("MINIMAX_USE_CHINA", "1")
    assert llm_extractor._resolve_minimax_api_base() == "https://api.minimaxi.com/v1"


def test_resolve_minimax_api_base_explicit_override(monkeypatch):
    """MINIMAX_API_BASE explicita gana sobre el default."""
    from rules import llm_extractor

    monkeypatch.setenv("MINIMAX_API_BASE", "https://custom.example.com/v1")
    monkeypatch.setenv("MINIMAX_USE_CHINA", "1")  # deberia ser ignorado
    assert llm_extractor._resolve_minimax_api_base() == "https://custom.example.com/v1"


def test_default_call_routes_minimax_via_litellm(monkeypatch):
    """_default_call para minimax/* usa litellm con api_key y api_base correctos."""
    from rules import llm_extractor

    monkeypatch.setenv("MINIMAX_API_KEY", "fake-minimax-key")
    monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
    monkeypatch.delenv("MINIMAX_USE_CHINA", raising=False)

    captured = {}

    class Choice:
        class message:
            content = '{"rules": []}'

    class Resp:
        choices = [Choice()]

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return Resp()

    monkeypatch.setattr(llm_extractor.litellm, "completion", fake_completion)
    out = llm_extractor._default_call(
        [{"role": "user", "content": "hi"}],
        "minimax/MiniMax-M3",
        30.0,
    )
    assert captured["api_key"] == "fake-minimax-key"
    assert captured["api_base"] == "https://api.minimax.io/v1"
    assert captured["model"] == "minimax/MiniMax-M3"
    assert json.loads(out)["rules"] == []


def test_default_call_raises_when_minimax_missing_api_key(monkeypatch):
    """Si el modelo es MiniMax pero no hay MINIMAX_API_KEY, levanta RuntimeError claro."""
    from rules import llm_extractor

    for k in ("MINIMAX_API_KEY", "MINIMAX_GROUP_ID"):
        monkeypatch.delenv(k, raising=False)

    try:
        llm_extractor._default_call(
            [{"role": "user", "content": "hi"}],
            "minimax/MiniMax-M3",
            30.0,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as exc:
        assert "MINIMAX_API_KEY" in str(exc)
