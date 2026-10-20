---
name: power-bi-pbip
description: Auditar, editar, crear y modificar proyectos Power BI en formato PBIP/PBIR/TMDL segun las 36 reglas compiladas en este proyecto, y disenar HTML embebido en el visual custom "HTML Content" de coacervo. Activar cuando el usuario pida auditar, validar, corregir, crear, modificar un modelo o reporte Power BI (.pbip, .tmdl, .pbir), o disenar HTML/CSS para tarjetas/KPIs/badges en Power BI. Para tareas avanzadas de authoring (planning exhaustivo, design system, deploy a Fabric), consultar los skills complementarios powerbi-report-planning, powerbi-report-design, powerbi-report-authoring, powerbi-report-management, semantic-model-authoring.
---

# Power BI (PBIP/PBIR/TMDL) — Skill local unificado

## 0. Proposito

Este proyecto es un **auditor, editor y diseniador basado en reglas**: lee un
modelo Power BI existente, lo compara contra las 36 reglas compiladas en
`rules.json`, y aplica correcciones o crea archivos nuevos segun los findings.
Tambien genera HTML embebido para el visual custom "HTML Content" (coacervo),
respetando las reglas de auditoria del proyecto.

NO cubre authoring exhaustivo — eso lo hacen los 5 skills oficiales de Microsoft
listados al final.

## 1. Regla de oro

Toda accion sobre un modelo o reporte Power BI debe justificarse contra al
menos una de las **36 reglas** de `rules.json` o contra las **reglas de
diseno HTML** del visual custom. Las dos areas estan acopladas: cuando se
audita un visual HTML se usan ambas reglas; cuando se disena HTML se valida
contra las reglas visuales del proyecto.

## 2. Tools disponibles (MCP server `powerbi-mcp`)

| Tool | Para que |
|---|---|
| `check_pbi_desktop_status(path)` | Detecta si Desktop está abierto, reportes activos y advierte sobre pisar disco |
| `query_dax(query, path, port)` | Consultar datos en vivo en el motor VertiPaq local (rango de fechas, distincts, medidas) |
| `disable_auto_date_time(path)` | Desactivar Auto Date/Time en model.tmdl para prevenir crashes de DateTableSubsystem |
| `verify_and_fix_pbip_encoding(path)` | Verificar y limpiar archivos TMDL/JSON a UTF-8 sin BOM |
| `read_pbip(path)` | Inspeccionar tablas, columnas, particiones, medidas, relaciones, paginas |
| `validate_rules(model)` | Correr las 36 reglas; devuelve findings con severidad |
| `generate_pbip_docx(...)` | Generar informe tecnico Word (.docx) completo con origenes, SQL/M, DAX y diccionario |
| `write_tmdl_relationship(...)` | Crear/editar relaciones en TMDL con sintaxis oficial y sin corchetes |
| `write_dax_measure(...)` | Crear/editar medidas DAX respetando estructura TMDL antes de particiones |
| `write_pbir_layout(...)` | Generar pages/visuals JSON (incluye HTML Content) |
| `generate_design(...)` | Generar theme.json + layout propuesto |
| `fix_dax(...)` | Refactorizar y auditar DAX problematico |
| `detect_format(path)` | Detecta `.pbix` vs `.pbip` |

Recursos adicionales via MCP (`server/resources/power_bi_reference.py`):
- `power-bi://reference` — el contenido completo de este skill
- `power-bi://rules/summary` — tabla compacta de las 36 reglas
- `power-bi://grid-layout` — grilla 1280x720 del proyecto
- `power-bi://anti-patterns-compact` — top 10 anti-patterns
- `power-bi://skill/{name}` — sirve un skill por nombre (local o Microsoft)

## 3. Skills complementarios (Microsoft, PRIMARIO)

Descargados via `uv run scripts/run.py setup-microsoft`. Carga automaticamente.

