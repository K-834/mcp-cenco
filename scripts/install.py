"""Instalador integral dedicado exclusivamente para Claude (Desktop y Claude Code CLI).

Configura automaticamente:
1. Servidor MCP de Power BI en Claude Desktop (claude_desktop_config.json)
2. Servidor MCP en Claude Code CLI (claude mcp add / ~/.claude.json)
3. Instalacion de todas las Skills de Power BI en Claude Code / Agent (~/.claude/skills/)
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


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_mac() -> bool:
    return platform.system() == "Darwin"


def get_claude_desktop_config_path() -> Path:
    if is_windows():
        return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    if is_mac():
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_claude_home_dir() -> Path:
    return Path.home() / ".claude"


def get_claude_skills_dir() -> Path:
    return get_claude_home_dir() / "skills"


def get_mcp_entry() -> dict:
    """Bloque MCP compatible con Claude Desktop."""
    return {
        "command": "uv",
        "args": [
            "run",
            "--project",
            PROJECT_PATH,
            "powerbi-mcp",
        ],
    }


def update_json_file(path: Path, server_name: str, entry: dict) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup)
            print(f"[!] Archivo {path} danado, backup creado en {backup}")
            data = {}

    servers = data.setdefault("mcpServers", {})
    servers[server_name] = entry
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def install_skills_to_claude() -> int:
    """Instala todos los skills de Power BI en ~/.claude/skills/."""
    claude_skills = get_claude_skills_dir()
    claude_skills.mkdir(parents=True, exist_ok=True)

    sources = [
        ROOT / "skills",
        ROOT / ".agents" / "skills",
        ROOT / ".opencode" / "skills",
        ROOT / "docs" / "agent",
    ]

    installed = 0
    copied_slugs = set()

    for base in sources:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists() and item.name not in copied_slugs:
                    dest = claude_skills / item.name
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(skill_md, dest / "SKILL.md")
                    copied_slugs.add(item.name)
                    installed += 1
                    print(f"  [+] Skill instalada en Claude: {item.name}")

    # Asegurar el skill de auditoria local (logica-bi-pbip-cenco)
    local_skill_canonical = ROOT / "docs" / "agent" / "SKILL_POWER_BI.md"
    if local_skill_canonical.exists() and "logica-bi-pbip-cenco" not in copied_slugs:
        dest = claude_skills / "logica-bi-pbip-cenco"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_skill_canonical, dest / "SKILL.md")
        copied_slugs.add("logica-bi-pbip-cenco")
        installed += 1
        print("  [+] Skill instalada en Claude: logica-bi-pbip-cenco")

    return installed


def install_mcp_claude_desktop() -> bool:
    path = get_claude_desktop_config_path()
    try:
        update_json_file(path, "powerbi-mcp", get_mcp_entry())
        print(f"  [+] Servidor MCP configurado en Claude Desktop: {path}")
        return True
    except Exception as e:
        print(f"  [-] Error configurando Claude Desktop: {e}")
        return False


def install_mcp_claude_code() -> bool:
    print("  [*] Configurando Claude Code CLI...")
    entry = get_mcp_entry()
    cmd = ["claude", "mcp", "add", "powerbi-mcp", "--", entry["command"]] + entry["args"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, shell=is_windows())
        if res.returncode == 0:
            print("  [+] Servidor MCP agregado exitosamente a Claude Code CLI.")
            return True
        else:
            # Fallback directo a ~/.claude.json si existe
            user_claude_json = Path.home() / ".claude.json"
            if user_claude_json.exists():
                entry_with_env = get_mcp_entry()
                entry_with_env["env"] = {}
                update_json_file(user_claude_json, "powerbi-mcp", entry_with_env)
                print(f"  [+] Servidor MCP configurado en ~/.claude.json")
                return True
            print("  [-] No se pudo registrar en Claude Code CLI automaticamente.")
            return False
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Instalador de PowerBI MCP Server y Skills para Claude")
    parser.add_argument("--desktop-only", action="store_true", help="Solo configurar Claude Desktop")
    parser.add_argument("--code-only", action="store_true", help="Solo configurar Claude Code CLI")
    args = parser.parse_args()

    print("=" * 65)
    print("PowerBI MCP Agent & Skills para Claude")
    print(f"Repositorio: {PROJECT_PATH}")
    print("=" * 65)

    print("\n[1] Instalando Skills en Claude (~/.claude/skills)...")
    count = install_skills_to_claude()
    print(f"    Total de skills instaladas: {count}")

    print("\n[2] Configurando Servidor MCP en Claude...")
    if not args.code_only:
        install_mcp_claude_desktop()
    if not args.desktop_only:
        install_mcp_claude_code()

    print("\n" + "=" * 65)
    print("Instalacion para Claude completada exitosamente!")
    print("-> Cierra y vuelve a abrir Claude Desktop o Claude Code para activarlo.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
