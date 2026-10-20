# Sistema de skills

Como se distribuye el skill local de Power BI y los 5 skills oficiales de
microsoft/skills-for-fabric en el proyecto, porque hay 3 ubicaciones, y como
mantenerlas sincronizadas.

## Vision general

| Capa | Cantidad | Prioridad | Quien la sirve |
|---|---|---|---|
| **Skills Microsoft (5)** | 5 skills | **PRIMARIO** — fuente de verdad para authoring exhaustivo | opencode (carga como skill nativa) |
| **Skill local** (1) | `power-bi-pbip` | **SECUNDARIO** — unico valor del proyecto (MCP tools + reglas) | opencode + Claude Desktop (via MCP resource) |
| **MCP resources** (3) | `rules/summary`, `grid-layout`, `anti-patterns-compact` | **FALLBACK** para clientes sin skill loading | Claude Desktop, VS Code, etc. via MCP |

### Que cubren los 5 skills de Microsoft (PRIMARIO)

Descargados desde `microsoft/skills-for-fabric` → `plugins/powerbi-authoring/skills/`:

| Skill | Cubre |
|---|---|
| `powerbi-report-authoring` | Mecanica PBIR (pages, visuals, filters, themes), CLI `powerbi-report-author`, Desktop reload + screenshot |
| `powerbi-report-design` | Tone, archetype (Executive / Operational / Analytical / Narrative / Comparative), layout, color, accessibility |
| `powerbi-report-planning` | Workflow Define→Inspect→Spec→Approve→Build→Publish (con aprobacion humana) |
| `powerbi-report-management` | Deploy a Fabric workspace via REST API (`az rest`), LRO polling |
| `semantic-model-authoring` | TMDL/DAX/Direct Lake/AI readiness, tiered tools (MCP > TMDL > az rest) |

Estos skills son **la fuente de verdad** para tareas de authoring. El skill local NO los duplica.

### Que cubre el skill local `power-bi-pbip` (SECUNDARIO)

Lo unico que el proyecto agrega sobre Microsoft:

- **Las 36 reglas compiladas** en `rules.json` (auditoria segun buenas practicas locales)
- **Los 8 tools del MCP server** (`read_pbip`, `validate_rules`, `write_*`, etc.)
- **El flujo audit-first**: leer → validar → corregir (vs authoring desde cero)
- **Las convenciones del proyecto**: grilla 1280x720, 7 categorias, 3 niveles de severidad
- **Anti-patterns locales** (10 mas criticos segun las reglas del proyecto)

### Que cubren los 3 MCP resources (FALLBACK)

Para clientes que NO cargan skills nativas (ej: Claude Desktop sin skill loading):

| URI | Sirve |
|---|---|
| `power-bi://reference` | El SKILL local completo (busca en 6 ubicaciones) |
| `power-bi://rules/summary` | Tabla compacta de las 36 reglas (id, categoria, severidad, titulo) |
| `power-bi://grid-layout` | Convencion de grilla 1280x720 del proyecto |
| `power-bi://anti-patterns-compact` | Top 10 anti-patterns del proyecto |

## Las ubicaciones de skills

| Copia | Path | Quien la lee |
|---|---|---|
| Canonica (fuente) | `docs/agent/SKILL_POWER_BI.md` | `sync_skill.py` la copia |
| Project-local (Agents) | `.agents/skills/<slug>/SKILL.md` | Antigravity, Cursor, Agent IDEs en este workspace |
| Project-local (OpenCode) | `.opencode/skills/<slug>/SKILL.md` | opencode cuando el workspace es este proyecto |
| Project-local (Visible) | `skills/<slug>/SKILL.md` | Acceso directo visible en raiz para usuarios y herramientas |
| Global | `~/.config/opencode/skills/<slug>/SKILL.md` | opencode en cualquier workspace |

Tanto los 5 skills oficiales de Microsoft como el skill local (`logica-bi-pbip-cenco`) estan presentes en todas las ubicaciones locales y se mantienen sincronizados automaticamente con `sync_skill.py`.


## Como se sincronizan

Script: `scripts/sync_skill.py`. Hace 2 fases:

**Fase 1 (local)**: lee `docs/agent/SKILL_*.md` y compara SHA256 con `.opencode/skills/<slug>/SKILL.md`. Copia si difieren.

**Fase 2 (global)**: sincroniza **todos** los subdirs de `.opencode/skills/` con `~/.config/opencode/skills/`. Incluye:
- Los 2 skills locales (`logica-bi-pbip-cenco`, `diseno-bi-content-cenco`)
- Los 5 skills de Microsoft (`powerbi-report-authoring`, `powerbi-report-design`, `powerbi-report-planning`, `powerbi-report-management`, `semantic-model-authoring`)

```bash
# Descargar los 5 skills de Microsoft (una sola vez, o cuando se actualicen):
uv run scripts/run.py setup-microsoft
# Equivalente a: uv run python scripts/setup_microsoft_skills.py

# Sincronizar todo a global:
uv run scripts/run.py sync
# Equivalente a: uv run python scripts/sync_skill.py
```

Output tipico:
```
=== Fase 1: copiar fuentes locales a .opencode/skills/ ===
[local] 'logica-bi-pbip-cenco' — fuente: docs\agent\SKILL_POWER_BI.md
         SHA256: e8c776a20d4efbf6...
  [=] Sin cambios: .opencode\skills\logica-bi-pbip-cenco\SKILL.md

=== Fase 2: sincronizar todos los .opencode/skills/ a global ===
[global] [=] Sin cambios: .config\opencode\skills\powerbi-report-authoring\SKILL.md
...

Resumen:
  Fase 1 (local):   0 actualizados, 2 sin cambios, 0 errores
  Fase 2 (global):  7 skills detectados, 0 actualizados, 7 sin cambios, 0 errores
```

