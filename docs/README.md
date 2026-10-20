# Documentacion del proyecto

Toda la documentacion del proyecto vive en esta carpeta, separada en dos carpetas segun a quien le habla. Esta pagina es el indice.

## `proyecto/` — documentacion humana del proyecto

Todo lo que explica el proyecto en si (por que existe, como se desarrolla, como se despliega, como se conecta a clientes):

| Doc | Que explica |
|---|---|
| [proyecto/plan.md](proyecto/plan.md) | Plan original del proyecto (objetivos, principios, fases, criterios de listo). |
| [proyecto/architecture.md](proyecto/architecture.md) | Estructura del proyecto, que hace cada archivo, como fluye la informacion. |
| [proyecto/dev-workflow.md](proyecto/dev-workflow.md) | Comandos uv, suite de tests, sincronizacion del skill, ciclo de desarrollo. |
| [proyecto/deployment.md](proyecto/deployment.md) | Roadmap para llevar el server a produccion (Hitos 1-4: HTTP, Docker, auth, multiusuario). |
| [proyecto/lan-deployment.md](proyecto/lan-deployment.md) | Guía para desplegar el servidor MCP en tu PC y compartirlo en toda la LAN/WiFi. |
| [proyecto/integracion-claude.md](proyecto/integracion-claude.md) | Como conectar el server a Claude Desktop y Claude Code CLI. |
| [proyecto/ollama-setup.md](proyecto/ollama-setup.md) | Setup de Ollama local para el extractor LLM (gratis, privado). |
| [proyecto/skill-system.md](proyecto/skill-system.md) | Distribucion del skill de Power BI, sincronizacion entre las 3 ubicaciones. |

## `reglas-mcp/` — reglas que compila y sirve el MCP

El documento de entrada de buenas practicas y como se compila a `rules/rules.json`:

| Doc | Que explica |
|---|---|
| [reglas-mcp/rules-compilation.md](reglas-mcp/rules-compilation.md) | Como se compilan las reglas desde el PDF/DOCX a `rules/rules.json` (extraccion con markitdown, parser regex + LLM), estructura del JSON, heuristicas. |
| [reglas-mcp/Checklist de Buenas Practicas Power BI 1.1 7 (1).pdf](reglas-mcp/Checklist%20de%20Buenas%20Pr%C3%A1cticas%20Power%20BI%201.1%207%20(1).pdf) | Documento de entrada que se compila a `rules.json`. |

## Docs para el agente LLM

Todo lo que consume el LLM vive en [`agent/`](agent/) (separado para no mezclar con la documentacion humana):

- [agent/README.md](agent/README.md) — indice.
- [agent/SKILL_POWER_BI.md](agent/SKILL_POWER_BI.md) — skill canonico de Power BI.
- [agent/agent-guide.md](agent/agent-guide.md) — guia operativa: como invocar las 4 tools, flujo recomendado, manejo de errores.

Estos se exponen al agente via MCP resources (`power-bi://reference` y `usage://getting-started`).

## Como agregar un nuevo doc

1. Decidir la carpeta: `docs/proyecto/<topic>.md` si habla del proyecto (arquitectura, deploy, dev, clientes); `docs/reglas-mcp/<topic>.md` si es sobre las reglas que valida el MCP; `docs/agent/<topic>.md` solo si el LLM lo va a consumir como resource.
2. Anadir una fila en la tabla correspondiente de arriba.
3. Si el doc tiene informacion que estaba antes en otro archivo (README, comentarios inline, plan viejo): consolidar primero, luego reemplazar.

## Convenciones

- Markdown estandar, links relativos entre docs (`[proyecto/architecture.md](proyecto/architecture.md)`).
- Espanol consistente, terminos tecnicos en ingles cuando es el estandar (MCP, TMDL, etc.).
- Codigo en fences con identificador de lenguaje (` ```python `, ` ```bash `).
- Sin emojis (no se usan aca).
- Si un doc se vuelve obsoleto, archivarlo o borrarlo. No dejar docs "viejos" como referencia.
