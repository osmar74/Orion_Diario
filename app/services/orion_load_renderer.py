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