| Tarea | Skill Microsoft |
|---|---|
| Crear reporte end-to-end con aprobacion humana | `powerbi-report-planning` |
| Disenar tono, archetype, layout, color | `powerbi-report-design` |
| Escribir PBIR pages/visuals/filters/themes | `powerbi-report-authoring` |
| Publicar a Fabric workspace via REST | `powerbi-report-management` |
| TMDL/DAX/Direct Lake/AI readiness | `semantic-model-authoring` |

Este skill NO duplica su contenido. Los delega.

## 4. Flujo A — Audit / Edit / Create (PBIP/PBIR/TMDL)

### Pasos

1. **Inspeccionar** el modelo con `read_pbip` para entender la estructura actual.
2. **Auditar** con `validate_rules`. Devuelve findings con severidad alta/media/baja.
3. **Presentar** los findings al usuario agrupados por severidad. Pedir aprobacion
   antes de aplicar cambios destructivos (sobreescritura, borrado).
4. **Aplicar fixes** con los tools `write_*` segun los findings aprobados.
5. **Re-validar** con `validate_rules` para confirmar que el modelo cumple.

### Convenciones del proyecto

- **Grilla canvas 1280x720** con 4 franjas verticales: header/filtros,
  KPIs (cards), graficos principales, detalle (tabla/matrix).
- **Severidad**: `alta` (bloqueante), `media` (mejorable), `baja` (cosmetico).
- **Categorias**: 7 tipos (`modelo_datos`, `medidas_dax`, `reporte_visual`,
  `rendimiento`, `nomenclatura`, `seguridad`, `documentacion`).
- **Relaciones**: prefer 1:N single-direction; evitar bidirectional.
- **FK visibles**: ocultar columnas FK (regla de oro de Power BI modeling).
- **Nomenclatura TMDL**: prefijos `Fact*` / `Dim*` son bienvenidos.
- **Medidas DAX**: siempre con `formatString`, `displayFolder`, `description`.
- **Recursos**: ver `power_bi_reference.py` para los MCP resources asociados.

### Generacion de Documentacion Tecnica Word (.docx)

Usa la herramienta `generate_pbip_docx` para compilar un documento Microsoft Word integral:
1. **Orígenes de Datos y Linaje**: Matriz de conectores, host/base de datos, consultas SQL nativas (`Value.NativeQuery`) y código M / DAX de cada partición.
2. **Diccionario de Datos**: Columnas, tipos de datos (`dataType`), formatos y carpetas.
3. **Catálogo de Medidas DAX**: Fórmulas formateadas en cajas de código sombreadas y display folders.
4. **Relaciones, RLS y PBIR**: Cardinalidad, filtros de seguridad por roles y páginas/visuales.
5. **Auditoría de Buenas Prácticas**: Diagnóstico de hallazgos automáticos evaluados contra las 36 reglas.

### Flujo C — Procesamiento de Mockups, Generación de Plan y Resolución de Discrepancias

Cuando el usuario provea una imagen, captura, wireframe o boceto visual de un dashboard:
1. **Deconstrucción Visual**: Identificar páginas requeridas, 4 franjas modulares de grilla, tarjetas de KPI, tipos de gráficos y segmentadores.
2. **Cotejo con Modelo**: Correr `read_pbip` para validar si las tablas, columnas y medidas DAX solicitadas existen en el modelo.
3. **Plan de Implementación**: Generar un plan detallado con las páginas a crear, coordenadas en grilla modular, medidas existentes a reutilizar y nuevas medidas DAX a escribir.
4. **Auditoría y Preguntas de Discrepancia (Mockup Audit)**:
   - Identificar discrepancias de datos (medidas ausentes), de relaciones (filtros no soportados) y de usabilidad (anti-patrones visuales o problemas de contraste).
   - **Formular preguntas claras y numeradas al usuario** proponiendo soluciones recomendadas para resolver cada discrepancia antes de escribir archivos PBIR o DAX.

