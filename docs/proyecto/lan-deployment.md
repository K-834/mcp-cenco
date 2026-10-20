# Guía: Desplegar el servidor MCP en tu PC para toda la LAN

Esta guía describe cómo ejecutar `powerbi-mcp-agent` en tu computadora principal y permitir que otras computadoras o dispositivos en la misma red local (WiFi o LAN) se conecten y usen el servidor MCP.

---

## Requisitos previos

- Python 3.10+ y `uv` instalado.
- Tu PC servidor y los clientes conectados a la misma red WiFi/LAN.
- Permisos de Administrador en el PC servidor para abrir el puerto en el firewall.

---

## Paso 1: Entender los transportes MCP

| Transporte | Uso recomendado | Comando |
|------------|-----------------|---------|
| `stdio` | Uso local en tu propia máquina (default) | `uv run powerbi-mcp` |
| `streamable-http` / `sse` | Red local (LAN) o servidores compartidos | `uv run scripts/run.py server-lan` |

Para que otros equipos se conecten a través de la red local, **debes usar el transporte HTTP**.

---

## Paso 2: Obtener la IP LAN de tu PC Servidor

### Windows (PowerShell / CMD)
```powershell
ipconfig
```
Busca **Dirección IPv4** en tu adaptador de red o WiFi (ejemplo: `192.168.1.45`).

### Linux / WSL2
```bash
hostname -I
```

### macOS
```bash
ipconfig getifaddr en0
```

**Anota esta IP local** (ej. `192.168.1.45`).

---

## Paso 3: Abrir el puerto en el Firewall

Por defecto el servidor escucha en el puerto **8000/TCP**. Debes permitir las conexiones entrantes a este puerto.

### Windows (PowerShell como Administrador)
Ejecuta el siguiente comando en una consola de PowerShell elevada:
```powershell
New-NetFirewallRule -DisplayName "PowerBI MCP Server 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

O desde la interfaz gráfica:
1. Abre **Firewall de Windows Defender con seguridad avanzada**.
2. Selecciona **Reglas de entrada** → **Nueva regla...**
3. Elige **Puerto** → **TCP** → **Puertos locales específicos: 8000**.
4. Selecciona **Permitir la conexión** y guarda la regla.

### Linux (UFW)
```bash
sudo ufw allow 8000/tcp
```

### macOS
1. Ve a **Preferencias del Sistema** → **Seguridad y Privacidad** → **Firewall**.
2. Añadir la aplicación de Python/uv a las excepciones de entrada.

---

## Paso 4: Iniciar el servidor en modo LAN

Ejecuta el servidor con el comando de desarrollo preparado:

```bash
uv run scripts/run.py server-lan
```

O ejecutando directamente el binario con argumentos:
```bash
uv run powerbi-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp
```

El servidor quedará escuchando en `http://0.0.0.0:8000/mcp` (accesible en `http://<TU-IP-LAN>:8000/mcp`).

---

## Paso 5: Conectar clientes desde otras computadoras

En cualquier otra máquina conectada a la misma red WiFi, configura el cliente MCP deseado especificando la IP de tu PC servidor:

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "powerbi-mcp-lan": {
      "url": "http://192.168.1.45:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### Cursor / OpenCode / Antigravity
Ver la plantilla lista en [`clients/lan.mcp.json`](../../clients/lan.mcp.json):
```json
{
  "mcpServers": {
    "powerbi-mcp-lan": {
      "url": "http://192.168.1.45:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

*Recuerda reemplazar `192.168.1.45` por la IP anotada en el Paso 2.*

---

## Paso 6: Probar la conexión

Desde otra computadora conectada a la LAN, abre una terminal y prueba responder con `curl`:

```bash
curl http://192.168.1.45:8000/mcp
```

Si el servidor responde o establece handshake, la conexión está lista para usarse desde cualquier cliente MCP.

---

## Solución de problemas comunes

### Error: "Connection refused" o "No se puede conectar"
1. Verifica que el servidor esté activo corriendo en el PC host (`uv run scripts/run.py server-lan`).
2. Comprueba que el puerto 8000 esté abierto en el Firewall del PC host.
3. Asegúrate de que ambas máquinas estén en la misma red WiFi (y no en la red de invitados).

### La IP cambia cada vez que reinicias la PC
- Configura una **IP fija/estática** en la configuración de red de tu sistema operativo o reserva la IP en tu router.
- O bien utiliza la resolución de nombres mDNS de tu red (ejemplo: `http://mi-pc.local:8000/mcp`).
