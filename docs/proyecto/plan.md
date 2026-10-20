# Plan del proyecto: agente MCP de buenas prácticas y diseño para Power BI

## 1. Objetivo

Construir un servidor MCP (Model Context Protocol) que:

1. Lea modelos de Power BI en formato `.pbip` (avisando si se le da un `.pbix` para que se convierta manualmente desde Power BI Desktop).
2. Valide el modelo contra una guía de buenas prácticas propia, compilada una sola vez en un archivo de reglas estructurado.
3. Pregunte al usuario cuando falte contexto necesario para evaluar o diseñar.
4. Genere una propuesta de diseño: layout de reporte + `theme.json` de Power BI.
5. Funcione igual desde distintos clientes/agentes (VS Code, Claude Desktop, Claude Code, Antigravity, opencode) y con distintos proveedores de LLM (Claude, GPT, Ollama, etc.), sin reescribir el servidor.

## 2. Principios de diseño

- **El servidor MCP es el núcleo reutilizable.** No depende de ningún cliente ni proveedor de LLM. Cada cliente solo necesita un archivo de configuración que le diga cómo lanzarlo (`command` + `args`).
- **Las reglas se compilan una sola vez.** El documento Word/PDF de buenas prácticas se convierte a `rules.json` en un paso aparte (offline). El servidor nunca vuelve a leer el documento original en tiempo de ejecución.
- **Separar validación automática de validación por criterio.** Reglas verificables por código (ej. "¿existe tabla de fechas?") se resuelven sin LLM. Reglas que requieren juicio (ej. "¿el nombre es descriptivo?") se pasan al LLM.
- **El cliente orquesta, el LLM decide, el servidor ejecuta.** El LLM nunca llama directamente al servidor MCP; el cliente es el intermediario entre ambos.
- **Proveedor de LLM intercambiable.** Se abstrae detrás de una interfaz común (recomendado: LiteLLM) para poder cambiar de modelo editando solo un archivo de configuración.

## 3. Estructura del proyecto

```
powerbi-mcp-agent/
├── README.md
├── requirements.txt
├── config.yaml                     # proveedor/modelo LLM activo (si se usa cliente propio)
│
├── docs/
│   └── buenas-practicas.docx       # guía original, tal cual la entregue el usuario
│
├── rules/
│   ├── compile_rules.py            # script de compilación (se corre 1 vez o al actualizar la guía)
│   └── rules.json                  # salida: reglas estructuradas, listas para cargar en memoria
│
├── server/
│   ├── mcp_server.py               # servidor MCP (entry point, carga rules.json al iniciar)
│   ├── tools/
│   │   ├── read_pbip.py            # tool: extrae tablas, medidas, relaciones del .pbip (TMDL/JSON)
│   │   ├── detect_format.py        # tool: detecta .pbix vs .pbip y avisa si hace falta convertir
│   │   ├── validate_rules.py       # tool: aplica reglas automáticas contra el modelo extraído
│   │   └── generate_design.py      # tool: genera theme.json + propuesta de layout
│   └── resources/
│       └── best_practices.py       # resource: expone rules.json como rules://best-practices
│
├── clients/                        # configs de ejemplo por entorno (mismo servidor, distinto cliente)
│   ├── vscode.mcp.json
│   ├── claude_desktop.mcp.json
│   ├── claude_code.mcp.json
│   ├── antigravity.mcp_config.json
│   └── opencode.mcp.json
│
├── proyectos/                      # carpetas .pbip a analizar (input del usuario)
│   └── (vacío, el usuario coloca aquí sus modelos)
│
└── outputs/                        # informes de hallazgos y diseños generados
    └── (se genera en tiempo de ejecución)
```

## 4. Formato de `rules.json` (salida de la compilación)

```json
{
  "rules": [
    {
      "id": "BP-001",
      "category": "modelo_datos",
      "title": "Tabla de fechas marcada",
      "description": "Debe existir una tabla de fechas marcada como Date Table",
      "severity": "alta",
      "check_type": "automatico",
      "detection": "buscar propiedad isDateTable en los .tmdl del modelo"
    },
    {
      "id": "BP-014",
      "category": "reporte_visual",
      "title": "Consistencia de paleta de colores",
      "description": "Los visuales deben usar la paleta corporativa definida",
      "severity": "media",
      "check_type": "llm",
      "detection": "requiere criterio, no es booleano"
    }
  ]
}
```