### Comunicacion con Flujo B (HTML)

Cuando `read_pbip` reporte un visual `htmlContent443BE3AD55E043BF878BED274D3A6865`
(identificador del visual HTML Content), aplicar **ademas** las reglas del
Flujo B (seccion 5). En particular:
- Verificar que el HTML generado por la medida cumple las reglas de sanitizacion.
- Verificar que no usa `card`/`table`/`matrix` legacy cuando deberia ser `cardVisual`/`tableEx`/`pivotTable`.
- Validar que las medidas que producen HTML usan `DIVIDE()` y `FORMAT()`.

## 5. Flujo B — Diseno HTML Content (visual custom coacervo)

### 5.1 Que es y cuando usarlo

El visual **HTML Content** (coacervo / Daniel Marsh-Patrick) renderiza como HTML
el valor de texto devuelto por una medida DAX o columna. Dos ediciones:

| Edicion | Certificacion AppSource | Exportar PDF/PPT | Tags permitidos | Recursos externos |
|---|---|---|---|---|
| **HTML Content (lite)** | Si | Si | Subconjunto sanitizado | No |
| **HTML Content (full/regular)** | No | No | Casi todo | Si |

**Regla de oro**: si el usuario no especifica edicion, disenar para **lite**.
Si requiere imagenes remotas o fuentes web, avisar que se necesita **full** (pierde
certificacion/exportacion).

### 5.2 Ciclo de ejecucion

```
[Fase 1: Rol de datos] -> [Fase 2: Plantilla HTML] -> [Fase 3: CSS inline] -> [Fase 4: DAX ensamblado] -> [Fase 5: Sanitizacion]
```

1. **Rol de datos**: columna (fila por valor) o medida (un contexto, usar rol **Granularity**).
2. **Plantilla HTML**: solo tags de la lista blanca (seccion 5.3).
3. **CSS inline**: `style=""` o `<style>` embebido, solo propiedades permitidas.
4. **Ensamblado DAX**: concatenar literales con `FORMAT()`, `SELECTEDVALUE()`, `DIVIDE()`.
5. **Sanitizacion**: revisar checklist 5.6 antes de entregar.

### 5.3 Tags HTML permitidos (lite)

**Permitidos**: `a`, `address`, `article`, `aside`, `b`, `base`, `bdi`, `bdo`,
`blockquote`, `br`, `caption`, `cite`, `code`, `col`, `colgroup`, `data`, `dd`,
`del`, `details`, `dfn`, `div`, `dl`, `dt`, `em`, `figcaption`, `figure`, `footer`,
`header`, `hgroup`, `hr`, `h1`-`h6`, `i`, `img`, `ins`, `kbd`, `li`, `main`, `mark`,
`meter`, `nav`, `ol`, `output`, `p`, `pre`, `progress`, `q`, `rb`, `rp`, `rt`, `rtc`,
`ruby`, `s`, `samp`, `search`, `section`, `small`, `span`, `strong`, `sub`, `summary`,
`sup`, `table`, `tbody`, `td`, `tfoot`, `th`, `thead`, `time`, `tr`, `u`, `ul`, `var`,
`wbr`. SVG completo excepto `use`, `script`, `foreignObject`. SMIL permitido
salvo `attributeName` apuntando a `style` o IRI/URL.

**Bloqueados** (eliminan el elemento): `script`, `iframe`, `object`, `embed`,
`link`, `meta`, `form`.

**Atributos globales permitidos**: `class`, `id`, `title`, `lang`, `dir`, `style`,
`role`, `tabindex`, `aria-*`, `data-*`.

**Atributos prohibidos** (eliminan el elemento): cualquier `on*`, `srcdoc`,
`formaction`, `action`, `ping`, `background`, `poster`, `srcset`.

**URLs**: `a[href]` admite `https://`/`http://`. `img[src]` solo `data:image/*;base64,...`.
NO usar imagenes remotas (no carga en lite).

