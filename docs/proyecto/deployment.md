# Deployment: llevar el server a produccion

Roadmap para que el server deje de ser local-only y pueda ser usado por multiples usuarios.

## Vision

| Escenario | Descripcion | Cuando aplica |
|---|---|---|
| **A. Distribucion** | Cada usuario instala el paquete localmente (PyPI o uv tool). | 1-5 usuarios, baja friccion. |
| **B. Servicio interno** | Server HTTP compartido en una infra de la empresa, con auth basica. | 5-100 usuarios, auth corporativo. |
| **C. SaaS publico** | Hosting en cloud con auth, billing, landing, compliance. | 100+ usuarios, monetizacion o acceso externo. |

Esta pagina describe **B + C**. Para A, basta con `uv tool install powerbi-mcp-agent` o publicar a PyPI.

## Hitos

### Hito 0 — Preparacion (1-2 dias)

No toca codigo. Documenta:

- Transporte: `streamable-http` (moderno, recomendado) o `sse` (legacy).
- Donde corre: VM propia, PaaS (fly.io, Railway, Render), Kubernetes.
- Quien paga el LLM: cada usuario (estado actual) o la empresa (futuro).

**Salida**: `docs/deployment.md` (este archivo). Si se decide distinto, se actualiza aca.

### Hito 1 — Server HTTP basico (3-5 dias)

Convertir el server de stdio a HTTP.

**Cambios al server**:

1. Transporte HTTP en `mcp_server.py`:
   ```python
   if __name__ == "__main__":
       mcp.settings.host = os.environ.get("HOST", "0.0.0.0")
       mcp.settings.port = int(os.environ.get("PORT", 8000))
       mcp.run(transport="streamable-http")
   ```
2. Healthcheck: ruta `/ping` que devuelve `{"status": "ok", "tools": [...]}`.
3. Variables de entorno:
   - `POWERBI_MCP_HOST` (default `0.0.0.0`)
   - `POWERBI_MCP_PORT` (default `8000`)
   - `POWERBI_MCP_RULES_PATH` (ruta al `rules.json`)
   - `POWERBI_MCP_LOG_LEVEL` (default `INFO`)

**Tests**: agregar tests que verifiquen handshake MCP via HTTP y `/ping`.

**Resultado**: `uv run scripts/run.py server-lan` o `uv run powerbi-mcp --transport streamable-http` levanta el server en `http://0.0.0.0:8000`.

> Para una guía paso a paso sobre cómo usarlo en tu red local WiFi y configurar clientes en otras computadoras, consulta [lan-deployment.md](lan-deployment.md).

### Hito 2 — Contenedor y deploy (2-3 dias)

**Dockerfile multi-stage**:
```dockerfile
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app
WORKDIR /app
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD ["uv", "run", "powerbi-mcp"]
```

**Docker Compose**:
```yaml
services:
  powerbi-mcp:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./rules:/app/rules:ro
    environment:
      - POWERBI_MCP_RULES_PATH=/app/rules/rules.json
```

**Where**:
- **VM propia**: $5-20/mes, control total.
- **fly.io / Railway / Render**: $5-50/mes, deploy con `git push`, HTTPS automatico. **Recomendado** para arrancar.
- **Kubernetes**: si ya tenes cluster.

### Hito 3 — Auth y multi-usuario (3-5 dias)

Opciones de auth ordenadas por complejidad:

| Opcion | Implementacion | Tiempo | Cuando |
|---|---|---|---|
| API keys simples (env var) | Lista de keys en `POWERBI_MCP_ALLOWED_KEYS`. Header `Authorization: Bearer <key>`. | 1 dia | Equipo pequeno (<20), baja seguridad. |
| API keys con scopes | Cada key tiene `read`/`write`/`admin`. Middleware. | 2 dias | Equipo mediano, separar permisos. |
| OAuth corporativo (Azure AD / Google Workspace / Okta) | Integracion via OAuth provider del MCP SDK. | 3-5 dias | Empresa real con IdP. |
| mTLS | Certificados de cliente. Requiere PKI interna. | 4-6 dias | Compliance estricto. |

