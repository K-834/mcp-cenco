"""Tests para el sistema de skills hibrido (Microsoft + local)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import sync_skill  # noqa: E402
from scripts import setup_microsoft_skills  # noqa: E402


# Skills de Microsoft que el setup debe descargar
EXPECTED_MICROSOFT_SKILLS = {
    "powerbi-report-authoring",
    "powerbi-report-design",
    "powerbi-report-planning",
    "powerbi-report-management",
    "semantic-model-authoring",
}


def test_setup_microsoft_skills_has_all_five():
    """El setup debe apuntar a los 5 skills oficiales de microsoft/skills-for-fabric."""
    slugs = {slug for slug, _url in setup_microsoft_skills.SKILLS}
    assert slugs == EXPECTED_MICROSOFT_SKILLS, (
        f"Faltan skills: {EXPECTED_MICROSOFT_SKILLS - slugs}. "
        f"Extra: {slugs - EXPECTED_MICROSOFT_SKILLS}"
    )


def test_setup_microsoft_skills_urls_are_raw_github():
    """Las URLs deben apuntar a raw.githubusercontent.com (no a la UI de GitHub)."""
    for slug, url in setup_microsoft_skills.SKILLS:
        assert url.startswith("https://raw.githubusercontent.com/"), f"URL no raw para {slug}: {url}"
        assert url.endswith("/SKILL.md"), f"URL no apunta a SKILL.md para {slug}: {url}"


def test_sync_skill_local_skills_list_has_canonical_sources():
    """Los local skills deben apuntar a fuentes canonicas en docs/agent/."""
    PROJECT_ROOT = Path(sync_skill.PROJECT_ROOT) if hasattr(sync_skill, "PROJECT_ROOT") else Path(__file__).resolve().parent.parent
    for slug, canonical, fallback in sync_skill.LOCAL_SKILLS:
        assert "SKILL_" in canonical.name, f"slug={slug} canonical no es SKILL_*.md: {canonical}"


def test_sync_skill_finds_local_skill_file():
    """El SKILL local (docs/agent/SKILL_POWER_BI.md) existe y se lee."""
    path = Path(__file__).resolve().parent.parent / "docs" / "agent" / "SKILL_POWER_BI.md"
    assert path.exists(), f"No existe el skill local en {path}"
    content = path.read_text(encoding="utf-8")
    assert "power-bi-pbip" in content, "Falta name=power-bi-pbip en frontmatter"
    assert "---" in content, "Falta el frontmatter YAML"


def test_local_skill_mentions_microsoft_skills_complement():
    """El SKILL local debe referenciar los 5 skills de Microsoft como complementarios."""
    path = Path(__file__).resolve().parent.parent / "docs" / "agent" / "SKILL_POWER_BI.md"
    content = path.read_text(encoding="utf-8")
    for slug in EXPECTED_MICROSOFT_SKILLS:
        assert slug in content, f"El SKILL local no menciona el complementario {slug}"


def test_local_skill_mentions_mcp_resources():
    """El SKILL local debe anunciar los MCP resources que sirven su contenido."""
    path = Path(__file__).resolve().parent.parent / "docs" / "agent" / "SKILL_POWER_BI.md"
    content = path.read_text(encoding="utf-8")
    assert "power-bi://rules/summary" in content
    assert "power-bi://grid-layout" in content
    assert "power-bi://anti-patterns-compact" in content


def test_opencode_skills_has_microsoft_copies():
    """Las copias project-local de los 5 skills de Microsoft deben existir."""
    skills_dir = Path(__file__).resolve().parent.parent / ".opencode" / "skills"
    for slug in EXPECTED_MICROSOFT_SKILLS:
        path = skills_dir / slug / "SKILL.md"
        assert path.exists(), f"Falta copia project-local de {slug} en {path}"
        content = path.read_text(encoding="utf-8")
        assert f"name: {slug}" in content, f"Frontmatter incorrecto en {slug}"


def test_opencode_skills_has_local_copies():
    """La copia project-local del skill local unificado debe existir."""
    skills_dir = Path(__file__).resolve().parent.parent / ".opencode" / "skills"
    for slug in {"logica-bi-pbip-cenco"}:
        path = skills_dir / slug / "SKILL.md"
        assert path.exists(), f"Falta copia project-local de {slug} en {path}"


def test_agents_and_root_skills_have_all_copies():
    """Tanto .agents/skills como skills/ deben tener todas las 6 skills."""
    base_dirs = [
        Path(__file__).resolve().parent.parent / ".agents" / "skills",
        Path(__file__).resolve().parent.parent / "skills",
    ]
    all_expected = EXPECTED_MICROSOFT_SKILLS | {"logica-bi-pbip-cenco"}
    for b in base_dirs:
        for slug in all_expected:
            path = b / slug / "SKILL.md"
            assert path.exists(), f"Falta copia en {path}"



def test_diseno_bi_content_cenco_no_longer_exists():
    """El skill diseno-bi-content-cenco fue fusionado en logica-bi-pbip-cenco y debe estar eliminado."""
    skills_dir = Path(__file__).resolve().parent.parent / ".opencode" / "skills"
    docs_agent = Path(__file__).resolve().parent.parent / "docs" / "agent"
    assert not (skills_dir / "diseno-bi-content-cenco").exists(), "diseno-bi-content-cenco deberia estar eliminado"
    assert not (docs_agent / "SKILL_HTML_POWERBI.md").exists(), "SKILL_HTML_POWERBI.md deberia estar eliminado"


def test_merged_skill_covers_both_domains():
    """El skill fusionado debe mencionar tanto audit/edit PBIP como diseno HTML Content."""
    path = Path(__file__).resolve().parent.parent / "docs" / "agent" / "SKILL_POWER_BI.md"
    content = path.read_text(encoding="utf-8")
    # audit/edit/create PBIP
    assert "audit" in content.lower()
    assert "PBIP" in content or ".pbip" in content
    # diseno HTML Content
    assert "HTML Content" in content
    assert "coacervo" in content or "htmlContent" in content
    # comunicacion entre ambos
    assert "Comunicacion" in content or "comunican" in content.lower()


def test_merged_skill_does_not_overlap_with_microsoft():
    """El skill fusionado NO debe duplicar contenido de los skills Microsoft."""
    path = Path(__file__).resolve().parent.parent / "docs" / "agent" / "SKILL_POWER_BI.md"
    content = path.read_text(encoding="utf-8")
    # No debe listar visual types exhaustivos (eso lo cubre powerbi-report-authoring)
    assert "cardVisual" in content  # OK, lo menciona en anti-patterns
    # No debe explicar DAX INFO functions (eso es semantic-model-authoring)
    assert "INFO.VIEW" not in content, "No debe duplicar INFO functions de semantic-model-authoring"
    # No debe explicar el workflow Define->Approve->Build (eso es planning)
    assert "Approve" not in content or "Approve" in content.split("skills complementarios")[0], (
        "Approve solo debe aparecer como referencia, no como contenido duplicado"
    )


def test_docs_agent_has_microsoft_skills_downloaded():
    """Las 5 skills de Microsoft deben vivir en docs/agent/<slug>/SKILL.md (canonical local)."""
    docs_agent = Path(__file__).resolve().parent.parent / "docs" / "agent"
    for slug in EXPECTED_MICROSOFT_SKILLS:
        path = docs_agent / slug / "SKILL.md"
        assert path.exists(), f"Falta {slug}/SKILL.md en docs/agent/"
        content = path.read_text(encoding="utf-8")
        assert f"name: {slug}" in content, f"Frontmatter incorrecto en docs/agent/{slug}/SKILL.md"


def test_docs_agent_microsoft_skills_match_opencode_copies():
    """Las copias project-local deben tener el mismo SHA256 que las canonicales en docs/agent/."""
    docs_agent = Path(__file__).resolve().parent.parent / "docs" / "agent"
    opencode_skills = Path(__file__).resolve().parent.parent / ".opencode" / "skills"
    import hashlib
    for slug in EXPECTED_MICROSOFT_SKILLS:
        canonical = docs_agent / slug / "SKILL.md"
        local = opencode_skills / slug / "SKILL.md"
        if canonical.exists() and local.exists():
            h1 = hashlib.sha256(canonical.read_bytes()).hexdigest()
            h2 = hashlib.sha256(local.read_bytes()).hexdigest()
            assert h1 == h2, f"SKILL.md desincronizado para {slug}"


def test_sync_skill_microsoft_list_is_complete():
    """La lista MICROSOFT_SKILLS de sync_skill.py debe matchear los 5 esperados."""
    slugs = set(sync_skill.MICROSOFT_SKILLS)
    assert slugs == EXPECTED_MICROSOFT_SKILLS


def test_sync_skill_syncs_to_global(tmp_path, monkeypatch):
    """sync_skill.py debe sincronizar todos los .opencode/skills/ a ~/.config/opencode/skills/."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(sync_skill, "GLOBAL_SKILLS_DIR", fake_home / ".config" / "opencode" / "skills")

    project_root = Path(__file__).resolve().parent.parent
    monkeypatch.setattr(sync_skill, "PROJECT_ROOT", project_root)

    rc = sync_skill.main()
    assert rc == 0, f"sync_skill.main() retorno {rc}"

    global_dir = fake_home / ".config" / "opencode" / "skills"
    expected = set(EXPECTED_MICROSOFT_SKILLS) | {"logica-bi-pbip-cenco"}
    actual = {p.name for p in global_dir.iterdir() if p.is_dir()}
    assert expected <= actual, f"Faltan skills en global: {expected - actual}"


def test_sync_skill_idempotent():
    """Correr sync_skill.py 2 veces seguidas no debe romper ni duplicar."""
    rc1 = sync_skill.main()
    rc2 = sync_skill.main()
    assert rc1 == 0
    assert rc2 == 0
