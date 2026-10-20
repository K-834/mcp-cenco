# Arquitectura del proyecto

## Vision general

Servidor MCP (Model Context Protocol) que:

1. Lee modelos de Power BI en formato `.pbip` (solicita conversion manual si recibe `.pbix`).
2. Valida el modelo contra una guia de buenas practicas compilada una sola vez en `rules/rules.json`.
3. Pregunta al usuario cuando falta contexto para evaluar o disenar.
4. Genera una propuesta de diseno: layout de reporte + `theme.json` de Power BI.
5. Funciona igual desde distintos clientes y proveedores LLM sin reescribir el server.

## Principios de diseno

- **El server MCP es el nucleo reutilizable.** No depende de ningun cliente ni proveedor de LLM. Cada cliente solo necesita un archivo de configuracion que diga como lanzarlo.
- **Las reglas se compilan una sola vez.** El documento Word/PDF de buenas practicas se convierte a `rules.json` en `rules/compile_rules.py`. El server nunca vuelve a leer el documento original en tiempo de ejecucion.
- **Separar validacion automatica de validacion por criterio.** Reglas verificables por codigo (`check_type: automatico`) se resuelven sin LLM. Reglas que requieren juicio (`check_type: llm`) se devuelven al LLM cliente para que las evalue.
- **El cliente orquesta, el LLM decide, el server ejecuta.** El LLM nunca llama directamente al server MCP; el cliente es el intermediario.
- **Proveedor de LLM intercambiable.** Se abstrae detras de una interfaz comun (LiteLLM) para poder cambiar de modelo editando solo `config.yaml`.

## Estructura de archivos

```
powerbi-mcp-agent/
├── pyproject.toml                # manifest del paquete (deps, scripts, build, pytest)
├── uv.lock                       # lock reproducible de dependencias
├── README.md                     # entrada breve al proyecto, apunta a docs/
├── config.yaml                   # proveedor/modelo LLM activo (futuro)
├── .gitignore                    # exclusiones (.venv, caches, etc.)
│
├── docs/                         # TODA la documentacion (ver docs/README.md)
│   ├── README.md                 # indice
│   ├── proyecto/                 # documentacion humana del proyecto (plan, arquitectura, dev, deploy, clientes)
│   │   ├── plan.md               # plan original
│   │   ├── architecture.md       # este archivo
│   │   ├── dev-workflow.md
│   │   ├── deployment.md
│   │   ├── integracion-claude.md
│   │   ├── ollama-setup.md
│   │   └── skill-system.md
│   ├── reglas-mcp/                # entrada + doc de las reglas que compila y sirve el MCP
│   │   ├── rules-compilation.md
│   │   └── Checklist...pdf       # entrada del compilador de reglas
│   └── agent/                    # docs que consume el LLM via resources MCP
│       ├── README.md
│       ├── SKILL_POWER_BI.md     # skill canonico
│       └── agent-guide.md
│
├── scripts/                      # utilidades de linea de comando
│   ├── sync_skill.py             # sincroniza el skill a 3 ubicaciones
│   ├── install_claude.py         # instala/desinstala el server en Claude Desktop / Claude Code CLI
│   └── run.py                    # entry point unico con subcomandos (setup/compile/sync/test/llm/all/status/server-check/claude)
│
├── rules/                        # REGLAS COMPILADAS (cerebro del sistema)
│   ├── schema.json               # JSON Schema que valida reglas.json
│   ├── rules.json                # 31 reglas compiladas del PDF
│   └── compile_rules.py          # script que lee .docx/.pdf y genera rules.json
│
├── server/                       # NUCLEO: servidor MCP reutilizable
│   ├── mcp_server.py             # entry point, registra tools+resources
│   ├── tools/
│   │   ├── detect_format.py      # tool: detecta .pbip vs .pbix
│   │   ├── read_pbip.py          # tool: parsea TMDL/JSON del proyecto
│   │   ├── validate_rules.py     # tool: aplica reglas automaticas
│   │   └── generate_design.py    # tool: genera theme.json + layout
│   └── resources/
│       ├── best_practices.py     # resource: rules://best-practices
│       └── power_bi_reference.py # resource: power-bi://reference (skill)
│
├── clients/                      # CONFIGURACIONES POR CLIENTE MCP
│   ├── vscode.mcp.json
│   ├── claude_desktop.mcp.json
│   ├── claude_code.mcp.json
│   ├── antigravity.mcp_config.json
│   └── opencode.mcp.json
│
├── proyectos/                    # ENTRADA: modelos .pbip a analizar
│   └── test power bi/            # caso de prueba (proyecto real)
│       └── README.md             # describe este proyecto especifico
│
├── outputs/                      # SALIDA: informes y disenos generados
│
├── .vscode/mcp.json              # config que VS Code auto-detecta
│
├── .opencode/skills/             # skills project-local para opencode
│   ├── logica-bi-pbip-cenco/SKILL.md
│   └── diseno-bi-content-cenco/SKILL.md
│
└── tests/                        # SUITE PYTEST (40 tests)
    ├── conftest.py               # descubre .pbip por glob; fixtures
    ├── test_detect_format.py
    ├── test_read_pbip.py
    ├── test_validate_rules.py
    ├── test_generate_design.py
    ├── test_compile_rules.py
    ├── test_mcp_server.py
    └── test_integration.py
```

