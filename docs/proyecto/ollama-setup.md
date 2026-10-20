# Ollama (LLM local gratuito)

Setup para correr el extractor LLM **sin gastar un centavo** y **sin enviar datos a internet**.

## Que es Ollama

Ollama es un servidor de LLMs open-source que corre en tu maquina. Descarga los pesos del modelo y los ejecuta con CPU o GPU local. Ideal para:

- 100% gratis (despues de la descarga inicial)
- 100% privado (tus chunks del PDF nunca salen de tu maquina)
- Sin rate limits ni cuotas

## Instalacion (una sola vez, ~5-10 min)

### Windows

1. Descarga el instalador desde https://ollama.com/download (~300 MB).
2. Ejecuta el instalador. Ollama queda corriendo como servicio de Windows.
3. Verifica que esta activo:
   ```powershell
   ollama --version
   # deberia decir algo como "ollama version 0.x.x"
   ```

### macOS / Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Verificar que el daemon esta corriendo

```powershell
# PowerShell
Invoke-WebRequest http://localhost:11434/api/tags | Select-Object -ExpandProperty Content
```

o en Python:

```bash
uv run python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3).read()[:200])"
```

Deberia devolver JSON con los modelos descargados.

## Descargar un modelo

```powershell
# El default del proyecto (rapido en CPU, alcanza para JSON estructurado)
ollama pull gemma3:4b                # 3 GB, el "4B de Google" original

# Alternativas con mejor calidad (mas lentas en CPU sin GPU):
ollama pull qwen2.5-coder:7b         # 5 GB, balance calidad/velocidad
ollama pull qwen2.5-coder:14b        # 9 GB, mejor calidad, pero mas lento en CPU
ollama pull llama3.1:8b              # 5 GB, generalista
ollama pull mistral:7b               # 4 GB, mas rapido

# Alternativas mas grandes (mejor calidad, requieren mas RAM y son lentas sin GPU):
ollama pull qwen2.5-coder:32b       # 20 GB, maxima calidad local
ollama pull llama3.1:70b             # 40 GB, top-tier pero pesado
```

### Requisitos de hardware

| Modelo | Disco | RAM (CPU) | VRAM (GPU) |
|---|---|---|---|
| `gemma3:4b` | 3 GB | 6 GB | 4 GB |
| `qwen2.5-coder:7b` | 5 GB | 10 GB | 6 GB |
| `qwen2.5-coder:14b` | 9 GB | 16 GB | 10 GB |
| `qwen2.5-coder:32b` | 20 GB | 32 GB | 20 GB |

**GPU NVIDIA recomendada**: mejora 5-10x la velocidad. Sin GPU, CPU funciona pero tarda mas.

## Uso en este proyecto

El proyecto detecta automaticamente Ollama. No necesitas configurar nada extra:

```bash
# Setup una sola vez: descarga el modelo
ollama pull qwen2.5-coder:14b

# Despu�s, todo funciona normal:
uv run scripts/run.py all
```

### Lo que pasa automaticamente

1. `is_available()` hace un GET a `http://localhost:11434/api/tags` (timeout 1.5s).
2. Si Ollama responde, `compile_rules.py` usa el extractor LLM (no hay modo regex — sin LLM disponible, el compilado falla con un mensaje claro).
3. El documento se divide en trozos de ~2500 caracteres y se hace una llamada nativa a Ollama por trozo (mas rapido que pasar por litellm).
4. Si Ollama se cae durante el run, ese trozo reintenta hasta 3 veces y despues falla el compile completo (no hay fallback silencioso).

### Cambiar el modelo

Via variable de entorno (no requiere tocar codigo):

```powershell
# PowerShell
$env:POWERBI_MCP_LLM_MODEL = "ollama/qwen2.5-coder:14b"
uv run scripts/run.py all
```

O via flag:

```bash
uv run scripts/run.py compile --llm-model ollama/qwen2.5-coder:7b
```

## Troubleshooting

### "Ollama no responde en http://localhost:11434"

- **Windows**: Ollama deberia correr como servicio. Verifica en el Administrador de Tareas que `ollama.exe` esta activo. Si no, ejecuta `ollama serve` manualmente.
- **Linux/macOS**: corre `ollama serve` en otra terminal.

### "model not found"

El modelo no esta descargado. Ejecuta:
```bash
ollama pull <nombre-modelo>
```

### "Connection refused" / timeout

- Verifica que el puerto 11434 no esta bloqueado por firewall.
- Si Ollama corre en otra maquina de tu red: `$env:OLLAMA_API_BASE = "http://192.168.1.100:11434"`.

### Muy lento en CPU

- El documento se manda en trozos de ~2500 caracteres (no de una sola vez — un intento con el documento completo tardo >15 min y dio timeout). Aun asi, cada trozo puede tardar 1-3 minutos en CPU sin GPU.
- Soluciones:
  1. Usar el modelo default (`gemma3:4b`, ya es el mas chico recomendado).
  2. Subir el timeout por trozo si el modelo progresa pero no llega a tiempo: `$env:POWERBI_MCP_LLM_TIMEOUT = 300`.
  3. Usar un provider cloud para esa corrida puntual (mas rapido, tiene costo).
  4. Comprar una GPU NVIDIA con 8+ GB VRAM (~$200-400 USD) — mejora 5-10x.

### "Out of memory"

- El modelo no cabe en RAM. Soluciones:
  1. Cerrar otras aplicaciones pesadas (Chrome, IDEs, etc.).
  2. Usar un modelo mas chico.
  3. Verificar cuanta RAM tienes: `(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize / 1MB` (en GB).

## Cost comparison

| Setup | Costo total | Privacidad | Velocidad (documento de ~30 reglas, varios trozos) |
|---|---|---|---|
| **Ollama local** | $0 despues de descargar | 100% privada | Minutos con GPU; puede ser 10-20+ min en CPU sin GPU |
| Gemini flash (cloud) | $0 con rate limits | Datos a Google | Segundos a minutos (limitado por 429) |
| GPT-4o-mini / Claude Haiku (cloud) | ~$0.05-0.20 por run | Datos al provider | Segundos a minutos |

**Recomendacion**: Ollama local para uso recurrente/datos sensibles si tenes GPU o paciencia. Si tu maquina es CPU-only y necesitas velocidad, un provider cloud es mucho mas rapido para una corrida puntual.

## Comandos utiles

```bash
ollama list                          # lista modelos descargados
ollama rm <modelo>                   # borra un modelo (libera disco)
ollama show <modelo>                 # info detallada del modelo
ollama ps                            # modelos cargados en memoria ahora
ollama stop <modelo>                 # descarga un modelo de RAM/VRAM
```
