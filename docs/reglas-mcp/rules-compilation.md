# Compilacion de reglas

Como se transforma un documento de buenas practicas (PDF o DOCX) en `rules/rules.json`, estructura del JSON, y como el server lo consume.

## Pipeline

```
docs/reglas-mcp/<documento>.pdf (o .docx)
        │
        │ extract_text() (markitdown)
        ▼
texto completo del documento
        │
        │ extract_rules() (rules/llm_extractor.py) — requiere LLM, sin fallback regex
        ▼
lista de reglas (dict) + assign_ids()
        │
        │ uv run python rules/compile_rules.py
        ▼
rules/rules.json  ◄── validado contra rules/schema.json
        │
        │ arrancas el server MCP
        ▼
server/mcp_server.py:load_rules()  ◄── lee UNA vez al iniciar, cachea en memoria
        │
        │ el cliente MCP pide el resource
        ▼
rules://best-practices  ◄── serializa a JSON para el LLM
        │
        │ LLM lee, decide que tool invocar
        ▼
validate_rules(model)  ◄── itera rules.json, dispatcha por check_type + category
        │
        ▼
findings + pending_llm_review
```

## Comandos

```bash
# Auto-descubre el documento en docs/reglas-mcp/ (si hay uno solo)
uv run python rules/compile_rules.py

# Especificar el documento
uv run python rules/compile_rules.py --input docs/reglas-mcp/mi-guia.pdf

# Elegir modelo (default: Ollama local, ver docs/proyecto/ollama-setup.md)
uv run python rules/compile_rules.py --llm-model ollama/qwen2.5-coder:14b

# Cambiar la salida
uv run python rules/compile_rules.py --output rules/rules.json
```

Si hay varios documentos en `docs/reglas-mcp/`, el script los lista y pide uno explicito.

Requiere un LLM disponible (Ollama local corriendo, o una API key cloud). Sin eso,
el compilado falla con un mensaje claro — no hay modo regex de respaldo.

## Extraccion de texto (`extract_text()`)

