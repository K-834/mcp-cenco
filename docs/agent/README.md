# Documentos para el agente LLM

Esta carpeta contiene todo lo que el **agente LLM** (Claude, GPT, Ollama, etc.) consume cuando se conecta al server MCP.

**No son docs del proyecto** (esos viven en `docs/`, no en esta subcarpeta). Esta carpeta es lo que el LLM debe leer al arrancar la sesion para tener el contexto correcto.

## Que hay aca

| Doc | Que hace | Cuando lo lee el agente |
|---|---|---|
| [agent-guide.md](agent-guide.md) | Operacional: como invocar las 4 tools, que devuelve cada una, orden recomendado, manejo de errores. | Al inicio de la sesion, o cuando necesite recordar el flujo. |
| [SKILL_POWER_BI.md](SKILL_POWER_BI.md) | Skill canonico de Power BI: estructura PBIP/PBIR/TMDL, cuando convertir desde .pbix, catalogo de skills externos, checklist rapido. | Cuando trabaje con un modelo .pbip (recomendado: pedirlo una vez al inicio). |
| [SKILL_HTML_POWERBI.md](SKILL_HTML_POWERBI.md) | Skill de diseno HTML/CSS para el visual "HTML Content" (lite/full) de Daniel Marsh-Patrick: tags y CSS permitidos, sanitizacion, patron de ensamblado DAX, checklist de publicacion. | Cuando el usuario pida tarjetas, KPIs o layouts renderizados como HTML embebido dentro de una medida DAX. |

## Como se exponen al agente via MCP

| Resource URI | Contenido | Equivalente en disco |
|---|---|---|
| `usage://getting-started` | Markdown de `agent-guide.md` (operacional). | `docs/agent/agent-guide.md` |
| `power-bi://reference` | Markdown de `SKILL_POWER_BI.md` (skill de Power BI). | `docs/agent/SKILL_POWER_BI.md` |
| `html-content://reference` | Markdown de `SKILL_HTML_POWERBI.md` (skill de HTML/CSS embebido via visual "HTML Content"). | `docs/agent/SKILL_HTML_POWERBI.md` |

Ademas, `rules://best-practices` (que vive en `rules/rules.json`) expone las reglas compiladas para `validate_rules`.

## Como agregar un nuevo doc para el agente

1. Crear el archivo en `docs/agent/<nombre>.md`.
2. Si el doc debe ser expuesto como resource MCP, agregar:
   - Una entrada en `server/resources/agent_docs.py` (o el archivo correspondiente).
   - Un registro en `server/mcp_server.py`.
3. Si el doc tiene una contraparte opencode (skill), agregalo a `scripts/sync_skill.py` para que se distribuya a `.opencode/skills/` y `~/.config/opencode/skills/`.
4. Actualizar este README.md con la fila correspondiente.

## Convenciones

- Espanol consistente.
- Markdown estandar con frontmatter YAML solo si se distribuye como skill opencode (campo `description` para trigger).
- Codigo en fences con identificador de lenguaje.
- Sin emojis.
- Un archivo por tema. Si crece mucho (>500 lineas), partir.