Nota: los archivos se escriben con `newline="\n"` (LF) para que el SHA256 sea consistente entre Windows y Linux. Sin esto, Windows escribe CRLF y los hashes difieren.

## Cuando ejecutar el script

| Momento | Comando |
|---|---|
| Modificas `docs/agent/SKILL_*.md` | `uv run scripts/run.py sync` |
| Microsoft actualiza un skill en su repo | `uv run scripts/run.py setup-microsoft && uv run scripts/run.py sync` |
| Clonas el repo en otra PC | `uv run scripts/run.py setup-microsoft && uv run scripts/run.py sync` |
| Quieres verificar que todo esta en sync | `uv run scripts/run.py sync` (output dice "Sin cambios") |
| Como parte de CI/CD | Despues de `git pull` o antes de un commit |

## Orden de busqueda del MCP resource

`server/resources/power_bi_reference.py` busca el skill local en este orden (el primero que exista gana):

1. `docs/agent/SKILL_POWER_BI.md` (canonica, project-relative)
2. `docs/SKILL_POWER_BI.md` (legacy, para proyectos viejos)
3. `.opencode/skills/logica-bi-pbip-cenco/SKILL.md` (project-local)
4. `.agents/skills/logica-bi-pbip-cenco/SKILL.md` (alternativa project-local)
5. `skills/logica-bi-pbip-cenco/SKILL.md` (otra alternativa)
6. `~/.config/opencode/skills/logica-bi-pbip-cenco/SKILL.md` (global)

Esto asegura que:
- Un clon fresco funciona inmediatamente (encuentra la copia project-local o la canonica).
- Si ninguna existe, devuelve un mensaje claro pidiendo correr `sync`.

## Como se descubren los skills desde opencode

opencode busca skills en:

1. `~/.config/opencode/skills/<name>/SKILL.md` (global).
2. `<workspace>/.opencode/skills/<name>/SKILL.md` (project-local).

Cuando encuentra un archivo, parsea el frontmatter YAML:
- `name`: identificador del skill.
- `description`: trigger para activarlo (keywords que matchean con tu mensaje).

## Frontmatter del skill local

```yaml
---
name: power-bi-pbip
description: Auditar, editar, crear y modificar proyectos Power BI en formato PBIP/PBIR/TMDL segun las 36 reglas compiladas en este proyecto. Activar cuando el usuario pida auditar, validar, corregir, crear o modificar un modelo o reporte Power BI (.pbip, .tmdl, .pbir). Para tareas avanzadas de authoring (planning exhaustivo, design system, deploy a Fabric, etc.), consultar los skills complementarios powerbi-report-planning, powerbi-report-design, powerbi-report-authoring, powerbi-report-management, semantic-model-authoring.
---
```

La `description` declara explicitamente que el skill es **complementario** a los 5 de Microsoft, y los nombra para que opencode los cargue en cadena.

## Como agregar un nuevo skill

1. **Si es del proyecto**: crea `docs/agent/SKILL_<nombre>.md` con frontmatter. Agregalo a `LOCAL_SKILLS` en `scripts/sync_skill.py` con su slug.
2. **Si es de Microsoft**: agregalo a `SKILLS` en `scripts/setup_microsoft_skills.py`. Corrre `setup-microsoft`.

## Versionar skills

- **Skill local**: `docs/agent/SKILL_POWER_BI.md` esta commiteado. Cada modificacion requiere commit + sync.
- **Skills Microsoft**: NO se commitean (vienen de URL externa). Se descargan via `setup-microsoft`. Si Microsoft actualiza, re-corre el setup.

Para Git, lo mas limpio: commitea solo `docs/agent/SKILL_POWER_BI.md` y `.opencode/skills/` (que es la copia project-local). El sync regenera la copia global.

Alternativa: agregar `.opencode/` a `.gitignore`. Esta opcion require actualizar la politica de versionado.

## Diagnosticar problemas

| Sintoma | Causa probable | Fix |
|---|---|---|
| opencode no carga el skill local | El frontmatter `description` no matchea las keywords | Reformula mencionando "Power BI", ".pbip" |
| opencode no carga skills Microsoft | No se ejecuto `setup-microsoft` | `uv run scripts/run.py setup-microsoft` |
| `power-bi://reference` no encuentra el skill | Ninguna de las 6 ubicaciones tiene el archivo | `uv run scripts/run.py sync` |
| Cambios en `docs/agent/SKILL_POWER_BI.md` no se reflejan | Olvidaste correr sync | `uv run scripts/run.py sync` |
| Skill aparece duplicado | Tienes el archivo en multiples ubicaciones y se cargan todos | Normal: opencode deduplica por nombre |
| SHA256 difiere entre copias despues de sync | Bug en `sync_skill.py` (line endings, encoding) | Verificar que el script use `newline="\n"` |

## Regla de interaccion (skill local vs Microsoft)

Cuando el usuario pida algo:

1. **Si lo cubre el skill local** (`power-bi-pbip`): auditar, validar, corregir, crear/modificar segun las 36 reglas del proyecto. Usar las tools MCP y las convenciones locales.
2. **Si NO lo cubre**: invocar el skill Microsoft correspondiente desde opencode:
   - planning → `powerbi-report-planning`
   - design system → `powerbi-report-design`
   - mecanica PBIR exhaustiva → `powerbi-report-authoring`
   - deploy a Fabric → `powerbi-report-management`
   - TMDL/DAX/Direct Lake avanzado → `semantic-model-authoring`
3. **Si el cliente no carga skills nativas**: usar el MCP resource correspondiente (`power-bi://rules/summary`, etc.) via el server `powerbi-mcp`.

Esta separacion evita duplicacion y mantiene cada skill enfocado en lo que hace bien.
