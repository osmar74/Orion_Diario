from pathlib import Path


SERVICE = Path("app/services/gestion_consolidada_service.py")
RENDERER = Path("app/services/gestion_consolidada_renderer_service.py")
BLUEPRINT = Path("app/controllers/gestion_consolidada_blueprint.py")
TEMPLATE = Path("app/templates/gestion_consolidada.html")
JS = Path("app/static/js/gestion_consolidada.js")
CSS = Path("app/static/css/deepblack.css")
AUDIT = Path("tools/audit_gestion_consolidada.py")


# ============================================================
# 1) Service: Fase I carga SQL
# ============================================================

service = SERVICE.read_text(encoding="utf-8")

if "def cargar_informacion_gestion_sql(" not in service:
    service += r'''


def _connection_string_vencorp(conexion: str) -> str:
    """
    Conexión SQL Server para carga final de Consolidar Gestión.

    Variables opcionales:
    - GESTION_SQL_DRIVER
    - GESTION_SQL_LOCAL_SERVER
    - GESTION_SQL_REMOTE_SERVER
    - GESTION_SQL_USER
    - GESTION_SQL_PASSWORD

    Si no hay usuario/clave, usa Trusted_Connection=yes.
    """
    conn = str(conexion or "local").lower()
    driver = os.getenv("GESTION_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    local_server = os.getenv("GESTION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV")
    remote_server = os.getenv("GESTION_SQL_REMOTE_SERVER", "VC-EIDER")

    server = remote_server if conn == "remoto" else local_server

    user = os.getenv("GESTION_SQL_USER") or os.getenv("SQLSERVER_USER")
    password = os.getenv("GESTION_SQL_PASSWORD") or os.getenv("SQLSERVER_PASSWORD")

    if user and password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            "DATABASE=Vencorp_V2;"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        "DATABASE=Vencorp_V2;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def _normalizar_valor_sql(value: Any) -> Any:
    try:
        import pandas as pd
        import numpy as np
    except Exception:
        pd = None
        np = None

    if value is None:
        return None

    if pd is not None:
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

        try:
            if isinstance(value, pd.Timestamp):
                return value.to_pydatetime()
        except Exception:
            pass

    if np is not None:
        try:
            if isinstance(value, np.generic):
                return value.item()
        except Exception:
            pass

    return value


def _columnas_insertables_sql(cursor: Any, schema: str, table: str) -> list[str]:
    query = """
    SELECT c.name
    FROM sys.columns c
    INNER JOIN sys.objects o ON c.object_id = o.object_id
    INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE s.name = ?
      AND o.name = ?
      AND o.type = 'U'
      AND c.is_identity = 0
      AND c.is_computed = 0
    ORDER BY c.column_id;
    """

    return [row[0] for row in cursor.execute(query, schema, table).fetchall()]


def _contar_registros_tabla_sql(cursor: Any, schema: str, table: str) -> int | None:
    try:
        row = cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]").fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return None


def cargar_informacion_gestion_sql(
    data_dir: str | Path,
    fecha_raw: str,
    conexion: str = "local",
) -> dict[str, Any]:
    """
    Fase I - Cargar información.

    Lee:
    - 05_final/YYYYMMDD_Gestion_excel.xlsx

    Inserta en:
    - Vencorp_V2.gestion.gestion_adminfo_onedrive

    Reporta:
    - filas leídas
    - filas insertadas
    - columnas insertadas
    - errores
    """
    try:
        import pandas as pd
    except Exception as exc:
        return {
            "ok": False,
            "error": f"No se pudo importar pandas: {exc}",
        }

    try:
        import pyodbc
    except Exception as exc:
        return {
            "ok": False,
            "error": f"No se pudo importar pyodbc: {exc}",
        }

    rutas = resolver_rutas(data_dir, fecha_raw)
    fecha = rutas["fecha"]
    conexion_normalizada = str(conexion or "local").lower()

    schema = "gestion"
    table = "gestion_adminfo_onedrive"
    database = "Vencorp_V2"

    ruta_excel = (
        Path(rutas["subcarpetas"]["05_final"])
        / f"{fecha}_Gestion_excel.xlsx"
    )

    if not ruta_excel.exists():
        return {
            "ok": False,
            "error": f"No existe archivo final. Ejecute primero Fase G: {ruta_excel}",
            "ruta_excel": str(ruta_excel),
            "conexion": conexion_normalizada,
            "database": database,
            "schema": schema,
            "table": table,
        }

    try:
        df = pd.read_excel(ruta_excel)
        df.columns = [str(col).strip() for col in df.columns]

        filas_leidas = len(df)

        if filas_leidas == 0:
            return {
                "ok": False,
                "error": "El archivo final no contiene filas para insertar.",
                "ruta_excel": str(ruta_excel),
                "conexion": conexion_normalizada,
                "database": database,
                "schema": schema,
                "table": table,
                "filas_leidas": 0,
            }

        conn_str = _connection_string_vencorp(conexion_normalizada)

        with pyodbc.connect(conn_str, timeout=30) as conn:
            cursor = conn.cursor()

            total_antes = _contar_registros_tabla_sql(cursor, schema, table)

            columnas_tabla = _columnas_insertables_sql(cursor, schema, table)

            if not columnas_tabla:
                raise ValueError(
                    f"No se encontraron columnas insertables para {database}.{schema}.{table}. "
                    "Verifique que la tabla exista y que el usuario tenga permisos."
                )

            columnas_excel = list(df.columns)

            columnas_insertar = [
                col for col in columnas_tabla
                if col in columnas_excel
            ]

            columnas_omitidas_excel = [
                col for col in columnas_excel
                if col not in columnas_insertar
            ]

            columnas_tabla_sin_excel = [
                col for col in columnas_tabla
                if col not in columnas_excel
            ]

            if not columnas_insertar:
                raise ValueError(
                    "No hay columnas comunes entre el Excel final y la tabla destino. "
                    f"Columnas Excel: {columnas_excel}. "
                    f"Columnas tabla: {columnas_tabla}."
                )

            placeholders = ", ".join(["?"] * len(columnas_insertar))
            columnas_sql = ", ".join(f"[{col}]" for col in columnas_insertar)

            insert_sql = (
                f"INSERT INTO [{schema}].[{table}] "
                f"({columnas_sql}) VALUES ({placeholders})"
            )

            rows = []

            for row in df[columnas_insertar].itertuples(index=False, name=None):
                rows.append(tuple(_normalizar_valor_sql(value) for value in row))

            cursor.fast_executemany = True

            filas_insertadas = 0
            errores = []

            chunk_size = 1000

            for inicio in range(0, len(rows), chunk_size):
                chunk = rows[inicio: inicio + chunk_size]

                try:
                    cursor.executemany(insert_sql, chunk)
                    filas_insertadas += len(chunk)
                except Exception as exc:
                    errores.append(
                        {
                            "bloque_inicio": inicio + 1,
                            "bloque_fin": inicio + len(chunk),
                            "error": str(exc),
                        }
                    )
                    raise

            conn.commit()

            total_despues = _contar_registros_tabla_sql(cursor, schema, table)

        carpeta_carga = Path(rutas["subcarpetas"]["06_carga"])
        carpeta_reportes = Path(rutas["subcarpetas"]["Reportes"])
        carpeta_carga.mkdir(parents=True, exist_ok=True)
        carpeta_reportes.mkdir(parents=True, exist_ok=True)

        ruta_reporte = carpeta_reportes / f"{fecha}_reporte_carga_sql.xlsx"

        resumen = pd.DataFrame(
            [
                {"control": "Conexión", "valor": conexion_normalizada},
                {"control": "Base de datos", "valor": database},
                {"control": "Tabla destino", "valor": f"{schema}.{table}"},
                {"control": "Archivo leído", "valor": str(ruta_excel)},
                {"control": "Filas leídas Excel", "valor": filas_leidas},
                {"control": "Filas insertadas SQL", "valor": filas_insertadas},
                {"control": "Columnas insertadas", "valor": len(columnas_insertar)},
                {"control": "Columnas Excel omitidas", "valor": len(columnas_omitidas_excel)},
                {"control": "Columnas tabla sin Excel", "valor": len(columnas_tabla_sin_excel)},
                {"control": "Total tabla antes", "valor": "" if total_antes is None else total_antes},
                {"control": "Total tabla después", "valor": "" if total_despues is None else total_despues},
                {"control": "Errores", "valor": len(errores)},
            ]
        )

        df_columnas_insertadas = pd.DataFrame({"columna_insertada": columnas_insertar})
        df_columnas_omitidas = pd.DataFrame({"columna_excel_omitida": columnas_omitidas_excel})
        df_columnas_faltantes = pd.DataFrame({"columna_tabla_sin_excel": columnas_tabla_sin_excel})
        df_errores = pd.DataFrame(errores)

        with pd.ExcelWriter(ruta_reporte) as writer:
            resumen.to_excel(writer, sheet_name="Resumen", index=False)
            df_columnas_insertadas.to_excel(writer, sheet_name="ColumnasInsertadas", index=False)
            df_columnas_omitidas.to_excel(writer, sheet_name="ColumnasExcelOmitidas", index=False)
            df_columnas_faltantes.to_excel(writer, sheet_name="ColumnasTablaSinExcel", index=False)
            df_errores.to_excel(writer, sheet_name="Errores", index=False)

        return {
            "ok": True,
            "fecha": fecha,
            "conexion": conexion_normalizada,
            "database": database,
            "schema": schema,
            "table": table,
            "tabla_destino": f"{database}.{schema}.{table}",
            "ruta_excel": str(ruta_excel),
            "ruta_reporte": str(ruta_reporte),
            "archivo_excel": ruta_excel.name,
            "archivo_reporte": ruta_reporte.name,
            "filas_leidas": filas_leidas,
            "filas_insertadas": filas_insertadas,
            "columnas_insertadas": columnas_insertar,
            "columnas_omitidas_excel": columnas_omitidas_excel,
            "columnas_tabla_sin_excel": columnas_tabla_sin_excel,
            "total_antes": total_antes,
            "total_despues": total_despues,
            "errores": errores,
        }
    except Exception as exc:
        return {
            "ok": False,
            "fecha": fecha,
            "conexion": conexion_normalizada,
            "database": database,
            "schema": schema,
            "table": table,
            "tabla_destino": f"{database}.{schema}.{table}",
            "ruta_excel": str(ruta_excel),
            "error": str(exc),
        }
'''
    SERVICE.write_text(service, encoding="utf-8")


