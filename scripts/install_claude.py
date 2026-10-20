"""Instala (o desinstala) el MCP server de Power BI en clientes Claude.

Subcomandos:

    install-desktop  copia el config a %APPDATA%/Claude/claude_desktop_config.json
    install-code     agrega el server via `claude mcp add` (Claude Code CLI)
    install-all      instala en ambos
    uninstall        elimina la entrada `powerbi-mcp` de los configs
    status           muestra si esta instalado y donde

Usa la misma config que `clients/claude_desktop.mcp.json` y
`clients/claude_code.mcp.json`.

Nota: el proyecto debe estar clonado en la ruta que el config apunta. Si lo
moviste, edita PROJECT_ROOT abajo antes de correr.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_PATH = str(ROOT).replace("\\", "/")
# Usa el entry point `powerbi-mcp` declarado en pyproject.toml
# (`server.mcp_server:main`). Esto evita depender del cwd al lanzar el server,
# que era el bug original: Claude Desktop lanzaba `python server/mcp_server.py`
# desde su propio directorio de instalacion y el path relativo fallaba con
# `FileNotFoundError`. El entry point se resuelve via el venv de uv.
SERVER_ARGS = [
    "run",
    "--project",
    PROJECT_PATH,
    "powerbi-mcp",
]


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _claude_desktop_config_path() -> Path | None:
    """Path a claude_desktop_config.json segun OS."""
    if _is_windows():
        return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _server_entry() -> dict:
    """Bloque MCP server reusable, compatible con Claude Desktop y Claude Code."""
    return {
        "command": "uv",
        "args": SERVER_ARGS,
    }


def _server_entry_code() -> dict:
    """Bloque para Claude Code CLI (incluye `env` por compat)."""
    entry = _server_entry()
    entry["env"] = {}
    return entry


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[WARN] {path} no es JSON valido. Backup y reescribiendo.", file=sys.stderr)
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_install_desktop() -> int:
    target = _claude_desktop_config_path()
    if target is None:
        print("[ERROR] OS no soportado para Claude Desktop.", file=sys.stderr)
        return 1

    config = _read_json(target)
    servers = config.get("mcpServers") or config.get("mcp_servers") or {}
    if "powerbi-mcp" in servers:
        print(f"  [=] Ya instalado en {target}")
    else:
        servers["powerbi-mcp"] = _server_entry()
        config["mcpServers"] = servers
        _write_json(target, config)
        print(f"  [+] Instalado en {target}")

    print()
    print("  Reinicia Claude Desktop para que tome el cambio (hamburguesa > Quit).")
    return 0


def cmd_install_code() -> int:
    """Usa `claude mcp add` (subcomando oficial de Claude Code CLI)."""
    cmd = [
        "claude", "mcp", "add", "powerbi-mcp",
        "--command", "uv",
        "--args", "run", "--project", PROJECT_PATH, "powerbi-mcp",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  [+] Agregado via 'claude mcp add': {result.stdout.strip()}")
        else:
            print(f"  [!] 'claude mcp add' fallo: {result.stderr.strip()}", file=sys.stderr)
            print("  Verifica que Claude Code CLI esta instalado: https://claude.com/claude-code", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print("[ERROR] 'claude' CLI no esta en PATH. Instala Claude Code primero.", file=sys.stderr)
        return 1

    print()
    print("  El server ya esta disponible. Claude Code lo levanta on-demand al primer uso.")
    return 0


def cmd_install_all() -> int:
    rc1 = cmd_install_desktop()
    print()
    rc2 = cmd_install_code()
    return 0 if (rc1 == 0 and rc2 == 0) else 1


def cmd_uninstall() -> int:
    rc = 0

    target = _claude_desktop_config_path()
    if target and target.exists():
        config = _read_json(target)
        servers = config.get("mcpServers") or {}
        if "powerbi-mcp" in servers:
            del servers["powerbi-mcp"]
            config["mcpServers"] = servers
            _write_json(target, config)
            print(f"  [-] Removido de {target}")
        else:
            print(f"  [=] No estaba en {target}")

    try:
        result = subprocess.run(
            ["claude", "mcp", "remove", "powerbi-mcp"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  [-] Removido de Claude Code CLI")
        else:
            if "not found" in result.stderr.lower() or "no encontrado" in result.stdout.lower():
                print(f"  [=] No estaba registrado en Claude Code CLI")
            else:
                print(f"  [!] 'claude mcp remove' fallo: {result.stderr.strip()}", file=sys.stderr)
                rc = 1
    except FileNotFoundError:
        pass

    return rc


def cmd_status() -> int:
    print("\n=== Estado de instalacion Claude ===\n")

    target = _claude_desktop_config_path()
    if target and target.exists():
        config = _read_json(target)
        servers = config.get("mcpServers") or {}
        if "powerbi-mcp" in servers:
            print(f"  [OK] Claude Desktop: instalado en {target}")
            print(f"        command: {servers['powerbi-mcp'].get('command')}")
        else:
            print(f"  [--] Claude Desktop: NO instalado (config existe en {target})")
    else:
        print(f"  [--] Claude Desktop: NO instalado (no se encontro config)")

    try:
        result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True)
        if result.returncode == 0 and "powerbi-mcp" in result.stdout:
            print(f"  [OK] Claude Code CLI: registrado")
        else:
            print(f"  [--] Claude Code CLI: NO registrado")
    except FileNotFoundError:
        print(f"  [--] Claude Code CLI: 'claude' no esta en PATH")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instala/desinstala el MCP server en clientes Claude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install-desktop", help="copia config a Claude Desktop")
    sub.add_parser("install-code", help="agrega via 'claude mcp add'")
    sub.add_parser("install-all", help="instala en ambos")
    sub.add_parser("uninstall", help="remueve la entrada powerbi-mcp")
    sub.add_parser("status", help="muestra donde esta instalado")

    args = parser.parse_args()
    dispatch = {
        "install-desktop": cmd_install_desktop,
        "install-code": cmd_install_code,
        "install-all": cmd_install_all,
        "uninstall": cmd_uninstall,
        "status": cmd_status,
    }
    return dispatch[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())