`compile_rules.py` usa [`markitdown`](https://github.com/microsoft/markitdown) para convertir el PDF/DOCX a texto (en vez de `pypdf`/`python-docx` directo). markitdown reconstruye el layout con mas fidelidad: no rompe acentos, no descarta filas de tablas complejas. Como markitdown emite las tablas en sintaxis markdown (`| celda | celda |`), `_flatten_markdown_tables()` las aplana a texto separado por espacios — esto es limpieza cosmetica, no decide donde empieza o termina una regla.

## Extraccion de reglas: 100% LLM, sin parser regex

Versiones anteriores usaban un parser regex para decidir donde empieza y termina cada regla dentro del texto extraido (buscando marcadores como `Obligatorio X` / `Opcional X`, keywords de "Ambito"/"Objetivo", verbos de accion para separar titulo de descripcion, etc.). Ese enfoque resulto **fragil en la practica**:

- Palabras clave que tambien aparecian en el parrafo introductorio del documento (ej. "performance") hacian que el limite de la primera regla de una seccion se calculara mal, y esa regla terminaba con contenido mezclado o se perdia.
- Los titulos quedaban cortados a mitad de palabra porque la heuristica de "buscar el primer verbo de accion" no siempre coincidia con el limite real.
- Cualquier variacion en el layout del documento (una celda de tabla partida en varias lineas, un termino nuevo) podia romper silenciosamente la deteccion.

Por eso `compile_rules.py` ya no tiene ese parser. Ahora **un LLM lee el texto y decide todo**: cuantas reglas hay, donde empieza y termina cada una, titulo, descripcion, categoria, severidad, etc. El LLM tiene el contexto completo del documento (no un regex ciego a keywords), asi que no comete el mismo tipo de error.

### Como se llama al LLM (`rules/llm_extractor.py::extract_rules`)

Mandar el documento completo (~10K+ caracteres) en una sola llamada se probo primero y **fallo por timeout en CPU local** (>15 min sin respuesta, con Ollama `qwen2.5-coder:14b`). La solucion: el texto se divide en trozos de ~2500 caracteres (`_split_into_chunks`, corte solo por lineas — **no** busca keywords ni limites de regla, solo acota tamano) y se hace una llamada al LLM por trozo, con el mismo prompt de "documento completo". El LLM decide cuantas reglas hay dentro de cada trozo.

- Si una regla queda partida justo en el borde de un trozo, puede salir una version parcial de ese lado. Es un costo aceptable frente a perder reglas enteras por una heuristica de limites fragil, y en la practica el corte por tamano cae casi siempre entre filas de tabla (los trozos son mas grandes que una fila individual).
- Cada trozo se reintenta hasta `max_retries` veces (default 3) si el LLM falla o devuelve JSON invalido.
- Si un trozo agota los reintentos, `extract_rules()` lanza `RuntimeError` y el compile completo falla — no hay fallback silencioso que reduzca la calidad sin avisar.

### Formato de respuesta esperado del LLM

El prompt (`rules/prompts.py::build_document_messages`) le pide al LLM devolver:

```json
{"rules": [
  {
    "source_id": "BP-003",
    "title": "...",
    "description": "...",
    "category": "modelo_datos",
    "severity": "alta",
    "check_type": "automatico",
    "detection": "...",
    "rationale": "...",
    "scope": ["tables"],
    "keywords": ["..."],
    "example_violation": "...",
    "source_chunk": "..."
  }
]}
```

`source_id` es el ID que el documento original le puso a la regla (formato narrativo `BP-XXX`), o `null` si el documento no numera reglas explicitamente (formato tabular). `rules/llm_extractor.py::_coerce_rule` valida/normaliza cada objeto (categoria/severidad/check_type invalidos caen a un default seguro; entradas con titulo o descripcion demasiado cortos se descartan). `rules/compile_rules.py::assign_ids` decide el `id` final: usa `source_id` si es valido (`^BP-\d{2,}$`), si no asigna `PBICHK-XXX` secuencial.

## Estructura de `rules/rules.json`

```json
{
  "version": "1.0",
  "generated_from": "C:\\...\\docs\\reglas-mcp\\Checklist...pdf",
  "rules_count": 31,
  "rules": [
    {
      "id": "PBICHK-001",
      "category": "nomenclatura",
      "title": "Uso de tipos de datos correcto",
      "description": "Evitar el uso de tipo texto en campos numéricos o de fecha",
      "severity": "alta",
      "check_type": "automatico",
      "detection": "Revisar tipo de dato de columnas en TMDL.",
      "rationale": "Evita errores de conversion y mejora performance."
    }
  ]
}
```

### Campos

| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `id` | string | Si | Identificador unico. Patron: `^(BP\|PBICHK)-[0-9]{3,}$`. |
| `category` | enum | Si | `modelo_datos`, `medidas_dax`, `reporte_visual`, `rendimiento`, `nomenclatura`, `seguridad`, `documentacion`. |
| `title` | string (5+ chars) | Si | Nombre corto. |
| `description` | string (10+ chars) | Si | Detalle de la regla. |
| `severity` | enum | Si | `alta`, `media`, `baja`. |
| `check_type` | enum | Si | `automatico` (codigo) o `llm` (criterio). |
| `detection` | string | No | Pista de como detectarla contra un modelo real. Texto libre, lo redacta el LLM. |
| `rationale` | string | No | Por que existe la regla. Texto libre, lo redacta el LLM. |
| `scope` | array enum | No | A que artefacto aplica (`tables`, `columns`, `measures`, `relationships`, `pages`, `visuals`, `dataset`). |
| `keywords` | array string | No | Terminos que un auditor buscaria en TMDL/DAX. |
| `example_violation` | string | No | Ejemplo concreto de violacion. |
| `source_chunk` | string | No | Cita textual del documento original en la que se basa la regla (auditoria). |
| `compiled_by` | string | No | Siempre `"llm"`. |

Ver `rules/schema.json` para el JSON Schema formal.

## Compilacion es semiautomatica

Despues de correr `compile_rules.py`, **revisa manualmente** `rules.json`:

- Reglas duplicadas si una quedo partida entre dos trozos.
- Categoria o severidad que no coincida con tu criterio.
- `check_type` que deberia ser `llm` pero quedo como `automatico` (o viceversa).
- IDs duplicados (no deberia pasar, pero verificar).

## Que hace el server con cada campo

| Campo en `validate_rules.py` | Como se usa |
|---|---|
| `id` | Aparece en `findings[].rule_id`. |
| `category` | Despacha al handler `_check_<categoria>`. |
| `title` + `description` | Se exponen al LLM para que entienda la regla. |
| `severity` | Informativo (no afecta el comportamiento hoy). |
| `check_type` | Decide si va a `findings` (automatico) o `pending_llm_review` (llm). |
| `detection` | Se anexa a la evidencia del finding. |
| `rationale` | Se ignora (placeholder). |

## Categories disponibles en `validate_rules.py`

| Categoria | Que verifica |
|---|---|
| `modelo_datos` | Tabla de fechas marcada. |
| `medidas_dax` | formatString, VAR, FILTER, EARLIER, iteraciones. |
| `rendimiento` | Senales varias (cardinalidad, agregaciones, automatic date). |
| `nomenclatura` | Tipos de dato, ocultos. |
| `reporte_visual` | Titulos de paginas, max visuales. |
| `seguridad` | Placeholder (skipped por ahora). |
| `documentacion` | Placeholder (skipped por ahora). |

Si agregas una regla con una categoria que no tiene handler, devuelve `"skipped"` siempre.

## Limitaciones conocidas

- El parser TMDL (`server/tools/read_pbip.py`) usa regex. Funciona bien para proyectos estandar. Si un modelo TMDL tiene sintaxis exotica, puede fallar. Esto es independiente de la compilacion de reglas.
- Si una regla queda partida justo en el borde de un trozo (~2500 caracteres), puede salir duplicada o incompleta en `rules.json` — revisar manualmente despues de compilar.
- El resultado del LLM no es 100% deterministico (aunque se llama con `temperature=0`). Si necesitas reproducibilidad exacta, fija el modelo y revisa el diff despues de recompilar.
- Sin LLM disponible (Ollama apagado y sin API key), `compile_rules.py` falla — no hay modo offline sin LLM.

## Como agregar reglas manualmente

Edita `rules.json`. Schema en `rules/schema.json`. Despues de editar, corre `uv run pytest` (el test `test_real_rules_json_validates_against_schema` valida contra el schema).

## Como agregar categorias nuevas al handler de validacion

En `server/tools/validate_rules.py`, agregar un handler en `_eval_by_category`:

```python
def _eval_by_category(rule: dict, model: dict) -> tuple[str, str]:
    category = rule.get("category", "")
    if category == "mi_categoria_nueva":
        return _check_mi_categoria(model, rule)
    ...

def _check_mi_categoria(model, rule) -> tuple[str, str]:
    # logica aqui
    return "pass", "..."
```

Y agregar `mi_categoria_nueva` al enum en `rules/schema.json`.

## Elegir modelo LLM

```bash
uv run python rules/compile_rules.py --llm-model ollama/qwen2.5-coder:14b
```

### Variables de entorno

| Variable | Que hace |
|---|---|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `GEMINI_API_KEY` | API key cloud (cualquiera habilita `is_available()`). |
| `MINIMAX_API_KEY` | API key de **MiniMax** (modelo `MiniMax-M3`, etc.). |
| `MINIMAX_API_BASE` | Endpoint de MiniMax (default: `https://api.minimax.io/v1`). Para China: `https://api.minimaxi.com/v1` o setear `MINIMAX_USE_CHINA=1`. |
| `POWERBI_MCP_LLM_MODEL` | Modelo a usar (default: `ollama/gemma3:4b`). Tambien via `--llm-model`. Ejemplos: `minimax/MiniMax-M3`, `gemini/gemini-2.5-flash`. |
| `POWERBI_MCP_LLM_TIMEOUT` | Timeout por trozo en segundos (default: 180). |
| `POWERBI_MCP_LLM_MAX_TOKENS` | Tokens maximos de respuesta por trozo (default: 3000). |
| `POWERBI_MCP_LLM_NUM_CTX` | Contexto de Ollama por trozo (default: 4096). |
| `OLLAMA_API_BASE` | URL del daemon Ollama (default: `http://localhost:11434`). |

Ver [docs/proyecto/ollama-setup.md](../proyecto/ollama-setup.md) para setup de Ollama local (gratis, privado, sin rate limits).

### Proveedores: Ollama vs MiniMax vs otros cloud

| Aspecto | Ollama local | MiniMax | Gemini / OpenAI / Anthropic |
|---|---|---|---|
| Costo | $0 despues de descargar | $0 (free tier) / bajo | $0.01-2 por run |
| Privacidad | 100% local | Datos salen a MiniMax | Datos salen al provider |
| Rate limits | Ninguno | Generoso free tier | Si (free tier agotable) |
| Calidad maxima | Media-alta (depende del modelo) | Alta (M3 ~Claude level) | Muy alta (cloud mas grandes) |
| Setup | Instalar Ollama + pull modelo | Solo API key | Solo API key |
| Velocidad | ~13-30s/trozo en CPU | ~2-5s/trozo (cloud) | ~2-5s/trozo (cloud) |

**Cuando usar cada uno:**

- **Ollama local**: uso recurrente, datos sensibles, CI/CD, sin internet, gratis total.
- **MiniMax** (recomendado para cloud): buena relacion calidad/precio, free tier generoso, ~5-10x mas rapido que Ollama CPU.
- **OpenAI / Anthropic / Gemini**: maxima calidad en titulos/categorias, una corrida puntual.

### Que aporta cada campo extra al agente

| Campo | Para que sirve |
|---|---|
| `scope` | A que artefacto aplica la regla. El validador puede usar esto para acotar la busqueda. |
| `keywords` | Terminos que un LLM agente buscaria en TMDL/DAX para detectar candidatos a violacion. |
| `example_violation` | Ejemplo concreto, util para few-shot prompting. |
| `source_chunk` | Cita del texto original — auditoria de por que se genero la regla. |

Todos son opcionales en el schema.
