from __future__ import annotations

from unittest.mock import patch


def _clear_llm_env(monkeypatch):
    """Limpia todas las env vars que hacen is_available() retornar True (incluyendo Ollama)."""
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
        "MINIMAX_API_KEY",
        "MINIMAX_API_BASE",
        "MINIMAX_USE_CHINA",
    ):
        monkeypatch.delenv(k, raising=False)


def test_llm_available_true_when_key_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
    from scripts.run import _llm_available

    assert _llm_available() is True


def test_llm_available_false_when_no_keys(monkeypatch):
    _clear_llm_env(monkeypatch)
    from scripts.run import _llm_available
    from rules import llm_extractor

    with patch.object(llm_extractor, "_ollama_reachable", return_value=False):
        assert _llm_available() is False


def test_all_uses_llm_when_available(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

    from scripts.run import cmd_all

    with patch("scripts.run.cmd_setup", return_value=0) as m_setup, \
         patch("scripts.run.cmd_compile", return_value=0) as m_compile, \
         patch("scripts.run.cmd_sync", return_value=0) as m_sync, \
         patch("scripts.run.cmd_test", return_value=0) as m_test:
        rc = cmd_all()

    assert rc == 0
    m_setup.assert_called_once()
    m_compile.assert_called_once()
    m_sync.assert_called_once()
    m_test.assert_called_once()

    _, stderr = capsys.readouterr()
    assert "Modo LLM activado" in stderr


def test_all_fails_clearly_without_llm(monkeypatch, capsys):
    """Sin LLM disponible, `all` no debe compilar reglas con regex: falla con mensaje claro."""
    _clear_llm_env(monkeypatch)
    from rules import llm_extractor

    with patch.object(llm_extractor, "_ollama_reachable", return_value=False):
        from scripts.run import cmd_all

        with patch("scripts.run.cmd_setup", return_value=0) as m_setup, \
             patch("scripts.run.cmd_compile", return_value=0) as m_compile, \
             patch("scripts.run.cmd_sync", return_value=0), \
             patch("scripts.run.cmd_test", return_value=0):
            rc = cmd_all()

    assert rc != 0
    m_setup.assert_not_called()
    m_compile.assert_not_called()

    _, stderr = capsys.readouterr()
    assert "Sin LLM" in stderr


def test_all_uses_llm_when_ollama_running(monkeypatch, capsys):
    """Si Ollama esta corriendo y no hay API key, _llm_available() retorna True."""
    _clear_llm_env(monkeypatch)
    from rules import llm_extractor

    with patch.object(llm_extractor, "_ollama_reachable", return_value=True):
        from scripts.run import cmd_all

        with patch("scripts.run.cmd_setup", return_value=0), \
             patch("scripts.run.cmd_compile", return_value=0) as m_compile, \
             patch("scripts.run.cmd_sync", return_value=0), \
             patch("scripts.run.cmd_test", return_value=0):
            rc = cmd_all()

    assert rc == 0
    m_compile.assert_called_once()

    _, stderr = capsys.readouterr()
    assert "Ollama" in stderr


def test_all_returns_nonzero_when_step_fails(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

    from scripts.run import cmd_all

    with patch("scripts.run.cmd_setup", return_value=0), \
         patch("scripts.run.cmd_compile", return_value=0), \
         patch("scripts.run.cmd_sync", return_value=0), \
         patch("scripts.run.cmd_test", return_value=1):
        assert cmd_all() == 1