# ============================================================
# 2) Renderer
# ============================================================

renderer = RENDERER.read_text(encoding="utf-8")

if "def render_carga_sql_gestion(" not in renderer:
    renderer += r'''


def render_carga_sql_gestion(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        return (
            render_alert("error", f"❌ Error cargando información SQL: {resultado.get('error', '')}")
            + "<div class='gc-result-grid'>"
            + "<div class='gc-result-card'><h4>Conexión</h4><p>"
            + escape(str(resultado.get("conexion", "")))
            + "</p></div>"
            + "<div class='gc-result-card'><h4>Tabla destino</h4><p>"
            + escape(str(resultado.get("tabla_destino", "")))
            + "</p></div>"
            + "<div class='gc-result-card'><h4>Archivo Excel</h4><p>"
            + escape(str(resultado.get("ruta_excel", "")))
            + "</p></div>"
            + "</div>"
        )

    filas_leidas = _safe_int(resultado.get("filas_leidas", 0))
    filas_insertadas = _safe_int(resultado.get("filas_insertadas", 0))
    columnas_insertadas = resultado.get("columnas_insertadas") or []
    columnas_omitidas = resultado.get("columnas_omitidas_excel") or []
    columnas_faltantes = resultado.get("columnas_tabla_sin_excel") or []
    errores = resultado.get("errores") or []

    html = [
        render_alert("success", "✅ Carga SQL final completada correctamente."),
        "<div class='gc-result-grid'>",
        "<div class='gc-result-card'><h4>Conexión usada</h4><p><b>",
        escape(str(resultado.get("conexion", ""))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Tabla destino</h4><p><b>",
        escape(str(resultado.get("tabla_destino", ""))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Filas leídas</h4><p><b>",
        escape(str(filas_leidas)),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Filas insertadas</h4><p><b>",
        escape(str(filas_insertadas)),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Total tabla antes</h4><p><b>",
        escape(str(resultado.get("total_antes", ""))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Total tabla después</h4><p><b>",
        escape(str(resultado.get("total_despues", ""))),
        "</b></p></div>",
        "</div>",
    ]

    html.append("<div class='gc-donut-row'>")
    html.append(_render_gc_donut_card("Inserción SQL", filas_leidas, filas_insertadas, "insertadas"))
    html.append(_render_gc_donut_card("Columnas insertadas", len(columnas_insertadas) + len(columnas_omitidas), len(columnas_insertadas), "usadas"))
    html.append("</div>")

    html.append("<h4>Archivo cargado</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Tipo</th><th>Nombre</th><th>Ruta</th></tr></thead><tbody>")
    html.append(
        f"<tr><td>Excel final</td><td>{escape(str(resultado.get('archivo_excel', '')))}</td><td>{escape(str(resultado.get('ruta_excel', '')))}</td></tr>"
    )
    html.append(
        f"<tr><td>Reporte carga SQL</td><td>{escape(str(resultado.get('archivo_reporte', '')))}</td><td>{escape(str(resultado.get('ruta_reporte', '')))}</td></tr>"
    )
    html.append("</tbody></table></div>")

    html.append(
        _render_gc_collapsible(
            "Columnas insertadas",
            _gc_count_badge(len(columnas_insertadas), "columnas"),
            _render_gc_columns_grid(columnas_insertadas, 6),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Columnas del Excel no insertadas",
            _gc_count_badge(len(columnas_omitidas), "columnas"),
            _render_gc_columns_grid(columnas_omitidas, 6),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Columnas de tabla sin columna equivalente en Excel",
            _gc_count_badge(len(columnas_faltantes), "columnas"),
            _render_gc_columns_grid(columnas_faltantes, 6),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Errores de carga",
            _gc_count_badge(len(errores), "errores"),
            _render_gc_table_from_dicts(errores, 80),
            open_default=False,
        )
    )

    return "".join(html)
'''
    RENDERER.write_text(renderer, encoding="utf-8")