Para arrancar: **API keys con scopes** (suficiente para empezar, se migra a OAuth si crece).

**Implementacion minima viable**:

```python
ALLOWED_KEYS = set(os.environ.get("POWERBI_MCP_ALLOWED_KEYS", "").split(","))

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] not in ALLOWED_KEYS:
            raise PermissionError("invalid or missing key")
        return func(*args, **kwargs)
    return wrapper
```

### Hito 4 — Aislamiento de modelos (opcional, 2-4 dias)

Si cada usuario sube sus propios `.pbip` y no queres que se mezclen:

- **Por convencion de paths**: cada usuario tiene `proyectos/<username>/`. Simple, sin codigo nuevo.
- **Storage aislado**: cada usuario sube a S3/Azure Blob con prefijo. Requiere cambios en `detect_format` y `read_pbip` para aceptar URLs.
- **Sandbox**: cada usuario corre su propia instancia. No recomendado (rompe el modelo de server compartido).

Recomendacion: arrancar con paths por usuario.

## Roadmap de tiempos

| Hito | Cuando | Bloqueante |
|---|---|---|
| 0 | Ahora (ya esta documentado) | No |
| 1 | Semana 1 | Si |
| 2 | Semana 2 | Si |
| 3 | Semana 3 | Si para uso real |
| 4 | Semana 4+ | No, opcional |

**Tiempo total bloqueante**: 3 semanas. **Tiempo total con Hito 4**: 4 semanas.

## Costos

| Concepto | Costo estimado |
|---|---|
| PaaS para el server (fly.io/Railway) | $5-50/mes |
| VM propia equivalente | $5-20/mes |
| Kubernetes manejado | $50-500/mes |
| LLM por usuario | Lo paga cada usuario (estado actual) |
| Dominio + TLS | $0-15/mes |

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Usuario sube .pbip con datos sensibles y se filtra | Auth + audit log + politicas internas |
| Server cae y nadie puede trabajar | Healthcheck + auto-restart + status page |
| Alguien abusa (costo de LLM) | Rate limiting por usuario; recordar que cada uno paga el suyo |
| TLS caduca sin aviso | Si usas PaaS, TLS automatico. Si usas VM, Caddy. |
| Cambias `rules.json` y server queda inconsistente | Hot-reload con versionado; clients pueden recargar el resource |

## Lo que NO cambia para el usuario

- Cada usuario sigue pagando su API key de Anthropic/OpenAI.
- Misma instalacion: solo cambia el endpoint de `command: ...` a `url: ...`.
- Misma API del server (tools + resources).
- Los clientes MCP favoritos (opencode, Claude Desktop, VS Code) siguen funcionando.

## El unico cambio visible para el usuario

| Antes | Despues |
|---|---|
| `"command": ["uv", "run", "--project", "...", "python", "server/mcp_server.py"]` | `"url": "https://powerbi-mcp.empresa.com/mcp"` + key |

## Variables de entorno necesarias en produccion

```bash
HOST=0.0.0.0
PORT=8000
POWERBI_MCP_RULES_PATH=/app/rules/rules.json
POWERBI_MCP_LOG_LEVEL=INFO
POWERBI_MCP_ALLOWED_KEYS=key1,key2,key3
LOG_LEVEL=INFO
```

## Decisiones pendientes

| Cuestion | Estado actual | Cuando decidir |
|---|---|---|
| Quien paga el LLM | Cada usuario paga el suyo | Cuando crezca el uso interno |
| HTTPS | PaaS lo da automatico | Hito 2 |
| Rate limiting por usuario | No implementado | Hito 3 o 4 |
| Audit log | No implementado | Hito 4 |
| Compliance (SOC2, GDPR) | No requerido todavia | Cuando haya clientes externos |
| Billing (SaaS) | No requerido todavia | Escenario C |

## Cuando arrancar

Cuando tengas 3+ personas que quieran usarlo. Con 1-2, sigue siendo mas simple la distribucion local (instalacion via `uv tool install` o equivalente). Volve a este doc cuando estes listo y arranca por el Hito 1.
