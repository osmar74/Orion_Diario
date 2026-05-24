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