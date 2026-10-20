"""Descarga los 5 skills oficiales de microsoft/skills-for-fabric (plugin powerbi-authoring).

Los descarga a `.opencode/skills/<slug>/SKILL.md`. El script `sync_skill.py`
los propaga a `~/.config/opencode/skills/` para que esten disponibles
globalmente.

Ejecutar una sola vez (o cuando Microsoft actualice los skills):

    uv run python scripts/setup_microsoft_skills.py
    uv run scripts/run.py sync

Skills descargados:
    - powerbi-report-authoring     (mecanica PBIR + CLI validation)
    - powerbi-report-design        (tone, archetype, layout)
    - powerbi-report-planning      (Define->Inspect->Spec->Approve->Build)
    - powerbi-report-management    (deploy a Fabric via REST)
    - semantic-model-authoring     (TMDL/DAX/Direct Lake/AI readiness)
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / ".opencode" / "skills"

SOURCE_BASE = (
    "https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/"
    "plugins/powerbi-authoring/skills"
)

# (slug de destino, ruta remota del SKILL.md)
SKILLS: list[tuple[str, str]] = [
    ("powerbi-report-authoring", f"{SOURCE_BASE}/powerbi-report-authoring/SKILL.md"),
    ("powerbi-report-design", f"{SOURCE_BASE}/powerbi-report-design/SKILL.md"),
    ("powerbi-report-planning", f"{SOURCE_BASE}/powerbi-report-planning/SKILL.md"),
    ("powerbi-report-management", f"{SOURCE_BASE}/powerbi-report-management/SKILL.md"),
    ("semantic-model-authoring", f"{SOURCE_BASE}/semantic-model-authoring/SKILL.md"),
]


def _download(url: str, dest: Path, timeout: int = 30) -> int:
    """Descarga `url` a `dest`. Devuelve los bytes escritos."""
    req = urllib.request.Request(url, headers={"User-Agent": "powerbi-mcp-agent/setup_microsoft_skills"})
    data = urllib.request.urlopen(req, timeout=timeout).read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    print(f"\nDescargando {len(SKILLS)} skills oficiales de microsoft/skills-for-fabric...\n")
    failed = 0
    for slug, url in SKILLS:
        target = SKILLS_DIR / slug / "SKILL.md"
        try:
            size = _download(url, target)
            rel = target.relative_to(PROJECT_ROOT)
            print(f"  [+] {rel} ({size:,} bytes)")
        except Exception as exc:
            print(f"  [!] Error descargando {slug}: {exc}", file=sys.stderr)
            failed += 1

    print()
    if failed:
        print(f"[ERROR] {failed}/{len(SKILLS)} skills no se pudieron descargar.")
        return 1

    print(f"[OK] {len(SKILLS)} skills descargados a {SKILLS_DIR.relative_to(PROJECT_ROOT)}/")
    print()
    print("Proximo paso: ejecutar `uv run scripts/run.py sync` para propagarlos a")
    print("~/.config/opencode/skills/ (asi estan disponibles globalmente).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
