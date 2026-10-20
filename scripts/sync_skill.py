"""Sincroniza los skills del agente entre sus ubicaciones.

Arquitectura de skills (PRIORIDAD):
  1. PRIMARIO: skills oficiales de microsoft/skills-for-fabric (5 skills).
     Descargados por `scripts/setup_microsoft_skills.py` a
     `.opencode/skills/<slug>/SKILL.md`. Son la fuente de verdad para
     authoring exhaustivo de Power BI / Fabric.

  2. SECUNDARIO: skill local del proyecto (`docs/agent/SKILL_*.md`).
     Cubre lo unico de este proyecto: las 36 reglas de auditoria,
     los tools del MCP server, y el flujo audit-first.
     El slug de destino se mantiene estable para no romper integraciones.

  3. FALLBACK: recursos MCP (`power-bi://rules/summary`,
     `power-bi://grid-layout`, etc.) para clientes que no cargan skills nativas.

Este script sincroniza en dos fases:

  Fase 1 (local): copia cada `docs/agent/SKILL_*.md` a su destino
                  `.opencode/skills/<slug>/SKILL.md`.

  Fase 2 (global): sincroniza TODO `.opencode/skills/<slug>/SKILL.md` con
                   `~/.config/opencode/skills/<slug>/SKILL.md` (incluye
                   los 5 skills de Microsoft y los locales).

Ejecutar cada vez que se actualice un SKILL.md:

    uv run python scripts/sync_skill.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / ".opencode" / "skills"
AGENTS_SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"
ROOT_SKILLS_DIR = PROJECT_ROOT / "skills"
GLOBAL_SKILLS_DIR = Path.home() / ".config" / "opencode" / "skills"

# (slug de destino, fuente canonica, fuente legacy opcional)
# Skills del proyecto con fuente canonica en docs/agent/.
#
# Hay UN SOLO skill local (SKILL_POWER_BI.md) que cubre tanto audit/edit/create
# PBIP como diseno HTML Content. Antes habia dos skills separados pero se
# fusionaron en uno solo para evitar overlap y asegurar que las dos areas
# se comuniquen (ver seccion 5.7 del skill).
LOCAL_SKILLS: list[tuple[str, Path, Path | None]] = [
    (
        "logica-bi-pbip-cenco",
        PROJECT_ROOT / "docs" / "agent" / "SKILL_POWER_BI.md",
        PROJECT_ROOT / "docs" / "SKILL_POWER_BI.md",
    ),
]


# Skills de Microsoft descargados por setup_microsoft_skills.py a docs/agent/<slug>/SKILL.md.
# Tambien se sincronizan a .opencode/skills/<slug>/SKILL.md (project-local) y
# ~/.config/opencode/skills/<slug>/SKILL.md (global).
MICROSOFT_SKILLS = ["powerbi-report-authoring", "powerbi-report-design", "powerbi-report-planning", "powerbi-report-management", "semantic-model-authoring"]


def _resolve_source(canonical: Path, fallback: Path | None) -> Path | None:
    if canonical.exists():
        return canonical
    if fallback is not None and fallback.exists():
        return fallback
    return None


def _copy_to_destinations(source: Path, slug: str, source_hash: str) -> bool:
    """Copia la fuente a SKILLS_DIR (.opencode), AGENTS_SKILLS_DIR (.agents) y ROOT_SKILLS_DIR (skills)."""
    any_copied = False
    for base_dir in (SKILLS_DIR, AGENTS_SKILLS_DIR, ROOT_SKILLS_DIR):
        target = base_dir / slug / "SKILL.md"
        if not target.exists() or _sha256(target) != source_hash:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            print(f"  [+] Copiado:   {_print_path(target)}")
            any_copied = True
        else:
            print(f"  [=] Sin cambios: {_print_path(target)}")
    return any_copied


def _sync_microsoft_skill(slug: str) -> tuple[int, int, int]:
    """Copia docs/agent/<slug>/SKILL.md -> .opencode/skills, .agents/skills y skills/.

    Los skills de Microsoft viven en docs/agent/<slug>/SKILL.md (canonical local,
    descargados via setup_microsoft_skills.py). Esta fase los propaga a los directorios
    de skills para que cualquier cliente o agente pueda cargarlos.
    """
    canonical = PROJECT_ROOT / "docs" / "agent" / slug / "SKILL.md"

    if not canonical.exists():
        return 0, 0, 1

    source_hash = _sha256(canonical)
    print(f"[local] '{slug}' — fuente: {_print_path(canonical)}")
    print(f"         SHA256: {source_hash[:16]}...")

    copied = _copy_to_destinations(canonical, slug, source_hash)
    return (1, 0, 0) if copied else (0, 1, 0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _print_path(target: Path) -> str:
    try:
        return str(target.relative_to(PROJECT_ROOT))
    except ValueError:
        pass
    try:
        return str(target.relative_to(Path.home()))
    except ValueError:
        return str(target)


def _sync_project_local(slug: str, canonical: Path, fallback: Path | None) -> tuple[int, int, int]:
    """Fase 1: copia la fuente canonica a .opencode/skills, .agents/skills y skills/."""
    source = _resolve_source(canonical, fallback)
    if source is None:
        print(f"[ERROR] Fuente no existe para '{slug}': {canonical}", file=sys.stderr)
        if fallback is not None:
            print("Tambien busque el fallback en:", fallback, file=sys.stderr)
        return 0, 0, 1

    source_hash = _sha256(source)

    print(f"[local] '{slug}' — fuente: {_print_path(source)}")
    print(f"         SHA256: {source_hash[:16]}...")

    copied = _copy_to_destinations(source, slug, source_hash)
    return (1, 0, 0) if copied else (0, 1, 0)


def _sync_global_one(slug: str) -> tuple[int, int, int]:
    """Fase 2: sincroniza `.opencode/skills/<slug>/SKILL.md` -> `~/.config/opencode/skills/<slug>/SKILL.md`."""
    source = SKILLS_DIR / slug / "SKILL.md"
    target = GLOBAL_SKILLS_DIR / slug / "SKILL.md"

    if not source.exists():
        return 0, 0, 0

    source_hash = _sha256(source)
    if target.exists() and _sha256(target) == source_hash:
        return 0, 1, 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return 1, 0, 0


def _sync_all_global() -> tuple[int, int, int, int]:
    """Fase 2: sincroniza TODOS los skills del directorio .opencode/skills/ a global."""
    total_ok = total_skipped = total_failed = 0
    synced = 0
    if not SKILLS_DIR.exists():
        return 0, 0, 0, 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        slug = skill_dir.name
        synced += 1
        try:
            ok, skipped, failed = _sync_global_one(slug)
            target = GLOBAL_SKILLS_DIR / slug / "SKILL.md"
            if ok:
                print(f"[global] [+] Copiado:   {_print_path(target)}")
            elif skipped:
                print(f"[global] [=] Sin cambios: {_print_path(target)}")
            elif failed:
                print(f"[global] [!] Error en:   {_print_path(skill_md)}", file=sys.stderr)
            total_ok += ok
            total_skipped += skipped
            total_failed += failed
        except OSError as exc:
            print(f"[global] [!] Error en {slug}: {exc}", file=sys.stderr)
            total_failed += 1
    return total_ok, total_skipped, total_failed, synced


def main() -> int:
    print("\n=== Fase 1: copiar fuentes locales a .opencode/skills/ ===\n")
    local_ok = local_skipped = local_failed = 0

    for slug, canonical, fallback in LOCAL_SKILLS:
        ok, skipped, failed = _sync_project_local(slug, canonical, fallback)
        local_ok += ok
        local_skipped += skipped
        local_failed += failed
        print()

    print("--- Skills de Microsoft (descargados a docs/agent/) ---\n")
    for slug in MICROSOFT_SKILLS:
        ok, skipped, failed = _sync_microsoft_skill(slug)
        local_ok += ok
        local_skipped += skipped
        local_failed += failed
        print()

    print("=== Fase 2: sincronizar todos los .opencode/skills/ a global ===\n")
    global_ok, global_skipped, global_failed, synced = _sync_all_global()
    print()

    print(f"Resumen:")
    print(f"  Fase 1 (local):   {local_ok + local_skipped + local_failed} operaciones, {local_ok} actualizados, {local_skipped} sin cambios, {local_failed} errores")
    print(f"  Fase 2 (global):  {synced} skills detectados, {global_ok} actualizados, {global_skipped} sin cambios, {global_failed} errores")

    return 1 if (local_failed or global_failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
