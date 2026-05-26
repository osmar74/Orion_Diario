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



def _render_gc_table_from_dicts(rows: list[dict[str, Any]], max_rows: int = 80) -> str:
    if not rows:
        return "<div class='log-line success'>✅ Sin registros para mostrar.</div>"

    limited = rows[:max_rows]
    columns = list(limited[0].keys())

    html = [
        "<div class='gc-table-wrap'><table class='gc-table gc-table-small'>",
        "<thead><tr>",
    ]

    for col in columns:
        html.append(f"<th>{escape(str(col))}</th>")

    html.append("</tr></thead><tbody>")

    for row in limited:
        html.append("<tr>")

        for col in columns:
            html.append(f"<td>{escape(str(row.get(col, '')))}</td>")

        html.append("</tr>")

    html.append("</tbody></table></div>")

    if len(rows) > max_rows:
        html.append(
            f"<div class='gc-mini-note'>Mostrando {max_rows} de {len(rows)} registros. Revise el Excel generado para ver todo.</div>"
        )

    return "".join(html)


def render_verificar_calidad_gestion(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        return (
            render_alert("error", f"❌ Error verificando calidad: {resultado.get('error', '')}")
            + "<div class='gc-result-card'><h4>Archivo unión</h4><p>"
            + escape(str(resultado.get("ruta_union", "")))
            + "</p></div>"
        )

    totales = resultado.get("totales") or {}
    columnas = resultado.get("columnas") or {}
    tipo = "warning" if resultado.get("requiere_revision") else "success"
    mensaje = (
        "ℹ️ Verificación completada con observaciones. Revise los reportes generados."
        if resultado.get("requiere_revision")
        else "✅ Verificación completada sin observaciones críticas."
    )

    html = [
        render_alert(tipo, mensaje),
        "<div class='gc-result-grid'>",
    ]

    cards = [
        ("Total inicial", totales.get("total_inicial", 0)),
        ("Valores únicos descripción", totales.get("valores_unicos_descripcion", 0)),
        ("Descripción vacía", totales.get("descripcion_vacia", 0)),
        ("Registros TEL", totales.get("registros_tel", 0)),
        ("TEL sin Asesor/Grabador", totales.get("tel_sin_asesor_grabador", 0)),
        ("Duplicados TEL detectados", totales.get("tel_duplicados_detectados", 0)),
        ("Duplicados TEL eliminados", totales.get("tel_duplicados_eliminados", 0)),
        ("Total final", totales.get("total_final", 0)),
    ]

    for titulo, valor in cards:
        html.append(
            "<div class='gc-result-card'>"
            f"<h4>{escape(str(titulo))}</h4>"
            f"<p><b>{escape(str(valor))}</b></p>"
            "</div>"
        )

    html.append("</div>")

    html.append("<h4>Columnas usadas</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Uso</th><th>Columna detectada</th></tr></thead><tbody>")

    for key, value in columnas.items():
        html.append(f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>")

    html.append("</tbody></table></div>")

    html.append("<h4>C1. Valores únicos en Descripcion Codigo De Gestion</h4>")
    html.append("<p class='gc-mini-note'>Todos aparecen seleccionados por defecto para continuar. Las exclusiones interactivas se implementarán en una siguiente iteración si se requiere.</p>")
    html.append(_render_gc_table_from_dicts(resultado.get("valores_unicos") or [], 300))

    html.append("<h4>C2. Registros TEL sin Asesor o Grabador</h4>")
    html.append(_render_gc_table_from_dicts(resultado.get("tel_incompleto_preview") or [], 80))

    html.append("<h4>C3. Duplicados TEL por Cliente Nro.</h4>")
    html.append(_render_gc_table_from_dicts(resultado.get("tel_duplicados_preview") or [], 80))

    html.append("<h4>Registros eliminados por duplicidad TEL</h4>")
    html.append("<p class='gc-mini-note'>Criterio v1C: se conserva el primer registro y se eliminan los siguientes duplicados. La selección manual se puede agregar en una fase posterior.</p>")
    html.append(_render_gc_table_from_dicts(resultado.get("tel_eliminados_preview") or [], 80))

    html.append("<h4>Archivos generados</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Tipo</th><th>Ruta</th></tr></thead><tbody>")

    files = [
        ("Archivo verificado", resultado.get("ruta_verificada", "")),
        ("Reporte verificación", resultado.get("ruta_reporte", "")),
        ("Descripción vacía", resultado.get("ruta_desc_vacia", "")),
        ("TEL sin Asesor/Grabador", resultado.get("ruta_tel_incompleto", "")),
        ("TEL duplicados eliminados", resultado.get("ruta_tel_eliminados", "")),
    ]

    for tipo_archivo, ruta in files:
        if ruta:
            html.append(f"<tr><td>{escape(str(tipo_archivo))}</td><td>{escape(str(ruta))}</td></tr>")

    html.append("</tbody></table></div>")

    return "".join(html)
