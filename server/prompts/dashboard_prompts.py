from __future__ import annotations


def register(mcp) -> None:
    @mcp.prompt(
        name="audit_powerbi_report",
        description="Guia interactiva para auditar un proyecto Power BI (.pbip) contra las 36 reglas y generar reporte estructurado.",
    )
    def audit_powerbi_report(pbip_path: str) -> str:
        """Prompt para auditar un proyecto PBIP."""
        return f"""Por favor audita el proyecto Power BI PBIP ubicado en:
{pbip_path}

Sigue este procedimiento en orden:
1. Llama a la herramienta detect_format con la ruta '{pbip_path}' para validar que sea un proyecto .pbip valido.
2. Llama a read_pbip para extraer la definicion del modelo semantico (TMDL) y del reporte (PBIR).
3. Llama a validate_rules pasando el modelo y los visuales leidos para evaluar las 36 reglas de buenas practicas.
4. Genera un informe estructurado agrupando los hallazgos por:
   - Severidad (alta, media, baja)
   - Categoria (modelo, medidas, visuales, nomenclatura, rendimiento, accesibilidad)
5. Para cada hallazgo critico, propon una accion correctiva concreta usando las herramientas fix_dax, write_dax_measure o write_tmdl_relationship.
"""

    @mcp.prompt(
        name="design_powerbi_dashboard",
        description="Flujo guiado para estructurar paginas, KPIs y grilla 1280x720 para un dashboard Power BI.",
    )
    def design_powerbi_dashboard(
        pbip_path: str,
        goal: str,
        target_audience: str = "Ejecutiva",
    ) -> str:
        """Prompt para concebir y disenar un dashboard Power BI."""
        return f"""Disena un dashboard Power BI para el proyecto:
Ruta: {pbip_path}
Objetivo de negocio: {goal}
Audiencia objetivo: {target_audience}

Sigue estos pasos:
1. Llama a read_pbip para conocer las tablas, medidas y relaciones disponibles en el modelo.
2. Consulta el recurso power-bi://grid-layout para seguir la convencion del proyecto (grilla modular que se adecua a los visuales, sin limite rigido de 1280x720, adaptando la altura segun las filas necesarias).
3. Llama a generate_design con el objetivo '{goal}' para obtener la paleta corporativa y sugerencia de visuales.
4. Si la audiencia requiere tarjetas avanzadas o KPIs visuales estilizados, consulta html-content://reference para disenar tarjetas con HTML Content.
5. Presenta la propuesta de layout al usuario y, una vez aprobada, utiliza write_pbir_layout para escribir los archivos page.json y visual.json.
"""

    @mcp.prompt(
        name="optimize_dax_expression",
        description="Audita y refactoriza una expresion DAX aplicando buenas practicas (DIVIDE, VAR/RETURN, optimizacion de filtros).",
    )
    def optimize_dax_expression(dax_code: str) -> str:
        """Prompt para optimizar y refactorizar DAX."""
        return f"""Audita y refactoriza la siguiente expresion DAX:

```dax
{dax_code}
```

Sigue estos pasos:
1. Invoca la herramienta fix_dax pasando el codigo DAX anterior.
2. Revisa las advertencias y transformaciones aplicadas (reemplazo de division directa por DIVIDE, estructuracion con variables VAR/RETURN, advertencias sobre CALCULATE con FILTER).
3. Explica detalladamente el motivo de cada optimizacion tanto a nivel de rendimiento como de legibilidad.
4. Muestra la formula optimizada final lista para ser agregada al modelo con write_dax_measure.
"""

    @mcp.prompt(
        name="create_pbir_page",
        description="Flujo guiado para crear una nueva pagina PBIR con visuales posicionados automaticamente en la grilla.",
    )
    def create_pbir_page(pbip_path: str, page_display_name: str) -> str:
        """Prompt para crear una pagina PBIR posicionada en grilla."""
        return f"""Crea una nueva pagina PBIR en el proyecto:
Ruta PBIP: {pbip_path}
Nombre de pagina: {page_display_name}

Pasos:
1. Revisa las tablas y medidas disponibles con read_pbip.
2. Define la lista de visuales a incluir segun el arquetipo (slicers arriba, KPIs debajo, graficos al medio, detalle abajo).
3. Llama a write_pbir_layout pasando pbip_path, page_display_name y la lista de especificaciones de visuales.
4. Confirma los archivos generados en definition/pages/.
"""

    @mcp.prompt(
        name="plan_dashboard_from_mockup",
        description="Guia interactiva para analizar un Mockup/Wireframe, generar el Plan de Implementacion PBIP y consultar discrepancias antes de construir.",
    )
    def plan_dashboard_from_mockup(
        mockup_description: str,
        pbip_path: str = "",
        target_audience: str = "Ejecutiva",
    ) -> str:
        """Prompt para deconstruir mockups, auditar discrepancias y planificar la construccion PBIP."""
        path_instruction = f"Ruta del proyecto PBIP: {pbip_path}" if pbip_path else "Pide al usuario la ruta del proyecto .pbip si aun no fue provista."
        return f"""Procesa el siguiente Mockup / Wireframe para disenar y planificar la construccion del dashboard en Power BI:

DESCRIPCION DEL MOCKUP / WIREFRAME:
{mockup_description}

AUDIENCIA OBJETIVO: {target_audience}
{path_instruction}

SIGUE ESTE PROCEDIMIENTO ESTRICTO:
1. INSPECCION DEL MODELO SEMANTICO:
   - Si se indico la ruta PBIP, ejecuta detect_format y read_pbip para conocer las tablas, columnas, relaciones y medidas DAX existentes.

2. DECONSTRUCCION DEL MOCKUP:
   - Identifica las paginas/vistas necesarias.
   - Desglosa los visuales en las 4 franjas de la grilla modular (Header/Filtros, KPIs, Graficos Centrales, Tablas de detalle).
   - Identifica la paleta de colores y estilo corporativo requerido.

3. GENERACION DEL PLAN DE IMPLEMENTACION:
   - Presenta un plan estructurado indicando:
     * Paginas PBIR a crear o modificar.
     * Lista de visuales por pagina con su tipo y ubicacion en grilla.
     * Inventario de medidas DAX a reutilizar y nuevas medidas a crear con write_dax_measure.

4. AUDITORIA DE DISCREPANCIAS (MOCKUP AUDIT):
   - Revisa activamente e identifica discrepancias en 3 categorias:
     * [Discrepancia de Datos]: Medidas o dimensiones del mockup que no existen en el modelo semantico o difieren en calculo.
     * [Discrepancia de Relaciones/Filtros]: Segmentadores que podrian romper el filtrado o requerir cambios en el modelo estrella.
     * [Discrepancia de Usabilidad]: Anti-patrones de visualizacion (tortas con muchas porciones, falta de contexto en KPIs, problemas de contraste).

5. CONSULTA OBLIGATORIA DE DISCREPANCIAS AL USUARIO:
   - Antes de escribir archivos PBIR o DAX, formula una lista clara y numerada de preguntas sobre las discrepancias encontradas, proponiendo una solucion recomendada para cada una.
   - Espera la confirmacion y decision del usuario para proceder a la construccion con write_dax_measure y write_pbir_layout.
"""