### 5.4 CSS permitido (lite)

Permitido en `style=""` o `<style>`: `color`, `background-color`, `font-family`
(solo fuentes del sistema), `font-size`, `font-weight`, `text-align`, `line-height`,
`opacity`, `transform`, `border`, `border-radius`, `padding`, `margin`, `display`,
`flex*`, `grid*`, `width`, `height`, `fill`, `stroke`. At-rules: `@media`,
`@supports`, `@keyframes`, `@page`.

Bloqueado: `url()` con dominios externos, `@import`, `@font-face`, `expression()`,
`attr()`, at-rules no listadas.

### 5.5 Patron DAX de ensamblado

```dax
KPI Card Venta Bruta =
VAR _Valor = FORMAT ( SUM ( Ventas[Monto] ), "$#,##0" )
VAR _Delta = DIVIDE ( [VentaActual] - [VentaAnterior], [VentaAnterior], 0 )
VAR _ColorDelta = IF ( _Delta >= 0, "#16a34a", "#dc2626" )
RETURN
    "<div style='background:#f0e5ff;border-radius:12px;padding:20px;text-align:center;font-family:-apple-system,Segoe UI,Arial,sans-serif;'>" &
        "<div style='font-size:12px;color:#666;'>Venta Bruta</div>" &
        "<div style='font-size:24px;font-weight:700;color:#000;'>" & _Valor & "</div>" &
        "<div style='font-size:12px;color:" & _ColorDelta & ";'>" & FORMAT ( _Delta, "0.0%" ) & "</div>" &
    "</div>"
```

Reglas DAX aplicables (tambien valen para cualquier medida del proyecto):
- `DIVIDE()` en vez de `/` para evitar errores de division.
- `VAR/RETURN`: calcular valores primero, concatenar al final.
- `FORMAT()` para todo numero que entre al HTML como texto.

**Clave del rol Values en `visual.json` (PBIR)**: la clave interna de
`query.queryState` para el rol **Values** del HTML Content es `content` (no
`values` ni `Values`). Sintoma si se usa mal: el visual muestra el placeholder
"Thanks very much for using this" en vez del HTML.

### 5.6 Checklist de sanitizacion (entrega)

- [ ] Ningun tag fuera de la lista blanca (seccion 5.3).
- [ ] Ningun atributo `on*` presente.
- [ ] Todas las imagenes son `data:image/...;base64,...` o SVG inline.
- [ ] Ningun `@import`/`@font-face` — solo fuentes del sistema.
- [ ] Todo `href` usa `http(s)://`; documentar requisito del toggle "Allow opening URLs".
- [ ] Cifras visibles pasan por `FORMAT()`.
- [ ] Si se necesitan multiples filas desde una medida, el rol **Granularity** esta poblado o se usa `CONCATENATEX`.
- [ ] Probado con caracteres especiales (`&`, `<`, `>`, comillas) — escapar con `SUBSTITUTE()`.
- [ ] Si requiere fuentes web o imagenes remotas, avisar al usuario que necesita edicion **full**.

### 5.7 Comunicacion con Flujo A (audit)

Al disenar HTML, validar contra las 36 reglas del proyecto:

| Regla del proyecto (resumen) | Verificacion HTML |
|---|---|
| Severidad alta: visuales con `card` legacy | Reemplazar por HTML card bien estilizado si el reporte lo requiere |
| Severidad media: medir `n` tablas | El HTML Content no cuenta como `cardVisual` nativo — sigue contando como 1 visual |
| Severidad alta: medidas sin `formatString`/`displayFolder`/`description` | Las medidas que producen HTML tambien requieren los 3 metadatos |
| Severidad alta: visuales con `table` legacy | Reemplazar por `table` HTML estilizado (CSS inline) si el reporte lo requiere |
| Severidad alta: visuales con `matrix` legacy | Reemplazar por `table` HTML con jerarquia CSS si el reporte lo requiere |
| Severidad media: max 1 medida por visual | El HTML Content admite 1 medida (o columna) + Granularity. OK. |
| Severidad baja: inconsistencias de color | El HTML define sus propios colores via CSS — verificar coherencia con `theme.json` |