# ============================================================
# 3) Blueprint
# ============================================================

bp = BLUEPRINT.read_text(encoding="utf-8")

if "cargar_informacion_gestion_sql" not in bp:
    bp = bp.replace(
        "    listar_archivos_generados_gestion,\n)",
        "    listar_archivos_generados_gestion,\n    cargar_informacion_gestion_sql,\n)",
        1,
    )

if "render_carga_sql_gestion" not in bp:
    bp = bp.replace(
        "    render_archivos_generados_gestion,\n)",
        "    render_archivos_generados_gestion,\n    render_carga_sql_gestion,\n)",
        1,
    )

if "/accion/gestion-consolidada/cargar-sql" not in bp:
    bp += r'''


@gestion_consolidada_bp.route("/accion/gestion-consolidada/cargar-sql", methods=["POST"])
def accion_gestion_consolidada_cargar_sql():
    fecha = request.form.get("fecha", "")
    conexion = request.form.get("conexion", "local")

    resultado = cargar_informacion_gestion_sql(_data_dir(), fecha, conexion)

    return render_carga_sql_gestion(resultado)
'''
    BLUEPRINT.write_text(bp, encoding="utf-8")


# ============================================================
# 4) Template: sección Fase I
# ============================================================

tpl = TEMPLATE.read_text(encoding="utf-8")

