"""Standalone Single-File Installer para Claude (PowerBI MCP & Skills).

Este script descarga el repositorio desde GitHub (o usa el local si existe),
instala las dependencias y configura automaticamente tanto el Servidor MCP
como todas las Skills de Power BI en Claude Desktop y Claude Code.

Uso rapido en 1 sola linea desde PowerShell (Windows):
    irm https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/setup_claude.py | python -

O descargando el archivo y haciendo doble clic / ejecutando:
    python setup_claude.py
"""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

# Repositorio oficial en GitHub
GITHUB_REPO_URL = "https://github.com/K-834/mcp-cenco"
DEFAULT_INSTALL_DIR = Path.home() / ".powerbi-mcp-agent"

# Skills oficiales de Microsoft a descargar
MS_BASE = "https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/plugins/powerbi-authoring/skills"
MICROSOFT_SKILLS = [
    ("powerbi-report-authoring", f"{MS_BASE}/powerbi-report-authoring/SKILL.md"),
    ("powerbi-report-design", f"{MS_BASE}/powerbi-report-design/SKILL.md"),
    ("powerbi-report-planning", f"{MS_BASE}/powerbi-report-planning/SKILL.md"),
    ("powerbi-report-management", f"{MS_BASE}/powerbi-report-management/SKILL.md"),
    ("semantic-model-authoring", f"{MS_BASE}/semantic-model-authoring/SKILL.md"),
]


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


def get_claude_skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


def check_and_install_uv() -> bool:
    if shutil.which("uv"):
        return True

    print("[*] 'uv' no encontrado en el sistema. Instalando automaticamente...")
    try:
        if is_windows():
            cmd = "powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
            subprocess.run(cmd, shell=True, check=True)
            # Agregar ruta al PATH en sesion actual
            uv_path = Path.home() / ".local" / "bin"
            if uv_path.exists():
                os.environ["PATH"] = str(uv_path) + os.pathsep + os.environ["PATH"]
        else:
            cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            subprocess.run(cmd, shell=True, check=True)
            uv_path = Path.home() / ".local" / "bin"
            if uv_path.exists():
                os.environ["PATH"] = str(uv_path) + os.pathsep + os.environ["PATH"]
        return shutil.which("uv") is not None
    except Exception as e:
        print(f"[!] No se pudo instalar 'uv' automaticamente: {e}")
        return False


def get_target_repo_dir() -> Path:
    current_dir = Path(__file__).resolve().parent
    if (current_dir / "pyproject.toml").exists() and (current_dir / "server").exists():
        return current_dir
    return DEFAULT_INSTALL_DIR


def download_repo_zip(target_dir: Path, repo_url: str) -> bool:
    if (target_dir / "pyproject.toml").exists():
        print(f"[*] Repositorio ya disponible en: {target_dir}")
        return True

    print(f"[*] Descargando codigo fuente desde GitHub a: {target_dir}...")
    zip_url = f"{repo_url.rstrip('/')}/archive/refs/heads/main.zip"
    try:
        req = Request(zip_url, headers={"User-Agent": "PowerBI-MCP-Installer"})
        with urlopen(req) as resp:
            zip_bytes = resp.read()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # Extraer removiendo el prefijo repo-main/
            for member in z.infolist():
                parts = member.filename.split("/", 1)
                if len(parts) > 1 and parts[1]:
                    dest_file = target_dir / parts[1]
                    if member.is_dir():
                        dest_file.mkdir(parents=True, exist_ok=True)
                    else:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(dest_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        print("  [+] Codigo descargado y extraido con exito.")
        return True
    except Exception as e:
        print(f"[!] Error descargando desde {zip_url}: {e}")
        return False


def install_mcp_config(project_path: Path) -> None:
    path = get_claude_desktop_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    norm_path = str(project_path).replace("\\", "/")

    entry = {
        "command": "uv",
        "args": [
            "run",
            "--project",
            norm_path,
            "powerbi-mcp",
        ],
    }

    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    servers = data.setdefault("mcpServers", {})
    servers["powerbi-mcp"] = entry
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  [+] Servidor MCP configurado en Claude Desktop: {path}")

    # Configurar en Claude Code si ~/.claude.json existe
    claude_code_json = Path.home() / ".claude.json"
    if claude_code_json.exists():
        try:
            code_data = json.loads(claude_code_json.read_text(encoding="utf-8"))
            code_servers = code_data.setdefault("mcpServers", {})
            code_servers["powerbi-mcp"] = {"command": "uv", "args": entry["args"], "env": {}}
            claude_code_json.write_text(json.dumps(code_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  [+] Servidor MCP configurado en Claude Code: {claude_code_json}")
        except Exception:
            pass


def install_skills(project_path: Path) -> None:
    skills_dir = get_claude_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    print("\n[*] Instalando Skills de Power BI en Claude...")

    # 1. Copiar skills locales desde el repositorio
    local_skills_dir = project_path / "skills"
    if local_skills_dir.exists():
        for skill_folder in local_skills_dir.iterdir():
            if skill_folder.is_dir() and (skill_folder / "SKILL.md").exists():
                dest = skills_dir / skill_folder.name
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_folder / "SKILL.md", dest / "SKILL.md")
                print(f"  [+] Skill instalada: {skill_folder.name}")
    else:
        # Fallback si se ejecuta de forma remota sin repo clonado todavia: descargar de Microsoft
        for slug, url in MICROSOFT_SKILLS:
            try:
                dest = skills_dir / slug / "SKILL.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                req = Request(url, headers={"User-Agent": "PowerBI-Installer"})
                with urlopen(req) as resp:
                    dest.write_bytes(resp.read())
                print(f"  [+] Skill oficial descargada: {slug}")
            except Exception as e:
                print(f"  [-] Error descargando skill {slug}: {e}")


def main() -> None:
    print("=" * 65)
    print("  INSTALADOR 1-CLIC: PowerBI MCP Agent & Skills para Claude")
    print("=" * 65)

    # 1. Verificar uv
    check_and_install_uv()

    # 2. Obtener o descargar el repositorio
    repo_dir = get_target_repo_dir()
    if not (repo_dir / "pyproject.toml").exists():
        download_repo_zip(repo_dir, GITHUB_REPO_URL)

    # 3. Sincronizar entorno virtual con uv
    if shutil.which("uv"):
        print("\n[*] Sincronizando dependencias del MCP server...")
        try:
            subprocess.run(["uv", "sync", "--project", str(repo_dir)], check=True)
            print("  [+] Dependencias instaladas correctamente.")
        except Exception as e:
            print(f"  [!] Advertencia al correr uv sync: {e}")

    # 4. Configurar MCP y Skills
    install_mcp_config(repo_dir)
    install_skills(repo_dir)

    print("\n" + "=" * 65)
    print("  INSTALACION COMPLETADA CON EXITO!")
    print("  Ya puedes abrir o reiniciar Claude Desktop o Claude Code.")
    print("=" * 65)

    if is_windows() and "PROMPT" not in os.environ:
        input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    main()
