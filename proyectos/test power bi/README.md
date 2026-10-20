# Carpeta de prueba — proyecto Power BI real

Esta carpeta contiene un proyecto `.pbip` real usado como caso de prueba del agente MCP. El subagent descubrira cualquier archivo `.pbip` dentro de esta carpeta al ejecutar los tests.

## Contenido actual

- `Reporte Indicadores Wong Prime Omnicanal.pbip` — descriptor del proyecto.
- `*.SemanticModel/` — modelo semantico con tablas, medidas y relaciones.
- `*.Report/` — definicion del reporte con paginas y visuales.

## Uso

Desde Power BI Desktop: Archivo > Abrir > Examinar y seleccionar esta carpeta. Power BI Desktop carga el `.pbip` y todo el modelo.

Desde el server MCP: pasar la ruta de esta carpeta a la tool `detect_format`. La salida incluye las rutas del SemanticModel y del Report, listas para las tools `read_pbip`, `validate_rules` y `generate_design`.

## Que validar contra este modelo

| Tool | Esperado |
|---|---|
| `detect_format` | `format: "pbip"`, `ok: true` |
| `read_pbip` | Tablas (incluye `DateTableTemplate_*` y `LocalDateTable_*`), medidas con/sin formatString, relaciones bidireccionales y unidireccionales, paginas |
| `validate_rules` | BP-001 PASS, BP-002 WARNING (relaciones bidireccionales), BP-010 WARNING (medidas sin formato), BP-050 SKIPPED |
| `generate_design` | `theme.json` + 2 paginas de layout |

## Nota

Este es un proyecto real, no un fixture sintetico. Si lo reemplazas o renombras, los tests siguen funcionando porque `conftest.py` descubre el `.pbip` por glob. Si lo eliminas, los tests fallaran con un mensaje indicando que no hay proyecto.
