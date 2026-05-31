"""
Renderer temporal para ORION Fase G.

Responsabilidad:
- Generar HTML de resultados de carga/exportación.
- Reducir HTML directo dentro de carga_blueprint.py.
- Preparar migración futura a templates/partials.
"""

from __future__ import annotations

from html import escape
from typing import Any
from app.services.schema_validator import generar_html_errores_longitud


def render_log_error(mensaje: str) -> str:
    return f"<div class='log-line error'>❌ {escape(str(mensaje))}</div>"


def render_log_success(mensaje: str) -> str:
    return f"<div class='log-line success'>✅ {escape(str(mensaje))}</div>"


def render_tabla_estadisticas_consolidado(
    titulo: str,
    filas: list[tuple[str, Any]],
) -> str:
    """
    Genera una tabla HTML simple para mostrar estadísticas del consolidado.
    """
    html = f"""
    <div style='margin-top:10px; margin-bottom:10px;'>
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                    {escape(str(titulo))}
                </th>
            </tr>
    """

    for descripcion, valor in filas:
        html += f"""
            <tr>
                <td><b>{escape(str(descripcion))}</b></td>
                <td style='font-size:1rem; font-weight:bold;'>
                    {escape(str(valor))}
                </td>
            </tr>
        """

    html += """
        </table>
    </div>
    """

    return html


def render_gestion_orion_exportada(
    html_estadisticas: str,
    nombre_archivo: str,
    ruta_salida: str,
    ruta_relativa_descarga: str,
) -> str:
    """
    Genera HTML final de exportación Gestión ORION.

    Solo usa el enlace correcto:
    /descargar/YYYYMMDD/Orion/Salidas/YYYYMMDD_Gestion_orion.xlsx
    """
    html = html_estadisticas

    html += """
    <div class='log-line success'>
        ✅ Excel generado correctamente.
    </div>
    """

    html += f"""
    <p style='font-size:0.8rem;'>
        <b>Archivo:</b> {escape(str(nombre_archivo))}
    </p>
    """

    html += f"""
    <p>
        <a href='/descargar/{escape(str(ruta_relativa_descarga))}'
           style='color:#1e90ff; text-decoration:none; font-weight:bold;'>
            📥 Descargar {escape(str(nombre_archivo))}
        </a>
    </p>
    """

    html += f"""
    <p style='font-size:0.7rem; color:#888;'>
        Ruta: {escape(str(ruta_salida))}
    </p>
    """

    return html

def render_verificacion_carga_orion(res: dict[str, Any]) -> str:
    """
    Genera HTML de verificación de carga ORION.

    V2 seguro:
    - No usa onclick inline.
    - No usa insertarDatos(...) legacy.
    - El botón lo maneja app/static/js/orion_carga_v2_insert.js.
    """
    if not res.get("success"):
        return render_log_error(res.get("error", "Error desconocido."))

    tipo = str(res.get("tipo", ""))
    conexion = str(res.get("conexion", ""))
    tabla_destino = str(res.get("tabla_destino", ""))
    nombre_archivo = str(res.get("nombre_archivo", ""))
    ruta_archivo = str(res.get("ruta_archivo", ""))
    registros_archivo = res.get("registros_archivo", 0)

    tipo_lower = tipo.strip().lower()
    tabla_lower = tabla_destino.strip().lower()

    if "causal" in tipo_lower or "causal" in tabla_lower:
        insert_label = "Causales"
    elif "lote" in tipo_lower or "lote" in tabla_lower:
        insert_label = "Lotes"
    elif "discador" in tipo_lower or "discador" in tabla_lower:
        insert_label = "Discador"
    else:
        insert_label = tipo.capitalize() if tipo else "Datos"

    result_id = f"resultado-insercion-v2-{tipo_lower or 'orion'}"

    html = ""

    html += (
        "<div class='odv2-carga-v2-count-marker' style='display:none;'>"
        f"Registros detectados: {escape(str(registros_archivo))}. "
        f"Registros a insertar: {escape(str(registros_archivo))}."
        "</div>"
    )

    html += (
        f"<div class='log-line success'>"
        f"✅ Verificación de {escape(tipo.capitalize())} "
        f"(conexión {escape(conexion)})"
        f"</div>"
    )

    html += (
        f"<p style='font-size:0.75rem;'>"
        f"<b>Archivo:</b> {escape(nombre_archivo)}<br>"
        f"<b>Ruta:</b> {escape(ruta_archivo)}"
        f"</p>"
    )

    html += (
        f"<p style='font-size:0.75rem;'>"
        f"<b>Tabla destino:</b> {escape(tabla_destino)} "
        f"({escape(str(res.get('total_columnas_sql', 0)))} columnas)"
        f"</p>"
    )

    html += "<table class='dataframe' style='width:100%;'>"
    html += (
        "<tr>"
        "<th>Columna SQL Server</th>"
        "<th>Columna en Archivo</th>"
        "<th>Coincide</th>"
        "<th>Tipo SQL</th>"
        "</tr>"
    )

    for fila in res.get("columnas", []):
        coincide = "✅" if fila.get("coincide") else "❌"

        html += (
            "<tr>"
            f"<td>{escape(str(fila.get('columna_sql', '')))}</td>"
            f"<td>{escape(str(fila.get('columna_archivo') or '—'))}</td>"
            f"<td>{coincide}</td>"
            f"<td>{escape(str(fila.get('tipo_sql', '?')))}</td>"
            "</tr>"
        )

    html += "</table>"

    html += "<div style='display:flex; gap:20px; margin-top:10px; font-size:0.75rem;'>"
    html += f"<div><b>Registros en archivo:</b> {escape(str(registros_archivo))}</div>"

    if res.get("ultimo_id") is not None:
        html += f"<div><b>Último ID en tabla:</b> {escape(str(res.get('ultimo_id')))}</div>"

    html += f"<div><b>Registros en tabla:</b> {escape(str(res.get('total_tabla', 0)))}</div>"
    html += "</div>"

    html += f"""
    <div class="odv2-carga-v2-actions">
        <button type="button"
                class="odv2-carga-v2-insert-btn"
                data-orion-carga-v2-insert="1"
                data-tipo="{escape(tipo, quote=True)}"
                data-conexion="{escape(conexion, quote=True)}"
                data-target="{escape(result_id, quote=True)}">
            Insertar Datos {escape(insert_label)}
        </button>
    </div>

    """

    return html

