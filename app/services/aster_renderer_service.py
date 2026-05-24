"""
Renderers HTML para Gestión Diaria ASTER.

Responsabilidad:
- Generar HTML de respuesta para fases ASTER.
- Mantener aster_blueprint.py más limpio.
- No ejecutar lógica de negocio.
"""

from __future__ import annotations

from html import escape
from typing import Any


def render_total_aster(
    total: int | None,
    origen: str,
    previews: list[tuple[str, str]],
) -> str:
    """
    Genera respuesta HTML para mostrar el total ASTER detectado o ingresado.
    """
    html = "<div class='ocr-result-container'>"

    html += "<div class='ocr-images'>"

    if previews:
        for nombre, img_b64 in previews:
            html += (
                "<div class='ocr-thumb'>"
                f"<img src='data:image/png;base64,{img_b64}' alt='{escape(str(nombre), quote=True)}'/>"
                f"<small>{escape(str(nombre))}</small>"
                "</div>"
            )
    else:
        html += "<p style='color:#888;'>Sin vista previa de imagen.</p>"

    html += "</div>"

    html += "<div class='ocr-results'>"

    if total is not None:
        html += "<div class='log-line success'>✅ Total ASTER capturado correctamente.</div>"
        html += "<div class='totales-grid' style='margin-top:10px;'>"
        html += (
            "<div class='total-card'>"
            "<span class='label'>🔹 Total ASTER</span>"
            f"<span class='value'>{escape(str(total))}</span>"
            "</div>"
        )
        html += "</div>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:10px;'>"
            "<tr><th colspan='2' style='background:#1e3a5f; color:#fff;'>Detalle de captura</th></tr>"
            f"<tr><td><b>Origen</b></td><td>{escape(str(origen))}</td></tr>"
            f"<tr><td><b>Total general</b></td><td>{escape(str(total))}</td></tr>"
            "</table>"
        )
    else:
        html += (
            "<div class='log-line warning'>"
            "⚠️ No se pudo detectar automáticamente el total ASTER. "
            "Ingrese el total manualmente."
            "</div>"
        )

    html += "</div>"
    html += "</div>"

    html += (
        "<div id='aster-total-data' style='display:none;' "
        f"data-total='{escape(str(total if total is not None else ''), quote=True)}'>"
        "</div>"
    )

    return html


def render_archivo_aster(
    fecha_yyyymmdd: str,
    ruta_origen: str,
    ruta_destino: str,
    nombre_archivo: str,
) -> str:
    """
    Genera HTML de resultado para la copia del archivo ASTER.
    """
    html = "<div class='log-line success'>✅ Archivo ASTER localizado y copiado correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Información del archivo ASTER
            </th>
        </tr>
    """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Archivo encontrado", nombre_archivo),
        ("Ruta origen", ruta_origen),
        ("Ruta destino", ruta_destino),
    ]

    for etiqueta, valor in filas:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-archivo-data' style='display:none;' "
        f"data-fecha='{escape(str(fecha_yyyymmdd), quote=True)}' "
        f"data-ruta='{escape(str(ruta_destino), quote=True)}' "
        f"data-archivo='{escape(str(nombre_archivo), quote=True)}'>"
        "</div>"
    )

    return html


def render_normalizacion_aster(
    ruta_archivo: str,
    columnas_originales: list[Any],
    columnas_normalizadas: list[str],
) -> str:
    """
    Genera HTML con tabla comparativa de encabezados originales y normalizados.
    """
    html = "<div class='log-line success'>✅ Encabezados ASTER normalizados correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='3' style='background:#1e3a5f; color:#fff;'>
                Comparación de encabezados ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Encabezado original</th>
            <th>Encabezado normalizado</th>
        </tr>
    """

    for idx, (original, normalizado) in enumerate(
        zip(columnas_originales, columnas_normalizadas),
        start=1,
    ):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(original))}</td>
            <td><b>{escape(str(normalizado))}</b></td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Archivo actualizado
            </th>
        </tr>
        <tr>
            <td><b>Ruta</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(ruta_archivo))}</td>
        </tr>
    </table>
    """

    return html


def render_entidades_excel_aster(
    ruta_archivo: str,
    total_registros: int,
    conteo_entidades: list[tuple[str, int]],
) -> str:
    """
    Genera HTML con entidades únicas del Excel ASTER.
    """
    total_entidades = len(conteo_entidades)
    total_registros_con_entidad = sum(cantidad for _, cantidad in conteo_entidades)
    total_registros_sin_entidad = total_registros - total_registros_con_entidad

    html = "<div class='log-line success'>✅ Entidades ASTER analizadas correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen de entidades del Excel ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Archivo analizado", ruta_archivo),
        ("Registros totales del Excel", total_registros),
        ("Registros con Entidad", total_registros_con_entidad),
        ("Registros sin Entidad", total_registros_sin_entidad),
        ("Entidades únicas encontradas", total_entidades),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Cantidad de registros</th>
        </tr>
    """

    for idx, (entidad, cantidad) in enumerate(conteo_entidades, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(entidad))}</b></td>
            <td style='font-weight:bold;'>{escape(str(cantidad))}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-entidades-excel-data' style='display:none;' "
        f"data-total-entidades='{escape(str(total_entidades), quote=True)}' "
        f"data-total-registros='{escape(str(total_registros), quote=True)}'>"
        "</div>"
    )

    return html


def render_consulta_sql_aster(
    fecha_sql: str,
    resultados: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de la consulta SQL ASTER.
    """
    total_entidades = len(resultados)
    total_registros = sum(int(fila["numero"]) for fila in resultados)

    if not resultados:
        return f"""
        <div class='log-line warning'>
            ⚠️ La consulta ASTER no devolvió resultados para la fecha {escape(str(fecha_sql))}.
        </div>
        """

    html = "<div class='log-line success'>✅ Consulta SQL ASTER ejecutada correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen consulta SQL ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Fecha consultada", fecha_sql),
        ("Entidades devueltas por SQL", total_entidades),
        ("Total registros SQL", total_registros),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.9rem; font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    for idx, fila in enumerate(resultados, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila["entidad"]))}</b></td>
            <td style='font-weight:bold;'>{escape(str(fila["numero"]))}</td>
            <td><code>{escape(str(fila["SSS"]))}</code></td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-sql-data' style='display:none;' "
        f"data-fecha='{escape(str(fecha_sql), quote=True)}' "
        f"data-total-entidades='{escape(str(total_entidades), quote=True)}' "
        f"data-total-registros='{escape(str(total_registros), quote=True)}'>"
        "</div>"
    )

    return html