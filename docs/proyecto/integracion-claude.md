# Integracion con clientes Claude

Como conectar el server MCP con **Claude Desktop** y **Claude Code CLI**.

## TL;DR

```bash
# Claude Desktop (la app):
uv run scripts/install_claude.py install-desktop

# Claude Code CLI (la terminal):
uv run scripts/install_claude.py install-code

# Ambos:
uv run scripts/install_claude.py install-all

# Ver donde esta instalado:
uv run scripts/install_claude.py status

# Desinstalar:
uv run scripts/install_claude.py uninstall
```

O via el script unico:

```bash
uv run scripts/run.py claude install-desktop
uv run scripts/run.py claude install-code
uv run scripts/run.py claude install-all
uv run scripts/run.py claude status
uv run scripts/run.py claude uninstall
```

## Que hace el script

`scripts/install_claude.py` automatiza la instalacion:

- **Claude Desktop**: lee `%APPDATA%/Claude/claude_desktop_config.json`, agrega `mcpServers.powerbi-mcp` con el comando correcto, preserva el resto de tu config existente (preferencias, otras entradas mcpServers, etc.), escribe de vuelta.
- **Claude Code CLI**: ejecuta `claude mcp add powerbi-mcp --command uv --args "run --project <ruta> python server/mcp_server.py"`.
- Ambos subcomandos son idempotentes: si ya esta instalado, dicen "[=] Ya instalado".
- `--uninstall` elimina solo la entrada `powerbi-mcp`; no toca el resto del config.

## Por que `uv run --project ...` y no `python` directo

El comando que Claude ejecuta al levantar el server es:

```
uv run --project "C:/Users/.../powerbi-mcp-agent" python server/mcp_server.py
```

Esto garantiza que:
- Se use el Python del `.venv/` del proyecto (no el Python del sistema).
- Las dependencias (`mcp`, `pypdf`, `litellm`, etc.) esten disponibles sin tener que instalarlas globalmente.
- Funcione aunque moviste el proyecto a otra carpeta (solo edita el path en `scripts/install_claude.py`).

## Claude Desktop paso a paso

1. **Asegurate que Claude Desktop este cerrado** antes de editar el config.
2. Ejecuta:
   ```bash
   uv run scripts/install_claude.py install-desktop
   ```
3. **Reinicia Claude Desktop** (hamburguesa > Quit, luego abrir de nuevo). Claude no recarga MCP en caliente.
4. Acepta el trust prompt que aparece al usar el server por primera vez.
5. En el chat, escribe:
   ```
   @powerbi-mcp analiza el modelo en proyectos/test power bi
   ```
   Claude deberia invocar las tools automaticamente.

### Si queres hacerlo manualmente

En lugar del script, podes copiar el archivo directamente:

```bash
# Windows PowerShell:
Copy-Item -LiteralPath "clients/claude_desktop.mcp.json" `
              -Destination "$env:APPDATA\Claude\claude_desktop_config.json" -Force

```

El archivo destino es `%APPDATA%/Claude/claude_desktop_config.json` en Windows.

## Claude Code CLI paso a paso

1. **Instala Claude Code** desde https://claude.com/claude-code.
2. Asegurate de que `claude` este en tu PATH (`where claude` en Windows).
3. Ejecuta:
   ```bash
   uv run scripts/install_claude.py install-code
   ```
4. Iniciá una sesion de Claude Code en cualquier directorio:
   ```bash
   claude
   ```
5. Claude Code detecta el server MCP y lo levanta on-demand al primer uso.
6. Escribi lo mismo que con Claude Desktop:
   ```
   @powerbi-mcp analiza el modelo en proyectos/test power bi
   ```

### Si tenes varios workspaces

Claude Code CLI soporta 3 alcances:

| Scope | Path | Cuando usarlo |
|---|---|---|
| User (global) | `~/.claude.json` | Para todos tus proyectos. |
| Project (local) | `.mcp.json` en la raiz del proyecto | Solo en ese proyecto, commiteable. |
| Local | `~/.claude.json` con flag `--local` | Solo en tu maquina, no commiteable. |

El script `install-code` registra en user scope (global). Si queres registrar solo en este proyecto:

```bash
# Crea .mcp.json en la raiz del proyecto con este contenido:
cat > .mcp.json <<'EOF'
{
  "mcpServers": {
    "powerbi-mcp": {
      "command": "uv",
      "args": ["run", "--project", "<RUTA_ABSOLUTA>", "python", "server/mcp_server.py"]
    }
  }
}
EOF
```

## Que ve el agente Claude

Cuando Claude se conecta al server MCP, automaticamente descubre:

- **4 tools**: `detect_format`, `read_pbip`, `validate_rules`, `generate_design`.
- **3 resources**: `rules://best-practices`, `power-bi://reference`, `usage://getting-started`.

Claude puede pedir los resources cuando lo necesita para tener contexto del dominio Power BI, de las reglas a aplicar, y de como invocar las tools correctamente.

## Troubleshooting

| Sint | Causa probable | Fix |
|---|---|---|
| Claude no muestra tools MCP | El config no se escribio bien o Claude no se reinicio | Cerrar y reabrir Claude Desktop. Verificar el JSON. |
| Server arranca pero tools fallan | `uv` no esta en PATH del proceso Claude | Agregar `uv` al PATH del sistema o usar ruta absoluta en el config. |
| `ModuleNotFoundError: No module named 'mcp'` | uv no esta activando el venv | Verificar que `uv run python -c "import mcp"` funcione desde terminal. |
| 'claude' CLI no encontrado | Claude Code no instalado | Instalar desde https://claude.com/claude-code. |
| El agente invoca tools con argumentos incorrectos | Falta contexto | Pedir el resource `usage://getting-started` al inicio de la sesion. |

## Como revertir

```bash
uv run scripts/install_claude.py uninstall
```

Esto elimina la entrada `powerbi-mcp` de:
- `%APPDATA%/Claude/claude_desktop_config.json` (Claude Desktop).
- `~/.claude.json` (Claude Code CLI via `claude mcp remove`).

No toca ninguna otra config.