def render_carga_duplicada_orion(res: dict[str, Any]) -> str:
    """
    Genera HTML para carga duplicada bloqueada.
    """
    carga_previa = res.get("carga_previa") or {}

    return f"""
    <div class='log-line warning'>
        ⚠️ Este archivo ya fue insertado anteriormente.
    </div>
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#8a6d3b; color:#fff;'>
                Carga duplicada bloqueada
            </th>
        </tr>
        <tr><td><b>Tipo</b></td><td>{escape(str(res.get("tipo", "")))}</td></tr>
        <tr><td><b>Conexión</b></td><td>{escape(str(res.get("conexion", "")))}</td></tr>
        <tr><td><b>Tabla destino</b></td><td>{escape(str(res.get("tabla_destino", "")))}</td></tr>
        <tr><td><b>Archivo</b></td><td>{escape(str(carga_previa.get("nombre_archivo", "")))}</td></tr>
        <tr><td><b>Registros archivo</b></td><td>{escape(str(carga_previa.get("registros_archivo", "")))}</td></tr>
        <tr><td><b>Registros insertados</b></td><td>{escape(str(carga_previa.get("registros_insertados", "")))}</td></tr>
        <tr><td><b>Fecha de carga</b></td><td>{escape(str(carga_previa.get("fecha_carga", "")))}</td></tr>
    </table>
    """


