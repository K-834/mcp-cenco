# PowerBI MCP Agent & Power BI Skills para Claude 🤖📊

Servidor **MCP (Model Context Protocol)** y suite completa de **Skills de Power BI** optimizados y diseñados exclusivamente para **Claude** (**Claude Desktop** y **Claude Code CLI**).

Permite que Claude valide, audite bajo 36 reglas de buenas prácticas, diseñe reportes, escriba código DAX/TMDL y manipule proyectos Power BI en formato `.pbip` y `.pbir`.

---

## 🚀 Instalación en 1 Línea (Sin clonar el repo)

Cualquier persona puede instalar todo el servidor MCP y las Skills ejecutando este comando:

### En Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/K-834/mcp-cenco/main/setup_claude.py | python -
```

### En macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/K-834/mcp-cenco/main/setup_claude.py | python3 -
```

---

## ⚡ Instalación si ya descargaste el repositorio

### En Windows:
Haz doble clic en **`install.bat`** o ejecútalo desde tu terminal:
```cmd
install.bat
```

### En macOS / Linux:
```bash
chmod +x install.sh
./install.sh
```

### Manualmente con `uv`:
```bash
uv sync
uv run python scripts/install.py
```

### ¿Qué hace el instalador automáticamente?
1. **Configura el servidor MCP en Claude Desktop**: Actualiza `claude_desktop_config.json` apuntando directamente a las herramientas del proyecto.
2. **Configura Claude Code CLI**: Registra el servidor MCP en Claude Code (`~/.claude.json` / `claude mcp add`).
3. **Instala las Skills en Claude**: Copia los 6 skills de Power BI en el directorio global de skills de Claude (`~/.claude/skills/`) para que estén disponibles inmediatamente en cualquier conversación.

---

## 🧠 Skills de Power BI instaladas en Claude

Claude tendrá cargadas las siguientes capacidades especializadas:

1. **`logica-bi-pbip-cenco`**: Auditoría automática de 36 reglas de modelado (esquema estrella, medidas con formato, relaciones 1:* unidireccionales, fechas, performance) y diseño HTML/CSS para el visual "HTML Content".
2. **`powerbi-report-planning`**: Flujo ordenado de requerimientos, inspección del modelo, spec de diseño y validación de alcance.
3. **`powerbi-report-design`**: Arquetipos de reporte, paletas corporativas, accesibilidad y tipografía.
4. **`powerbi-report-authoring`**: Creación y edición automatizada de visuales PBIR y layouts de página.
5. **`powerbi-report-management`**: Administración y publicación de reportes hacia Microsoft Fabric via API REST.
6. **`semantic-model-authoring`**: Inspección y authoring de modelos semánticos TMDL, DAX y Direct Lake.

---

## 🛠️ Herramientas MCP Disponibles en Claude

Una vez instalado, Claude puede ejecutar estas herramientas en tus proyectos Power BI:

| Herramienta MCP | Descripción |
|---|---|
| `detect_format(path)` | Detecta si es `.pbix` o `.pbip` y extrae rutas de trabajo. |
| `read_pbip(sm_path, report_path)` | Parsea el modelo semántico TMDL y reportes PBIR. |
| `validate_rules(model)` | Audita el modelo contra 36 reglas automáticas de calidad. |
| `write_dax_measure(...)` | Agrega o actualiza medidas DAX de forma segura en los archivos TMDL. |
| `write_pbir_layout(...)` | Escribe layouts PBIR adaptables a resolución y grid design. |
| `write_tmdl_relationship(...)` | Añade o modifica relaciones entre tablas en TMDL. |
| `disable_auto_date_time(...)` | Desactiva las tablas de tiempo automáticas para reducir el peso del modelo. |
| `check_pbi_desktop_status()` | Verifica si Power BI Desktop está abierto con el modelo cargado. |
| `query_dax(query)` | Ejecuta queries DAX en vivo contra el modelo en memoria. |
| `generate_pbip_docx(...)` | Genera documentación funcional y técnica integral en `.docx`. |
| `generate_design(model, goal)` | Genera propuesta de diseño y `theme.json` según el objetivo del reporte. |

---

## 🧪 Verificación de Tests

```bash
uv sync --group dev
uv run pytest
```

---

## 📄 Licencia

MIT License.