if "Fase I — Cargar información" not in tpl:
    bloque = r'''
        <section class="gc-section">
            <div class="gc-section-header">
                <h2>Fase I — Cargar información</h2>
                <p>Carga YYYYMMDD_Gestion_excel.xlsx en Vencorp_V2.gestion.gestion_adminfo_onedrive usando la conexión global.</p>
            </div>

            <div class="gc-inline-controls">
                <span class="gc-mini-note">
                    La carga usa la conexión global seleccionada arriba. LOCAL es para pruebas; REMOTO es producción.
                </span>
            </div>

            <button type="button" class="gc-btn success" onclick="gcEjecutarFaseI()">
                Ejecutar Fase I: Cargar información SQL
            </button>

            <div id="gcResultadoFaseI" class="gc-result-block">
                <div class="log-line warning">⚠️ Fase I pendiente.</div>
            </div>
        </section>
'''

    tpl = tpl.replace(
        '        <section class="gc-section muted">',
        bloque + "\n        <section class=\"gc-section muted\">",
        1,
    )

    tpl = tpl.replace("                <div>I — Carga SQL final</div>\n", "")

    TEMPLATE.write_text(tpl, encoding="utf-8")


# ============================================================
# 5) JS: ejecutar Fase I
# ============================================================

js = JS.read_text(encoding="utf-8")

