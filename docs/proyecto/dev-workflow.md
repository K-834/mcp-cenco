# Flujo de desarrollo

Comandos, ciclo de trabajo, y procedimientos de mantenimiento.

## Setup inicial

Desde la raiz del proyecto:

```bash
uv sync --group dev
```

Crea `.venv/` y resuelve dependencias + dev-dependencies (pytest). Si ya existe `.venv/`, solo sincroniza lo que falte.

## Script unico: `scripts/run.py`

En lugar de memorizar multiples comandos, usa `scripts/run.py` que expone subcomandos para cada operacion habitual:

| Subcomando | Que hace |
|---|---|
| `setup` | `uv sync --group dev` |
| `compile` | Regenera `rules.json` desde el PDF/DOCX via LLM (no hay modo regex). |
| `sync` | Sincroniza el skill a `.opencode/skills/` y `~/.config/opencode/skills/`. |
| `test` | Corre la suite de pytest. |
| `server-check` | Arranca el server MCP 3 segundos y valida el handshake. |
| `status` | Muestra que archivos estan actualizados y cuales difieren. |
| `all` | `setup + compile + sync + test` (lo mas comun). Si no hay ningun LLM disponible (Ollama apagado y sin API key), falla con un mensaje claro en vez de compilar con menos calidad. |

Ejemplos:

```bash
uv run scripts/run.py all                              # flujo completo de setup + validacion
uv run scripts/run.py status                           # "que tengo actualizado?"
uv run scripts/run.py compile --llm-model ollama/qwen2.5-coder:14b
uv run scripts/run.py server-check                     # verifica que el server MCP arranca OK
```

### Variables de entorno para el LLM (usadas por `compile`/`all`)

| Variable | Default | Que hace |
|---|---|---|
| `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | - | Si esta seteada, se usa ese provider cloud. |
| `MINIMAX_API_KEY` | - | API key de MiniMax (https://api.minimax.io). Modelos: `MiniMax-M2.1`, `MiniMax-M2.5`, `MiniMax-M3`. |
| `MINIMAX_API_BASE` | `https://api.minimax.io/v1` | Endpoint de MiniMax. Para China: `https://api.minimaxi.com/v1` o `MINIMAX_USE_CHINA=1`. |
| `POWERBI_MCP_LLM_MODEL` | `ollama/gemma3:4b` | Modelo a invocar via litellm/Ollama. Ejemplos: `minimax/MiniMax-M3`, `gemini/gemini-2.5-flash`. |
| `OLLAMA_API_BASE` | `http://localhost:11434` | URL del daemon Ollama. Cambiar si corre en otra maquina/puerto. |
| `POWERBI_MCP_LLM_TIMEOUT` | 180 | Timeout por trozo del documento (segundos, no por documento completo). |
| `POWERBI_MCP_LLM_MAX_TOKENS` | 3000 | Tokens maximos de respuesta por trozo. |
| `POWERBI_MCP_LLM_NUM_CTX` | 4096 | Contexto de Ollama por trozo. |

**Proveedores soportados** (en orden de prioridad en `is_available()`):

1. Gemini / Google (`gemini/...`) — `GOOGLE_API_KEY` o `GEMINI_API_KEY`
2. OpenAI (`gpt-...`) — `OPENAI_API_KEY`
3. Anthropic (`claude-...`) — `ANTHROPIC_API_KEY`
4. **MiniMax** (`minimax/MiniMax-M3`, etc.) — `MINIMAX_API_KEY`
5. Cualquier OpenAI-compatible custom — `MODEL_API_KEY` + `MODEL_API_BASE`
6. Ollama local (`ollama/...`) — `OLLAMA_API_BASE` o `http://localhost:11434` accesible