## Quien produce que, quien consume que

| Archivo | Lo produce | Lo consume |
|---|---|---|
| `docs/reglas-mcp/Checklist...pdf` | Tu (manual) | `compile_rules.py` |
| `docs/agent/SKILL_POWER_BI.md` | Tu (manual, pero versionado) | `sync_skill.py`, MCP resource `power-bi://reference` |
| `.opencode/skills/...` | `sync_skill.py` | opencode (auto-carga) |
| `~/.config/opencode/skills/...` | `sync_skill.py` | opencode (global) |
| `rules/rules.json` | `compile_rules.py` (con tu revision) | `mcp_server.py` al arrancar |
| `rules/schema.json` | El proyecto (en el repo) | `compile_rules.py`; tests |
| `proyectos/<carpeta>/*.pbip` | Power BI Desktop | `detect_format`, `read_pbip` |
| `server/mcp_server.py` | El proyecto | El cliente MCP |
| `server/tools/*.py` | El proyecto | El server, registrado como tools MCP |
| `outputs/` | (vacio, sera donde el server escriba reportes) | Tu |
| `clients/*.json` | El proyecto (ejemplos) | Tu (los copias a la config del cliente) |
| `tests/` | El proyecto | `uv run pytest` |
| `.vscode/mcp.json` | El proyecto (referencia) | VS Code en este workspace |
| `README.md` | El proyecto | Cualquiera que abra el repo |

## Flujo de informacion end-to-end

```
USUARIO (escribe en opencode / VS Code / Claude Desktop)
  │
  │ "Analiza el modelo de Wong y dime que no cumple las buenas practicas"
  │
  ▼
CLIENTE MCP
  │
  │ 1) Lee el resource rules://best-practices (una vez por sesion)
  │      <- {rules: [PBICHK-001..PBICHK-031]}
  │
  │ 2) Lee el resource power-bi://reference (skill sobre estructura PBIP)
  │      <- Markdown con estructura, convenciones, BPA
  │
  │ 3) El LLM decide que tools invocar y con que argumentos
  │
  ▼
SERVER MCP (server/mcp_server.py)
  │
  │ 4) detect_format("proyectos/test power bi/")
  │      <- {format: "pbip", ok: true, semantic_model: "...", report: "..."}
  │
  │ 5) read_pbip(ruta_sm, ruta_report)
  │      <- {tables: [15], measures: [4], relationships: [7], pages: [2]}
  │
  │ 6) validate_rules(model)
  │      <- {findings: [...], pending_llm_review: [BP-020, BP-021, ...]}
  │
  │ 7) El LLM evalua las reglas `llm` con criterio propio
  │
  │ 8) generate_design(model, report_goal)
  │      <- {theme: {...}, layout: [...], notes: [...]}
  │
  ▼
CLIENTE MCP recibe todo, formatea la respuesta para ti
  │
  ▼
USUARIO lee el resumen en lenguaje natural + archivos generados
```

## Que hace cada parte del server

### `server/mcp_server.py` (entry point)

```python
mcp = MCPServer("powerbi-mcp-agent")         # crea instancia
load_rules()                                  # carga rules.json en cache
detect_format.register(mcp, load_rules)       # registra cada tool
read_pbip.register(mcp)
validate_rules.register(mcp, load_rules)
generate_design.register(mcp)
best_practices.register(mcp, load_rules)      # registra el resource de reglas
power_bi_reference.register(mcp)              # registra el resource de skill
mcp.run(transport="stdio")                    # arranca el server
```

~30 lineas. Tres responsabilidades: crear instancia, cargar reglas, registrar tools/resources. Sin logica de negocio.

### Las 4 tools

| Tool | Entrada | Salida |
|---|---|---|
| `detect_format(path)` | ruta a archivo o carpeta | `{format, ok, semantic_model, report, message}` |
| `read_pbip(sm_path, report_path)` | rutas a `*.SemanticModel/` y `*.Report/` | `{tables, measures, relationships, pages}` |
| `validate_rules(model)` | salida de read_pbip | `{findings, pending_llm_review}` |
| `generate_design(model, report_goal)` | modelo + objetivo | `{theme, layout}` o `{missing_info: "report_goal"}` |

Ver detalle de cada una en `docs/reglas-mcp/rules-compilation.md` para la logica de validacion y diseno.

### Los 2 resources

| Resource URI | Devuelve |
|---|---|
| `rules://best-practices` | JSON con las 31 reglas del PDF (cacheado al arrancar). |
| `power-bi://reference` | Markdown del skill canonico de Power BI. |

## Cambiar el proyecto despues

Para renombrar el proyecto o moverlo de carpeta, hay que actualizar **una sola ruta** en `clients/*.json` y en `.vscode/mcp.json`. Ver `dev-workflow.md`.
