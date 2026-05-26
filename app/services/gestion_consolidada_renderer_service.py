from __future__ import annotations

from html import escape
from typing import Any


def _td(value: Any) -> str:
    return f"<td>{escape(str(value if value is not None else ''))}</td>"


def _bool(value: Any) -> str:
    return "✅ Sí" if value else "❌ No"


def render_alert(tipo: str, texto: str) -> str:
    return f"<div class='log-line {escape(tipo)}'>{escape(texto)}</div>"


def render_resumen_sql(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        return (
            "<div class='gc-card-error'>"
            "<b>❌ No se pudo cargar la tabla resumen inicial.</b>"
            f"<p>Conexión: {escape(str(resultado.get('conexion', '')))}</p>"
            f"<p>Fecha: {escape(str(resultado.get('fecha', '')))}</p>"
            f"<pre>{escape(str(resultado.get('error', '')))}</pre>"
            "</div>"
        )

    datos = resultado.get("datos") or {}

    columnas = [
        "Total_Aster_dia_nc",
        "Total_Aster_comentarios",
        "Total_Aster_Usuarios",
        "Total_Orion_Causales",
        "Total_Orion_Lote",
        "Total_Orion_Discador",
    ]

    th = "".join(f"<th>{escape(col)}</th>" for col in columnas)
    td = "".join(_td(datos.get(col, 0)) for col in columnas)

    return (
        "<div class='gc-table-wrap'>"
        "<table class='gc-table'>"
        "<thead><tr>"
        f"{th}"
        "</tr></thead>"
        "<tbody><tr>"
        f"{td}"
        "</tr></tbody>"
        "</table>"
        "</div>"
        "<div class='gc-mini-note'>"
        f"Conexión: <b>{escape(str(resultado.get('conexion')))}</b> | "
        f"Fecha SQL: <b>{escape(str(resultado.get('fecha')))}</b>"
        "</div>"
    )


def render_preparar_proceso(resultado: dict[str, Any]) -> str:
    tipo = "success" if resultado.get("ok") else "warning"

    html = [
        render_alert(tipo, resultado.get("mensaje", "")),
        "<div class='gc-result-grid'>",
        "<div class='gc-result-card'>",
        "<h4>📁 Carpeta Consolidado Gestión</h4>",
        f"<p>{escape(str(resultado.get('carpeta_consolidado', '')))}</p>",
        "</div>",
        "<div class='gc-result-card'>",
        "<h4>📅 Fecha / Mes Gestión</h4>",
        f"<p>Fecha: <b>{escape(str(resultado.get('fecha_iso', '')))}</b></p>",
        f"<p>Mes Gestión: <b>{escape(str(resultado.get('mes_gestion', '')))}</b></p>",
        "</div>",
        "</div>",
    ]

    html.append("<h4>📄 Archivos base encontrados</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append(
        "<thead><tr>"
        "<th>Origen</th>"
        "<th>Existe</th>"
        "<th>Nombre</th>"
        "<th>Ruta</th>"
        "<th>Filas</th>"
        "<th>Tamaño KB</th>"
        "<th>Creación</th>"
        "<th>Modificación</th>"
        "</tr></thead><tbody>"
    )

    for item in resultado.get("archivos", []):
        html.append(
            "<tr>"
            f"{_td(item.get('origen'))}"
            f"{_td(_bool(item.get('existe')))}"
            f"{_td(item.get('nombre'))}"
            f"{_td(item.get('ruta'))}"
            f"{_td(item.get('filas'))}"
            f"{_td(item.get('tamano_kb'))}"
            f"{_td(item.get('fecha_creacion'))}"
            f"{_td(item.get('fecha_modificacion'))}"
            "</tr>"
        )

    html.append("</tbody></table></div>")

    html.append("<h4>🗂️ Estructura creada</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Carpeta</th><th>Existe</th><th>Ruta</th></tr></thead><tbody>")

    for item in resultado.get("carpetas", []):
        html.append(
            "<tr>"
            f"{_td(item.get('carpeta'))}"
            f"{_td(_bool(item.get('existe')))}"
            f"{_td(item.get('ruta'))}"
            "</tr>"
        )

    html.append("</tbody></table></div>")

    return "".join(html)



def render_unir_archivos_gestion(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        html = [
            render_alert("error", f"❌ Error en unión de archivos: {resultado.get('error', '')}"),
            "<div class='gc-result-grid'>",
            "<div class='gc-result-card'><h4>Archivo ASTER</h4><p>",
            escape(str(resultado.get("ruta_aster", ""))),
            "</p></div>",
            "<div class='gc-result-card'><h4>Archivo ORION</h4><p>",
            escape(str(resultado.get("ruta_orion", ""))),
            "</p></div>",
            "</div>",
        ]

        encabezados = resultado.get("encabezados") or {}

        if encabezados:
            html.append("<h4>Detalle de encabezados incompatibles</h4>")
            html.append("<div class='gc-table-wrap'><table class='gc-table'>")
            html.append("<thead><tr><th>Tipo</th><th>Columna</th></tr></thead><tbody>")

            for col in encabezados.get("faltan_en_orion", []):
                html.append(f"<tr><td>Falta en ORION</td><td>{escape(str(col))}</td></tr>")

            for col in encabezados.get("sobran_en_orion", []):
                html.append(f"<tr><td>Sobra en ORION</td><td>{escape(str(col))}</td></tr>")

            html.append("</tbody></table></div>")

        return "".join(html)

    html = [
        render_alert("success", "✅ Unión ASTER + ORION completada correctamente."),
        "<div class='gc-result-grid'>",
        "<div class='gc-result-card'><h4>Total ASTER</h4><p><b>",
        escape(str(resultado.get("total_aster", 0))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Total ORION</h4><p><b>",
        escape(str(resultado.get("total_orion", 0))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Total unión</h4><p><b>",
        escape(str(resultado.get("total_union", 0))),
        "</b></p></div>",
        "</div>",
        "<h4>Archivos generados</h4>",
        "<div class='gc-table-wrap'><table class='gc-table'>",
        "<thead><tr><th>Tipo</th><th>Nombre</th><th>Ruta</th></tr></thead><tbody>",
        f"<tr><td>Unión</td><td>{escape(str(resultado.get('archivo_union', '')))}</td><td>{escape(str(resultado.get('ruta_union', '')))}</td></tr>",
        f"<tr><td>Reporte</td><td>{escape(str(resultado.get('archivo_reporte', '')))}</td><td>{escape(str(resultado.get('ruta_reporte', '')))}</td></tr>",
        "</tbody></table></div>",
        "<h4>Encabezados finales</h4>",
        "<div class='gc-table-wrap'><table class='gc-table'>",
        "<thead><tr><th>#</th><th>Columna</th></tr></thead><tbody>",
    ]

    for idx, col in enumerate(resultado.get("columnas", []), start=1):
        html.append(f"<tr><td>{idx}</td><td>{escape(str(col))}</td></tr>")

    html.append("</tbody></table></div>")

    encabezados = resultado.get("encabezados") or {}

    html.append("<div class='gc-mini-note'>")
    html.append(
        "Encabezados compatibles: <b>SI</b> | "
        f"Mismo orden original: <b>{'SI' if encabezados.get('mismo_orden') else 'NO, ORION fue reordenado'}</b>"
    )
    html.append("</div>")

    return "".join(html)