El documento se divide en trozos de ~2500 caracteres (no hay parser regex de reglas; ver [rules-compilation.md](../reglas-mcp/rules-compilation.md#extraccion-de-reglas-100-llm-sin-parser-regex)) y se hace una llamada LLM por trozo, con hasta 3 reintentos cada uno.

### Si `compile` es muy lento en CPU

Con modelos locales chicos (`gemma3:4b`) cada trozo puede tardar 1-3 minutos en CPU sin GPU. Para 4-6 trozos, esperar 5-15 minutos es normal. Opciones si es demasiado lento:

1. **Usar un modelo mas chico**: ya es el default (`gemma3:4b`).
2. **Reducir el tamano de trozo** para respuestas mas cortas (mas llamadas, cada una mas rapida): pasar `chunk_chars` mas bajo si llamas `extract_rules()` directamente, o ajustar `DEFAULT_CHUNK_CHARS` en `rules/llm_extractor.py`.
3. **Subir el timeout** si el modelo esta progresando pero no llega a tiempo: `$env:POWERBI_MCP_LLM_TIMEOUT=300`.
4. **Usar un provider cloud** (mas rapido, tiene costo): `$env:ANTHROPIC_API_KEY=...` y `--llm-model claude-haiku-4-5`.
5. **Usar GPU**: si tenes GPU NVIDIA, Ollama la usa automaticamente y es 5-10x mas rapido.

`status` muestra que archivos existen y alerta si algo no esta sincronizado (ej. `rules.json` mas viejo que `pyproject.toml`, o `docs/SKILL_POWER_BI.md` con SHA distinto al de `.opencode/skills/.../SKILL.md`).

## Comandos uv utiles (uso directo)

| Comando | Que hace |
|---|---|
| `uv sync` | Instala dependencias desde `uv.lock`, recrea `.venv`. |
| `uv sync --group dev` | Ademas agrega dev-dependencies (pytest). |
| `uv add <paquete>` | Agrega dependencia y actualiza `pyproject.toml` + `uv.lock`. |
| `uv remove <paquete>` | Quita dependencia. |
| `uv lock` | Regenera `uv.lock` desde `pyproject.toml` sin tocar `.venv`. |
| `uv run <cmd>` | Ejecuta un comando dentro del entorno virtual del proyecto. |
| `uv run python rules/compile_rules.py` | Regenera `rules.json` desde el PDF/DOCX de `docs/reglas-mcp/`. |
| `uv run pytest` | Corre la suite (50 tests). |
| `uv run powerbi-mcp` | Atajo al entry point (`server/mcp_server.py:main`). |
| `uv run python scripts/sync_skill.py` | Sincroniza el skill a `.opencode/skills/` y `~/.config/opencode/skills/`. |
| `uv run scripts/run.py --help` | Lista los subcomandos disponibles. |

## Ciclo de trabajo habitual

### Cuando agregas una dependencia

```bash
uv add <paquete>
git add pyproject.toml uv.lock
```

Verifica que los tests siguen pasando:
```bash
uv run pytest
```

### Cuando actualizas el documento de buenas practicas

1. Reemplaza `docs/reglas-mcp/<documento>.pdf` (o `.docx`).
2. Regenera las reglas:
   ```bash
   uv run python rules/compile_rules.py
   ```
3. Revisa manualmente `rules/rules.json`. La compilacion es semiautomatica: podes editar IDs, descripciones, `severity`, etc. antes de commitear.
4. Reinicia el server MCP (los clientes MCP lo recargan al reconectar).
5. Corre los tests:
   ```bash
   uv run pytest
   ```

### Cuando agregas una regla manual

Edita `rules/rules.json` directamente. El schema esta en `rules/schema.json`. Despues corre `uv run pytest` para validar contra el schema (test `test_rules_json_validates_against_schema`).

### Cuando agregas una nueva tool o resource

1. Crea el archivo en `server/tools/<nombre>.py` o `server/resources/<nombre>.py`.
2. Sigue el patron de los existentes: `def register(mcp, ...)` con un decorador adentro.
3. Registra en `server/mcp_server.py` llamando `register(mcp)` o `register(mcp, load_rules)`.
4. Agrega tests en `tests/test_<tool>.py`.
5. Si el resource URI es nuevo, agregalo a `EXPECTED_RESOURCES` en `tests/test_mcp_server.py`.

### Cuando agregas un cliente MCP nuevo

Copia uno de los templates en `clients/*.json` y ajusta:
- `command` y `args` para apuntar a `uv run --project <ruta> python server/mcp_server.py`.
- El formato del JSON segun el esquema del cliente.

## Suite de tests

40 tests organizados en 7 archivos. Corren con:

```bash
uv run pytest
```

### Estructura

| Archivo | Cubre |
|---|---|
| `test_detect_format.py` | Deteccion de .pbip, .pbix, missing, unknown extension |
| `test_read_pbip.py` | Parser TMDL: tablas, medidas con formatString, relaciones, paginas |
| `test_validate_rules.py` | Logica de validacion por categoria |
| `test_generate_design.py` | Generacion de theme.json + layout segun `report_goal` |
| `test_compile_rules.py` | Compilador de reglas: heuristicas, format detection, schema validation |
| `test_mcp_server.py` | Handshake MCP, registro de tools/resources, resource `power-bi://reference` |
| `test_integration.py` | Pipeline end-to-end contra `proyectos/test power bi/` |

### Fixture clave: `tools`

`tests/conftest.py` expone un fixture `tools` (session-scoped) que devuelve las tools ya registradas en el MCP server como un dict `{nombre: funcion}`. Asi los tests pueden llamar las tools reales contra el modelo real sin mockear.

### Discovery del `.pbip`

`conftest.py` busca automaticamente cualquier `*.pbip` dentro de `proyectos/test power bi/`. Si renombras o reemplazas el modelo, los tests siguen funcionando. Si lo borras, fallaran con un mensaje claro pidiendo colocar un proyecto.

## Skill de Power BI

El skill (`docs/SKILL_POWER_BI.md`) se distribuye en 3 copias sincronizadas:

| Copia | Proposito |
|---|---|
| `docs/SKILL_POWER_BI.md` | Canonica, versionada con el codigo |
| `.opencode/skills/power-bi-pbip/SKILL.md` | Project-local, viaja con el repo |
| `~/.config/opencode/skills/power-bi-pbip/SKILL.md` | Global del usuario |

Sincronizacion:
```bash
uv run python scripts/sync_skill.py
```

El script solo copia si el SHA256 del archivo cambio (idempotente y barato). Ver `skill-system.md` para el detalle completo.

## Renombrar o mover el proyecto

Si cambias la ruta del proyecto en disco:

1. Actualiza las rutas en `clients/*.json` (los 5 archivos).
2. Actualiza `.vscode/mcp.json`.
3. Re-sincroniza el skill si aplica (las rutas internas usan `Path(__file__).resolve()`, asi que sobreviven a movimientos dentro del repo, pero la copia global en `~/.config/` queda fija).
4. Re-corre `uv sync` por si uv guardo paths absolutos.

## Errores comunes

| Error | Causa | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | `uv` no esta activando el venv | Usa `uv run` o activa el venv manualmente |
| Server arranca pero no responde | Estas lanzando `python` sin `uv` | Cambia el comando a `uv run --project . python server/mcp_server.py` |
| Tests fallan despues de editar `rules.json` | El JSON no valida contra `schema.json` | Corre `uv run python rules/compile_rules.py` para regenerar, o corrige manualmente el JSON |
| `ModuleNotFoundError: jsonschema` | Falta la dep en runtime | `uv add jsonschema` |

## CI / Git (pendiente)

El proyecto no tiene `.github/workflows/` todavia. Cuando lo agregues:

1. Trigger en PR.
2. Job: `uv sync --group dev` y `uv run pytest`.
3. Opcional: `uv run python rules/compile_rules.py --check` (pendiente: script que solo valide, sin escribir).