if "async function gcEjecutarFaseI()" not in js:
    bloque_js = r'''
    async function gcEjecutarFaseI() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        if (conexionGlobal === "remoto") {
            const confirmar = confirm(
                "Está por cargar información en conexión REMOTO / PRODUCCIÓN. ¿Desea continuar?"
            );

            if (!confirmar) {
                return;
            }
        }

        actualizarFase("I", "running", "Cargando información SQL.");
        setHtml("gcResultadoFaseI", htmlLoading("Cargando información en SQL Server..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/cargar-sql", formBase());
            setHtml("gcResultadoFaseI", html);

            const error = String(html).includes("Error cargando información SQL");

            actualizarFase(
                "I",
                error ? "error" : "done",
                error ? "Error en carga SQL." : "Carga SQL completada."
            );
        } catch (error) {
            setHtml("gcResultadoFaseI", htmlError(`Error ejecutando Fase I: ${error.message || error}`));
            actualizarFase("I", "error", String(error.message || error));
        }
    }
'''

    js = js.replace(
        "    function inicializarGestionConsolidada() {",
        bloque_js + "\n    function inicializarGestionConsolidada() {",
        1,
    )

    js = js.replace(
        "    window.gcEjecutarFaseH = gcEjecutarFaseH;",
        "    window.gcEjecutarFaseH = gcEjecutarFaseH;\n    window.gcEjecutarFaseI = gcEjecutarFaseI;",
        1,
    )

    JS.write_text(js, encoding="utf-8")


# ============================================================
# 6) CSS
# ============================================================

css = CSS.read_text(encoding="utf-8")

if "CONSOLIDAR GESTIÓN v1I" not in css:
    css += r'''

/* ============================================================
   CONSOLIDAR GESTIÓN v1I
   ============================================================ */

body.gc-body .gc-process-panels #gcResultadoFaseI .gc-result-card p {
    word-break: break-word;
}

body.gc-body .gc-process-panels #gcResultadoFaseI .gc-values-grid-six {
    grid-template-columns: repeat(6, minmax(110px, 1fr));
}
'''
    CSS.write_text(css, encoding="utf-8")


# ============================================================
# 7) Audit
# ============================================================

audit = AUDIT.read_text(encoding="utf-8")

if "/accion/gestion-consolidada/cargar-sql" not in audit:
    audit = audit.replace(
        '        "/accion/gestion-consolidada/archivos-generados",',
        '        "/accion/gestion-consolidada/archivos-generados",\n        "/accion/gestion-consolidada/cargar-sql",',
    )

if "gcEjecutarFaseI" not in audit:
    audit = audit.replace(
        '        "gcEjecutarFaseH",',
        '        "gcEjecutarFaseH",\n        "gcEjecutarFaseI",',
    )

AUDIT.write_text(audit, encoding="utf-8")


print("Consolidar Gestión v1I creado: carga SQL final.")