def render_insercion_orion_ok(res: dict[str, Any]) -> str:
    """
    Genera HTML final de inserción ORION.
    """
    exito = bool(res.get("exito"))

    color_coincide = "#28a745" if exito else "#dc3545"
    texto_coincide = "Coincide" if exito else "No coincide"

    tipo = str(res.get("tipo", ""))
    tabla_destino = str(res.get("tabla_destino", ""))
    nombre_archivo = str(res.get("nombre_archivo", ""))
    ruta_archivo = str(res.get("ruta_archivo", ""))

    html = "<div style='margin-top:10px;'>"

    html += f"""
    <div class='log-line {"success" if exito else "error"}'>
        {"✅" if exito else "⚠️"} Inserción de {escape(tipo.capitalize())} completada.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Información de la carga
            </th>
        </tr>
    """

    html += f"<tr><td><b>Tabla destino</b></td><td>{escape(tabla_destino)}</td></tr>"
    html += f"<tr><td><b>Archivo</b></td><td>{escape(nombre_archivo)}</td></tr>"
    html += f"<tr><td><b>Ruta</b></td><td style='font-size:0.7rem;'>{escape(ruta_archivo)}</td></tr>"
    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>Registros en archivo</th>
            <th>Registros antes</th>
            <th>Registros después</th>
            <th>Insertados</th>
        </tr>
    """

    html += "<tr>"
    html += f"<td style='font-size:1.1rem; font-weight:bold;'>{escape(str(res.get('registros_archivo', 0)))}</td>"
    html += f"<td>{escape(str(res.get('registros_antes', 0)))}</td>"
    html += f"<td>{escape(str(res.get('registros_despues', 0)))}</td>"
    html += (
        f"<td style='color:{color_coincide}; font-weight:bold;'>"
        f"{escape(str(res.get('insertados', 0)))} ({texto_coincide})"
        "</td>"
    )
    html += "</tr></table>"
    html += "</div>"

    return html


def render_insercion_orion_resultado(res: dict[str, Any]) -> str:
    """
    Decide qué HTML devolver según el resultado del service.
    """
    status = str(res.get("status", ""))

    if status == "duplicado":
        return render_carga_duplicada_orion(res)

    if status == "errores_longitud":
        return generar_html_errores_longitud(res.get("errores_longitud", []))

    if status == "insertado":
        return render_insercion_orion_ok(res)

    return render_log_error(res.get("error", "Error desconocido en inserción ORION."))


def render_consolidado_consulta_orion(res: dict[str, Any]) -> str:
    """
    Genera HTML para resultado de consulta consolidada ORION.
    """
    if not res.get("success"):
        if res.get("status") == "sin_resultados":
            return (
                "<div class='log-line warning'>"
                f"⚠️ {escape(str(res.get('warning', 'La consulta no devolvió resultados.')))}"
                "</div>"
            )

        return render_log_error(res.get("error", "Error desconocido."))

    valores_unicos = res.get("valores_unicos", [])
    temp_id = str(res.get("temp_id", ""))

    html = f"""
    <p style='font-size:0.75rem; color:#ccc;'>
        Valores únicos en 'Descripción Codigo de Gestion' con fecha de compromiso
        ({escape(str(len(valores_unicos)))})
    </p>
    """

    html += "<div style='max-height:200px; overflow-y:auto; margin-bottom:10px;'>"
    html += "<table class='dataframe' style='width:100%;'>"
    html += "<tr><th>Seleccionar</th><th>Descripción</th></tr>"

    for valor in valores_unicos:
        valor_esc = escape(str(valor), quote=True)
        html += (
            "<tr>"
            f"<td><input type='checkbox' name='descripcion' value='{valor_esc}'></td>"
            f"<td>{escape(str(valor))}</td>"
            "</tr>"
        )

    html += "</table>"
    html += "</div>"

    html += f"<input type='hidden' id='cons-temp-id' value='{escape(temp_id, quote=True)}'>"

    html += """
    <button onclick='return aplicarFiltroYExportar(this)'
            style='background:#28a745; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; font-size:0.8rem;'>
        Aplicar Filtro y Exportar a Excel
    </button>
    """

    return html

def render_prueba_conexion_orion(res: dict[str, Any]) -> str:
    """
    HTML para prueba de conexión SQL Server ORION.
    """
    if not res.get("success"):
        return render_log_error(res.get("error", "Error de conexión."))

    return (
        "<div class='log-line success'>"
        f"✅ {escape(str(res.get('mensaje', 'Conexión exitosa')))}"
        "</div>"
    )


def render_prueba_lectura_orion(res: dict[str, Any]) -> str:
    """
    HTML para prueba de lectura SQL Server ORION.
    """
    if not res.get("success"):
        if res.get("status") == "sin_registros":
            return (
                "<div class='log-line warning'>"
                f"⚠️ {escape(str(res.get('warning', 'La tabla no contiene registros.')))}"
                "</div>"
            )

        return render_log_error(res.get("error", "Error al leer la tabla."))

    columnas = res.get("columnas", [])
    filas = res.get("filas", [])

    html = (
        "<div class='log-line success'>"
        f"✅ Lectura exitosa. {escape(str(res.get('registros', 0)))} registros encontrados."
        "</div>"
    )

    html += "<table class='dataframe' style='width:100%; margin-top:10px;'>"

    html += "<tr>"
    for columna in columnas:
        html += f"<th>{escape(str(columna))}</th>"
    html += "</tr>"

    for fila in filas:
        html += "<tr>"
        for columna in columnas:
            html += f"<td>{escape(str(fila.get(columna, '')))}</td>"
        html += "</tr>"

    html += "</table>"

    return html