Reglas especificas para HTML Content (extienden las 36 reglas):

| Regla HTML | Severidad | Deteccion |
|---|---|---|
| Tag `script`/`iframe`/`form` presente | **alta** (visual no renderiza) | Buscar regex en la medida DAX |
| Atributo `on*` presente | **alta** (XSS bloqueado) | Buscar regex |
| `img src` con URL remota (no data:) | **alta** (lite no carga) | Buscar regex |
| `@font-face`/`@import` presente | **media** (no carga) | Buscar regex |
| Sin `DIVIDE()` en deltas/porcentajes | **media** (puede fallar con div/0) | Revisar DAX |
| Sin `FORMAT()` en cifras | **baja** (UX) | Revisar DAX |

## 6. Anti-patterns top del proyecto (consolidado)

| # | Categoria | Mal | Bien |
|---|---|---|---|
| 1 | DAX | `A / B` sin proteccion | `DIVIDE(A, B, 0)` |
| 2 | DAX | `FILTER(T, T[col]=x)` | filtro directo o `REMOVEFILTERS` |
| 3 | DAX | medida sin metadatos | `formatString`, `displayFolder`, `description` |
| 4 | Modelo | relacion bidirectional | single-direction |
| 5 | Modelo | FK visible | ocultar (`isHidden = true`) |
| 6 | Modelo | nombre crudo `customer_id` | nomenclatura legible |
| 7 | Visual nativo | `card` legacy | `cardVisual` |
| 8 | Visual nativo | `table` legacy | `tableEx` |
| 9 | Visual nativo | `matrix` legacy | `pivotTable` |
| 10 | Visual nativo | `map` legacy | `azureMap` |
| 11 | HTML Content | tag `script`/`iframe`/`form` | quitar o usar visual nativo |
| 12 | HTML Content | atributo `on*` | quitar (visual elimina el elemento) |
| 13 | HTML Content | `img src` con URL remota | usar `data:image/...;base64,...` |
| 14 | HTML Content | `@font-face`/`@import` | fuentes del sistema |
| 15 | HTML Content | sin `DIVIDE()` en delta | `DIVIDE([Actual] - [Anterior], [Anterior], 0)` |

## 7. Checklist final

- [ ] ¿Todas las medidas tienen `formatString`, `displayFolder`, `description`?
- [ ] ¿El modelo no tiene relaciones bidireccionales injustificadas?
- [ ] ¿Las columnas FK estan ocultas?
- [ ] ¿Los visuales nativos usan tipos modernos (no `card`/`table`/`matrix` legacy)?
- [ ] Si hay HTML Content, ¿la medida pasa el checklist 5.6 (sanitizacion)?
- [ ] Si hay HTML Content, ¿la clave `content` en `queryState` es correcta?
- [ ] ¿`validate_rules` reporta 0 errores de severidad alta?

## 8. Regla de interaccion (este skill vs Microsoft)

- **Este skill (auditar/editar/crear + diseno HTML)**: lo unico del proyecto.
- **Microsoft skills (PRIMARIO para authoring exhaustivo)**: planning,
  design system, mecanica PBIR, deploy a Fabric, modelado DAX avanzado.

Cuando el usuario pida algo, decidir:
1. ¿Lo cubre este skill (audit/edit/create local o HTML Content)? -> Hacerlo aca.
2. ¿NO lo cubre (planning, design system, deploy, modelado DAX exhaustivo)?
   -> Invocar el skill Microsoft correspondiente.
3. ¿El cliente no carga skills nativas? -> Usar el MCP resource `power-bi://skill/{name}` via el server `powerbi-mcp`.
