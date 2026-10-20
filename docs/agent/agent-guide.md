# Guia operativa para el agente

Este servidor MCP expone 4 tools + 3 resources. Esta guia describe **como usarlos en orden**, **cuando llamar a cada uno**, y **que hacer con cada respuesta**. El objetivo: que el agente LLM sepa ejecutar una auditoria o un diseno de un modelo `.pbip` de forma autonoma.

## Indice rapido

1. [Tools disponibles](#tools-disponibles)
2. [Resources disponibles](#resources-disponibles)
3. [Flujo recomendado para una auditoria](#flujo-recomendado-para-una-auditoria)
4. [Flujo recomendado para generar un diseno](#flujo-recomendado-para-generar-un-diseno)
5. [Cuando pedir contexto al usuario](#cuando-pedir-contexto-al-usuario)
6. [Errores comunes y como manejarlos](#errores-comunes-y-como-manejarlos)

---

## Tools disponibles

Todas las tools son **sincronicas, idempotentes, sin efectos secundarios**. Reciben parametros como string y devuelven JSON-serializable.

### `detect_format(path: str) -> dict`

Inspecciona si la ruta dada es un proyecto Power BI valido.

**Cuando usarla**: primera tool a invocar en cualquier tarea. Te dice si podes continuar o si el usuario debe convertir primero.

**Parametros**:
- `path`: ruta absoluta a archivo `.pbip`, carpeta de proyecto, archivo `.pbix`, o cualquier otra cosa.

**Respuestas tipicas**:

```json
{"format":": "pbip", "ok": true,  "semantic_model": ".../X.SemanticModel", "report": ".../X.Report", "message": "..."}
{"format":": "pbix", "ok": false, "message": "Convertilo en Power BI Desktop: Archivo > Guardar como > Power BI Project (.pbip)"}
{"format":": "missing", "ok": false, "message": "No existe la ruta: ..."}
{"format":": "unknown", "ok": false, "message": "..."}
```

### `read_pbip(semantic_model_path: str, report_path: str) -> dict`

Parsea el modelo semantico (`.tmdl`) y el reporte (`.json`) de un proyecto `.pbip`.

**Cuando usarla**: segunda tool, despues de `detect_format`. Te da el modelo estructurado que las demas tools necesitan.

**Parametros**:
- `semantic_model_path`: ruta al directorio `*.SemanticModel` (de la respuesta de `detect_format`).
- `report_path`: ruta al directorio `*.Report`.

**Respuesta**:

```json
{
  "tables":      [{"name": "...", "is_date_table": true, "source_file": "..."}],
  "measures":    [{"name": "...", "format_string": "#,##0.00", "expression": "..."}],
  "relationships": [{"from": "T.x", "to": "T.y", "cross_filter": "oneDirection|bothDirections"}],
  "pages":       [{"name": "...", "page_id": "..."}],
  "error": "..."   // solo si falla
}
```

**Notas**:
- Tablas, medidas y relaciones se extraen via regex sobre los `.tmdl`. Soporta formato "flat" (todo en raiz) y "split" (carpeta `tables/`).
- Tables con nombres `DateTableTemplate_*`, `LocalDateTable_*` o con `isDateTable: true` se marcan con `is_date_table: true`.

### `validate_rules(model: dict) -> dict`

Aplica las reglas automaticas del PDF de buenas practicas al modelo extraido.

**Cuando usarla**: tercera tool, despues de `read_pbip`. Te da hallazgos concretos + las reglas que requieren tu criterio.

**Parametros**:
- `model`: el dict que devolvio `read_pbip`.

**Respuesta**:

```json
{
  "findings": [
    {"rule_id": "PBICHK-001", "title": "...", "category": "modelo_datos",
     "severity": "alta", "status": "pass|warning|fail|skipped", "evidence": "..."},
    ...
  ],
  "pending_llm_review": [
    {"rule_id": "PBICHK-007", "title": "...", "category": "...",
     "severity": "media", "reason": "..."},
    ...
  ]
}
```

**Que hacer con cada parte**:
- `findings`: ya estan evaluados. Resumilos al usuario.
- `pending_llm_review`: **vos** (el LLM) tenes que evaluarlos. Mira el modelo, mira el titulo/descripcion de cada regla, y para cada uno decidis: `pass`, `warning` o `fail`. Anade tus veredictos al resumen final.

### `generate_design(model: dict, report_goal: str | None = None) -> dict`

Genera un `theme.json` + layout propuesto para el reporte.

**Cuando usarla**: solo si pidio diseno. Si falta contexto, devuelve `missing_info` y pregunta al usuario.

**Parametros**:
- `model`: el dict que devolvio `read_pbip`.
- `report_goal`: objetivo del reporte en lenguaje natural (ej. "ventas por region", "indicadores prime vs no prime"). Si es `null` o vacio, devuelve `missing_info: "report_goal"`.

**Respuesta** (con goal):

```json
{
  "theme": {"name": "...", "dataColors": ["#...", ...], "background": "#...", ...},
  "layout": [
    {"name": "Resumen Ejecutivo", "visuals": [{"type": "card", "title": "...", "dataBinding": {...}}, ...]},
    {"name": "Analisis Detallado", "visuals": [...]}
  ],
  "notes": ["..."]
}
```

**Respuesta** (sin goal):

```json
{"missing_info": "report_goal", "message": "Falta el objetivo del reporte. Pregunta al usuario..."}
```

---

## Resources disponibles

Resources son **read-only**: el servidor los expone, el cliente (vos) los pide cuando necesita contexto. Pedilos al arrancar una conversacion, no en cada mensaje.

### `rules://best-practices`

Devuelve `rules.json` completo con las reglas compiladas del documento de buenas practicas (actualmente 31 reglas del PDF del checklist).

**Cuando pedirlo**: al inicio de la sesion, antes de invocar `validate_rules`. Te sirve para saber que reglas existen y dar contexto al LLM cuando evalues `pending_llm_review`.

### `power-bi://reference`

Devuelve el skill canonico de Power BI: estructura PBIP/PBIR/TMDL, cuando convertir desde PBIX, catalogo de skills externos, checklist rapido.

**Cuando pedirlo**: si el usuario trabaja con `.pbip` o `.tmdl` y necesitas entender mejor la estructura del proyecto. Especialmente util si `read_pbip` devuelve tablas vacias (puede ser formato no estandar).

### `usage://getting-started`

**Este mismo doc.** Como invocar las tools, orden recomendado, manejo de errores. Pedilo al inicio de la sesion si es la primera vez que usas este server.

**Cuando pedirlo**: una vez, al principio. Despues ya lo tenes en el contexto de la conversacion.

---

## Flujo recomendado para una auditoria

Cuando el usuario dice "audita este modelo" / "que no cumple" / "pasame los hallazgos":

```
1.  detectar:
    Pedir rules://best-practices (si no lo tenes ya).
    Pedir power-bi://reference si vas a necesitar entender TMDL no estandar.

2.  Preguntar al usuario la ruta del proyecto .pbip si no la dio.
    Si dijo "este modelo" sin ruta especifica, pedirsela.

3.  Llamar detect_format(path).
    - Si format == "pbix": avisar al usuario que convierta primero.
      Esperar a que confirme la conversion. No continuar.
    - Si format == "missing" o "unknown": pedir una ruta valida.
    - Si format == "pbip" y ok: continuar.

4.  Llamar read_pbip(semantic_model, report) usando las rutas de detect_format.
    - Si devuelve "error": el modelo TMDL puede ser no estandar.
      Pedir power-bi://reference si no lo pediste, y avisar al usuario.
    - Si devuelve tablas/measures/relaciones: continuar.

5.  Llamar validate_rules(model).
    - Iterar findings[] y resumir al usuario por categoria/severity.
    - Iterar pending_llm_review[] y evaluarvos mismo cada uno contra el modelo.
      Para cada regla pendiente:
        - Mira el titulo/descripcion.
        - Mira el modelo (tablas, medidas, relaciones, paginas).
        - Decide: pass / warning / fail.
        - Anade al resumen.

6.  Resumen final al usuario:
    - N findings automaticos (cuantos pass, warning, fail).
    - M reglas evaluadas por ti mismo (cuantas pass, warning, fail).
    - Lista priorizada de issues (ordenados por severity).
    - Recomendaciones concretas.
```

## Flujo recomendado para generar un diseno

Cuando el usuario dice "disename un reporte" / "que layout recomendarias":

```
1.  Si no hiciste auditoria previa, seguir los pasos 1-4 del flujo de auditoria
    (necesitas el modelo).

2.  Llamar generate_design(model, report_goal).
    - Si devuelve missing_info == "report_goal": preguntar al usuario el objetivo.
      Ejemplos utiles: "ventas por region", "indicadores prime vs no prime",
      "inventario por almacen", "headcount por area".
      Volver a llamar generate_design con el goal.

3.  Con la respuesta:
    - theme: paleta de colores corporativa + tipografia + semantica.
      Sugerir importar a Power BI Desktop via Vista > Temas > Buscar tema.
    - layout: 2 paginas por defecto (Resumen Ejecutivo + Analisis Detallado).
      Cada pagina tiene una lista de visuales sugeridos.
      Decirle al usuario que es una sugerencia; puede ajustarla.

4.  Si el usuario quiere iterar, llamar generate_design de nuevo con otro goal
    o pedir mas detalle.
```

---

## Flujo recomendado ante un Mockup, Wireframe o Boceto de Dashboard

Cuando el usuario comparte una **imagen, captura de pantalla, boceto o descripción detallada de un Mockup/Wireframe**:

```
1.  DECONSTRUCCIÓN VISUAL DEL MOCKUP:
    - Identificar las páginas/pestañas requeridas.
    - Desglosar las 4 franjas modulares de la grilla:
      * Franja 1 (Superior): Header, títulos, segmentadores (slicers) y filtros globales.
      * Franja 2: Tarjetas de KPI principales (Totales, variaciones YoY/MoM, estado).
      * Franja 3: Gráficos centrales (tendencias temporales, rankings de barras, comparativas).
      * Franja 4: Tablas de auditoría, matrices detalladas o visuales secundarios.
    - Mapear la jerarquía visual de lectura (patrón Z o F).

2.  CONTRASTE CON EL MODELO SEMÁNTICO EXISTENTE:
    - Invocar read_pbip para inspeccionar tablas, columnas y medidas DAX disponibles.
    - Comparar cada elemento del mockup contra los metadatos reales del modelo.

3.  GENERACIÓN DEL PLAN DE IMPLEMENTACIÓN ESTRUCTURADO:
    Presentar al usuario un plan de trabajo claro con:
    - Lista de páginas PBIR a crear/actualizar (`definition/pages/`).
    - Matriz de visuales por página con coordenadas aproximadas en la grilla.
    - Inventario de medidas DAX necesarias:
      * Medidas existentes que se reutilizan.
      * Medidas nuevas que deben crearse con `write_dax_measure`.
    - Tema corporativo y estilos (`theme.json` / paleta de colores).

4.  AUDITORÍA DE DISCREPANCIAS E INCONSISTENCIAS (MOCKUP AUDIT):
    Identificar de forma proactiva cualquier discrepancia en 3 categorías:
    - [Discrepancia de Datos]: Medidas, columnas o agrupaciones presentes en el mockup
      que NO existen en el modelo semántico o tienen nombres diferentes.
    - [Discrepancia de Relaciones/Filtros]: Segmentadores o cortes de datos en el mockup
      que requieren relaciones inexistentes o direcciones de filtrado cruzado incompatibles.
    - [Discrepancia de UX / Mejores Prácticas]: Gráficos no recomendados (ej. gráfico de torta
      con más de 5 porciones, tarjetas sin contexto de variación, contraste insuficiente de color).

5.  CONSULTA PROACTIVA DE DISCREPANCIAS AL USUARIO:
    Antes de proceder a escribir código o archivos PBIR:
    - Listar las discrepancias encontradas de forma concisa y numerada.
    - Para cada discrepancia, proponer una solución recomendada concreta (ej. "La medida 'Margen Bruto' no existe: ¿deseas que la creemos usando `[Total Ventas] - [Costo Total]`?").
    - Solicitar confirmación/aprobación del usuario para proceder.

6.  CONSTRUCCIÓN Y ESCRITURA TRAS APROBACIÓN:
    - Crear las medidas DAX acordadas con `write_dax_measure`.
    - Escribir la estructura PBIR de páginas y visuales con `write_pbir_layout`.
    - Validar las reglas con `validate_rules`.
```

## Cuando pedir contexto al usuario

Pedile al usuario cuando:

| Situacion | Que preguntar |
|---|---|
| No diste ruta del proyecto | "Cual es la ruta del .pbip?" o "Donde esta guardado el proyecto?" |
| `detect_format` devolvio pbix | "Converti el archivo a .pbip desde Power BI Desktop (Archivo > Guardar como > Power BI Project) y avisame cuando este listo." |
| `generate_design` devuelve `missing_info: report_goal` | "Que tipo de reporte queres? (ej. ventas por region, indicadores prime, headcount por area, etc.)" |
| `read_pbip` devolvio 0 tablas/measures | "El modelo TMDL parece no estandar. Podes verificar que las tablas estan en `definition/tables/*.tmdl`?" |
| Pediste `rules://best-practices` y hay reglas con `check_type: llm` que requieren criterio | El LLM (vos) las evalua, no le preguntes al usuario salvo que falte info especifica |

## Errores comunes y como manejarlos

| Error | Causa probable | Que hacer |
|---|---|---|
| `detect_format` devuelve `format: "pbix"` | El archivo es .pbix, no .pbip | Pedir conversion. NO continuar. |
| `detect_format` devuelve `missing` | path inexistente | Verificar la ruta con el usuario. |
| `read_pbip` devuelve `{"error": "..."}` | SemanticModel o Report no existen en la ruta | Verificar la estructura del proyecto. |
| `read_pbip` devuelve 0 tablas | TMDL no estandar o vacio | Pedir `power-bi://reference`. Avisar al usuario. |
| `validate_rules` solo tiene `status: "skipped"` | Ninguna regla automatica matchea el modelo | Es valido. Solo evaluar `pending_llm_review` vos mismo. |
| `generate_design` devuelve `missing_info` | Falta `report_goal` | Preguntar al usuario. |
| Tool devuelve `{"error": "..."}` generico | Cualquier fallo del server | Reportar el mensaje al usuario y pedir info adicional. |

## Notas finales

- **Idempotencia**: podes llamar las tools multiples veces sin miedo. No modifican archivos del usuario.
- **No hay cache**: cada llamada lee el `.pbip` desde disco. Cambios en el modelo se ven al instante.
- **Orden importa**: `read_pbip` consume la salida de `detect_format`. `validate_rules` consume la salida de `read_pbip`. `generate_design` consume la salida de `read_pbip`. Encadena.
- **Performance**: `read_pbip` parsea todos los `.tmdl` (puede tardar 1-3 segundos en modelos grandes). El resto es instantaneo.
- **Determinismo**: las tools son deterministas. Mismo input = misma salida. Esto ayuda a reproducibilidad.