## 5. Tools y resource que expone el servidor MCP

| Nombre | Tipo | Qué hace |
|---|---|---|
| `detect_format` | tool | Revisa la ruta dada; si es `.pbix` responde pidiendo conversión manual a `.pbip` |
| `read_pbip` | tool | Parsea los `.tmdl` (tablas, medidas, relaciones) y el JSON del layout del reporte |
| `validate_rules` | tool | Corre las reglas `automatico` contra el modelo extraído; devuelve hallazgos + las reglas `llm` pendientes de criterio |
| `generate_design` | tool | A partir del modelo y el objetivo del reporte, genera `theme.json` y una propuesta de layout |
| `rules://best-practices` | resource | Expone `rules.json` para que el cliente lo pida una vez por sesión, sin reinyectarlo en cada mensaje |

## 6. Fases de construcción

### Fase 0 — Definir alcance
- Confirmar que se trabaja solo con `.pbip` locales (conversión desde `.pbix` es manual, vía Power BI Desktop).
- Confirmar formato del documento de buenas prácticas (Word/PDF) y su estructura (categorías, severidad, etc.).

### Fase 1 — Compilación de reglas
- Escribir `compile_rules.py`: extrae texto del Word/PDF y lo estructura en `rules.json` (categoría, severidad, `check_type`).
- Revisar manualmente el JSON generado antes de usarlo (la compilación es semiautomática, no 100% confiable a la primera).

### Fase 2 — Lectura del modelo `.pbip`
- Escribir `read_pbip.py`: recorre `*.SemanticModel/definition/*.tmdl` (tablas, columnas, medidas, relaciones) y `*.Report/definition/*.json` (layout).
- Escribir `detect_format.py`: distingue `.pbix` de `.pbip` y responde con instrucciones si hace falta convertir.

### Fase 3 — Validación automática
- Escribir `validate_rules.py`: aplica cada regla `check_type: automatico` del `rules.json` contra el modelo extraído, sin usar LLM.
- Las reglas `check_type: llm` se devuelven aparte, para que el cliente se las pase al modelo con contexto del proyecto.

### Fase 4 — Servidor MCP
- Ensamblar `mcp_server.py`: carga `rules.json` una vez al iniciar, registra las tools y el resource.
- Probar localmente con un cliente MCP simple (ej. VS Code, como ya se hizo con `cencomedia`).

### Fase 5 — Generación de diseño
- Escribir `generate_design.py`: usa el modelo (tablas, medidas, jerarquías) y el objetivo del reporte (que el agente pregunta si no está claro) para proponer layout + `theme.json`.

### Fase 6 — Multi-cliente
- Crear los archivos de config de ejemplo en `clients/` para VS Code, Claude Desktop, Claude Code, Antigravity y opencode, todos apuntando al mismo `command`/`args`.
- Verificar que el servidor responde igual sin importar el cliente.

### Fase 7 — Proveedor de LLM intercambiable (si se usa un cliente propio en vez de uno ya existente)
- Definir `config.yaml` con el proveedor/modelo activo.
- Integrar LiteLLM (o interfaz propia) para poder alternar entre Claude, GPT u Ollama sin tocar el resto del código.
- Probar el mismo flujo con al menos dos proveedores distintos y comparar calidad de resultados, especialmente en el uso de tools.

### Fase 8 — Mantenimiento
- Cuando cambie el documento de buenas prácticas: solo se re-corre `compile_rules.py` y se reinicia el servidor. Nada más cambia.

## 7. Criterios para saber que cada fase está lista

- **Fase 1:** el `rules.json` cubre todas las reglas del documento original y cada una tiene `check_type` correcto.
- **Fase 2-3:** correr el servidor contra un `.pbip` real y obtener una lista de hallazgos coherente con una revisión manual.
- **Fase 4:** el servidor responde correctamente el handshake MCP (lista sus tools y su resource) desde al menos un cliente.
- **Fase 5:** el `theme.json` generado es válido (se puede importar en Power BI sin errores) y el layout propuesto es razonable para el tipo de reporte pedido.
- **Fase 6:** el mismo servidor funciona sin cambios desde dos clientes distintos.
- **Fase 7:** el flujo completo corre igual cambiando solo el modelo en `config.yaml`.
