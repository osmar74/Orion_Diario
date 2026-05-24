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
    """
    if not res.get("success"):
        return render_log_error(res.get("error", "Error desconocido."))

    tipo = str(res.get("tipo", ""))
    conexion = str(res.get("conexion", ""))
    tabla_destino = str(res.get("tabla_destino", ""))
    nombre_archivo = str(res.get("nombre_archivo", ""))
    ruta_archivo = str(res.get("ruta_archivo", ""))

    html = (
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
    html += f"<div><b>Registros en archivo:</b> {escape(str(res.get('registros_archivo', 0)))}</div>"

    if res.get("ultimo_id") is not None:
        html += f"<div><b>Último ID en tabla:</b> {escape(str(res.get('ultimo_id')))}</div>"

    html += f"<div><b>Registros en tabla:</b> {escape(str(res.get('total_tabla', 0)))}</div>"
    html += "</div>"

    html += f"""
    <div style='margin-top:12px;'>
        <button onclick="insertarDatos('{escape(tipo)}', '{escape(conexion)}')"
                style="background:#28a745; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; font-size:0.8rem;">
            📤 Insertar datos en {escape(tabla_destino)}
        </button>
    </div>
    <div id="resultado-insercion-{escape(tipo)}" style="margin-top:10px;"></div>
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

