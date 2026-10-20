"""Ejecuta las operaciones habituales del proyecto con un solo comando.

Subcomandos disponibles:

    setup         uv sync (deps + dev)
    compile       regenera rules.json desde el PDF/DOCX de docs/reglas-mcp/ (requiere LLM)
    sync          sincroniza el skill a .opencode/skills/ y ~/.config/opencode/skills/
    test          corre la suite de pytest
    server-check  arranca el server MCP unos segundos para validar el handshake
    all           setup + compile + sync + test (lo mas comun)
    status        muestra que esta actualizado y que no

`compile` siempre usa el extractor LLM (no hay modo regex): por defecto Ollama
local (gratis, ver docs/proyecto/ollama-setup.md), o una API key cloud si la
seteaste. Si no hay ningun LLM disponible, `compile`/`all` fallan con un
mensaje claro en vez de degradar en calidad.

Ejemplos:
    uv run scripts/run.py all
    uv run scripts/run.py test
    uv run scripts/run.py compile --llm-model ollama/qwen2.5-coder:14b
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from rules._dotenv import load_dotenv  # noqa: E402

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ["uv", "run", "--no-sync", "python"]



def _run(cmd: list[str], **kwargs) -> int:
    """Ejecuta un comando y muestra que esta corriendo. Falla si retorna != 0."""
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(ROOT), **kwargs).returncode


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _err(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)


def cmd_setup() -> int:
    rc = _run(["uv", "sync", "--group", "dev"])
    if rc != 0:
        return rc
    _ok("Dependencias instaladas (.venv/)")
    return 0


def cmd_setup_microsoft() -> int:
    """Descarga los 5 skills oficiales de microsoft/skills-for-fabric."""
    rc = _run([*PYTHON, "scripts/setup_microsoft_skills.py"])
    if rc == 0:
        _ok("5 skills de microsoft descargados a .opencode/skills/")
        _ok("Ahora corre `uv run scripts/run.py sync` para propagarlos a global.")
    return rc


def cmd_compile(args: argparse.Namespace) -> int:
    cmd = [*PYTHON, "rules/compile_rules.py"]
    if args.llm_model:
        cmd.extend(["--llm-model", args.llm_model])
    rc = _run(cmd)
    if rc == 0:
        _ok("rules.json regenerado")
    return rc


def cmd_sync() -> int:
    rc = _run([*PYTHON, "scripts/sync_skill.py"])
    if rc == 0:
        _ok("Skill sincronizado a .opencode/skills/ y ~/.config/opencode/skills/")
    return rc


def cmd_test() -> int:
    return _run(["uv", "run", "pytest"])


def cmd_server_check() -> int:
    print("\n>>> Lanzando server MCP (3 segundos de prueba)...")
    proc = subprocess.Popen(
        [*PYTHON, "-m", "server.mcp_server"],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    proc.terminate()
    try:
        _, err = proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, err = proc.communicate()

    stderr_text = err.decode("utf-8", errors="replace")
    if "ModuleNotFoundError" in stderr_text or "ImportError" in stderr_text:
        _err("Server no arranco. Revisa `uv sync`.")
        return 1
    if stderr_text.strip():
        print(f"  stderr (informativo): {stderr_text[:300]}")
    _ok("Server arranco y esperaba stdin (handshake MCP OK)")
    return 0


def cmd_server_lan(args: argparse.Namespace) -> int:
    print(f"\n>>> Lanzando servidor MCP en la LAN (http://{args.host}:{args.port}{args.path})...")
    print("Presiona Ctrl+C para detener el servidor.\n")
    return _run([
        *PYTHON,
        "-m",
        "server.mcp_server",
        "--transport",
        "streamable-http",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--path",
        args.path,
    ])




def cmd_claude(args: argparse.Namespace) -> int:
    """Delega a scripts/install_claude.py."""
    sub = ["status", "install-desktop", "install-code", "install-all", "uninstall"]
    if args.claude_action not in sub:
        print(f"[ERROR] Subcomando desconocido: {args.claude_action}. Opciones: {', '.join(sub)}", file=sys.stderr)
        return 1
    rc = _run([*PYTHON, "scripts/install_claude.py", args.claude_action])
    if rc == 0:
        _ok(f"Operacion Claude ({args.claude_action}) completada")
    return rc


def cmd_status() -> int:
    print("\n=== Estado del proyecto ===\n")

    pyproject = ROOT / "pyproject.toml"
    rules = ROOT / "rules" / "rules.json"
    canonical_skill = ROOT / "docs" / "agent" / "SKILL_POWER_BI.md"
    legacy_skill = ROOT / "docs" / "SKILL_POWER_BI.md"
    local_skill = ROOT / ".opencode" / "skills" / "logica-bi-pbip-cenco" / "SKILL.md"
    global_skill = Path.home() / ".config" / "opencode" / "skills" / "logica-bi-pbip-cenco" / "SKILL.md"


    checks = [
        ("pyproject.toml", pyproject.exists()),
        ("uv.lock", (ROOT / "uv.lock").exists()),
        (".venv/", (ROOT / ".venv").exists()),
        ("rules.json", rules.exists()),
        ("docs/agent/SKILL_POWER_BI.md", canonical_skill.exists()),
        (".opencode/skills/.../SKILL.md", local_skill.exists()),
        ("~/.config/opencode/skills/.../SKILL.md", global_skill.exists()),
        (".vscode/mcp.json", (ROOT / ".vscode" / "mcp.json").exists()),
    ]
    for name, ok in checks:
        marker = "[OK]" if ok else "[--]"
        print(f"  {marker:6s} {name}")

    if rules.exists() and rules.stat().st_mtime < pyproject.stat().st_mtime:
        _warn("rules.json es mas viejo que pyproject.toml. Considera regenerar con `compile`.")

    if canonical_skill.exists() and local_skill.exists():
        import hashlib
        h1 = hashlib.sha256(canonical_skill.read_bytes()).hexdigest()[:8]
        h2 = hashlib.sha256(local_skill.read_bytes()).hexdigest()[:8]
        if h1 != h2:
            _warn(f"docs/agent/SKILL ({h1}) y .opencode/skills/.../SKILL ({h2}) difieren. Correr `sync`.")
        else:
            _ok(f"docs/agent/SKILL y .opencode/skills sincronizados ({h1})")

    if legacy_skill.exists():
        _warn("docs/SKILL_POWER_BI.md (legacy) aun existe. Es duplicado del canonico en docs/agent/. Borrar o migrar.")

    return 0


def _llm_available() -> bool:
    """True si hay litellm y al menos una API key seteada."""
    try:
        from rules.llm_extractor import is_available
        return is_available()
    except ImportError:
        return False


def cmd_all() -> int:
    """Setup + compile + sync + test.

    `compile` siempre requiere un LLM (no hay modo regex). Si no hay ninguno
    disponible (Ollama apagado y sin API key), `all` falla aca mismo con un
    mensaje claro en vez de compilar reglas de menor calidad en silencio.
    """
    if not _llm_available():
        _err("Sin LLM disponible (Ollama apagado y sin API key). `compile` lo requiere.")
        _err("Arranca Ollama local (ver docs/proyecto/ollama-setup.md) o define una API key.")
        return 1

    try:
        from rules.llm_extractor import _is_ollama_model, _resolve_model
        using_ollama = _is_ollama_model(_resolve_model())
    except ImportError:
        using_ollama = False
    if using_ollama:
        print("  [INFO] Modo LLM activado (Ollama local)", file=sys.stderr)
    else:
        print("  [INFO] Modo LLM activado (cloud API)", file=sys.stderr)

    compile_fn = lambda: cmd_compile(argparse.Namespace(llm_model=None))
    for fn in (cmd_setup, compile_fn, cmd_sync, cmd_test):
        rc = fn()
        if rc != 0:
            return rc
    _ok("Todo verde. Listo para usar.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta operaciones del proyecto powerbi-mcp-agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="uv sync --group dev")
    sub.add_parser("sync", help="sincroniza skills a .opencode/ y ~/.config/")
    sub.add_parser("test", help="corre la suite de pytest")
    sub.add_parser("server-check", help="lanza el server unos segundos y valida")
    sub.add_parser("status", help="muestra que esta actualizado")
    sub.add_parser("all", help="setup + setup-microsoft + compile + sync + test")
    sub.add_parser("setup-microsoft", help="descarga los 5 skills oficiales de microsoft/skills-for-fabric")

    p_lan = sub.add_parser("server-lan", help="lanza el servidor MCP en transporte HTTP para la LAN (0.0.0.0:8000)")
    p_lan.add_argument("--host", default="0.0.0.0", help="host donde escuchar (default: 0.0.0.0)")
    p_lan.add_argument("--port", type=int, default=8000, help="puerto (default: 8000)")
    p_lan.add_argument("--path", default="/mcp", help="endpoint path (default: /mcp)")

    p_compile = sub.add_parser("compile", help="regenera rules.json desde docs/reglas-mcp/ (via LLM)")
    p_compile.add_argument("--llm-model", default=None, help="modelo para litellm/Ollama")

    p_claude = sub.add_parser("claude", help="instala/desinstala en Claude Desktop/Code")
    p_claude.add_argument("claude_action", choices=[
        "install-desktop", "install-code", "install-all", "uninstall", "status",
    ], help="accion a ejecutar")

    args = parser.parse_args()

    dispatch = {
        "setup": lambda a: cmd_setup(),
        "setup-microsoft": lambda a: cmd_setup_microsoft(),
        "sync": lambda a: cmd_sync(),
        "test": lambda a: cmd_test(),
        "server-check": lambda a: cmd_server_check(),
        "server-lan": cmd_server_lan,
        "status": lambda a: cmd_status(),
        "all": lambda a: cmd_all(),
        "compile": cmd_compile,
        "claude": cmd_claude,
    }
    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        return 1
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
