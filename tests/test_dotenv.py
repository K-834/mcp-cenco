"""Tests para `rules._dotenv` (carga de `.env`)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rules._dotenv import load_dotenv


@pytest.fixture
def clean_env(monkeypatch):
    """Limpia todas las env vars que los tests van a usar."""
    for k in (
        "DOTENV_TEST_VAR",
        "DOTENV_QUOTED_VAR",
        "DOTENV_EMPTY_VAR",
        "DOTENV_COMMENT_VAR",
        "DOTENV_PRESET_VAR",
    ):
        monkeypatch.delenv(k, raising=False)


def test_load_dotenv_returns_zero_when_no_file(tmp_path, clean_env, monkeypatch):
    """Sin path y sin `.env` en cwd ni en la raiz del modulo, retorna 0."""
    monkeypatch.chdir(tmp_path)
    # Si hay `.env` en la raiz del proyecto, no podemos testear este caso;
    # necesitamos un path explicito que apunte a un archivo inexistente.
    nonexistent = tmp_path / "no-existe.env"
    assert load_dotenv(nonexistent) == 0


def test_load_dotenv_basic(clean_env, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DOTENV_TEST_VAR=hello\n", encoding="utf-8")
    assert load_dotenv(env_file) == 1
    assert os.environ["DOTENV_TEST_VAR"] == "hello"


def test_load_dotenv_handles_double_quotes(clean_env, tmp_path):
    (tmp_path / ".env").write_text(
        'DOTENV_TEST_VAR="hello world"\n', encoding="utf-8"
    )
    load_dotenv(tmp_path / ".env")
    assert os.environ["DOTENV_TEST_VAR"] == "hello world"


def test_load_dotenv_handles_single_quotes(clean_env, tmp_path):
    (tmp_path / ".env").write_text(
        "DOTENV_TEST_VAR='hello world'\n", encoding="utf-8"
    )
    load_dotenv(tmp_path / ".env")
    assert os.environ["DOTENV_TEST_VAR"] == "hello world"


def test_load_dotenv_skips_comments_and_blank_lines(clean_env, tmp_path):
    (tmp_path / ".env").write_text(
        "# esto es un comentario\n"
        "\n"
        "DOTENV_TEST_VAR=valor\n"
        "# DOTENV_COMMENT_VAR=deberia ignorarse\n",
        encoding="utf-8",
    )
    n = load_dotenv(tmp_path / ".env")
    assert n == 1
    assert os.environ["DOTENV_TEST_VAR"] == "valor"
    assert "DOTENV_COMMENT_VAR" not in os.environ


def test_load_dotenv_skips_empty_values(clean_env, tmp_path):
    """Valores vacios NO sobreescriben (preserva el del shell)."""
    (tmp_path / ".env").write_text(
        "DOTENV_EMPTY_VAR=\n"
        "DOTENV_TEST_VAR=set\n",
        encoding="utf-8",
    )
    load_dotenv(tmp_path / ".env")
    assert os.environ["DOTENV_TEST_VAR"] == "set"
    assert "DOTENV_EMPTY_VAR" not in os.environ


def test_load_dotenv_does_not_override_existing(monkeypatch, tmp_path):
    """Si la env var ya esta seteada en el shell, .env NO la sobreescribe."""
    monkeypatch.setenv("DOTENV_PRESET_VAR", "from-shell")
    (tmp_path / ".env").write_text(
        "DOTENV_PRESET_VAR=from-file\n", encoding="utf-8"
    )
    load_dotenv(tmp_path / ".env")
    assert os.environ["DOTENV_PRESET_VAR"] == "from-shell"


def test_load_dotenv_override_true_overrides_existing(monkeypatch, tmp_path):
    """Con override=True, .env SI sobreescribe."""
    monkeypatch.setenv("DOTENV_PRESET_VAR", "from-shell")
    (tmp_path / ".env").write_text(
        "DOTENV_PRESET_VAR=from-file\n", encoding="utf-8"
    )
    load_dotenv(tmp_path / ".env", override=True)
    assert os.environ["DOTENV_PRESET_VAR"] == "from-file"


def test_load_dotenv_finds_project_env(monkeypatch, tmp_path, clean_env):
    """Sin path explicito, busca `.env` en cwd y luego junto al modulo."""
    env_file = tmp_path / ".env"
    env_file.write_text("DOTENV_TEST_VAR=autodetect\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_dotenv() == 1
    assert os.environ["DOTENV_TEST_VAR"] == "autodetect"


def test_load_dotenv_loads_real_project_env_if_present():
    """Si `.env` existe en la raiz del proyecto, se carga sin path explicito.

    No verificamos el contenido exacto (puede tener keys reales del usuario);
    solo que carga >= 1 variable cuando hay vars en .env que no estan en os.environ.
    """
    project_env = Path(__file__).parent.parent / ".env"
    if not project_env.exists():
        pytest.skip("No hay .env en la raiz del proyecto")
    # Pop TODO lo que .env podria contener (incluido lo que scripts/run.py carga al importar).
    # Asi garantizamos que al menos 1 var sera efectivamente cargada.
    for k in (
        "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "MINIMAX_API_KEY", "MINIMAX_API_BASE",
        "REDSHIFT_HOST", "REDSHIFT_PORT", "REDSHIFT_DATABASE",
        "REDSHIFT_USER", "REDSHIFT_PASSWORD", "REDSHIFT_SCHEMA",
    ):
        os.environ.pop(k, None)
    n = load_dotenv()
    assert n >= 1


def test_load_dotenv_handles_malformed_lines(clean_env, tmp_path):
    """Lineas sin `=` se ignoran sin error."""
    (tmp_path / ".env").write_text(
        "esto no es una linea valida\n"
        "DOTENV_TEST_VAR=ok\n",
        encoding="utf-8",
    )
    n = load_dotenv(tmp_path / ".env")
    assert n == 1
    assert os.environ["DOTENV_TEST_VAR"] == "ok"
