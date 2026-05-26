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



def _gc_count_badge(total: Any, texto: str = "registros") -> str:
    return (
        "<span class='gc-badge-count'>"
        f"{escape(str(total))} {escape(texto)}"
        "</span>"
    )


def _render_gc_collapsible(title: str, badge_html: str, body_html: str, open_default: bool = False) -> str:
    open_attr = " open" if open_default else ""

    return (
        f"<details class='gc-collapse'{open_attr}>"
        "<summary>"
        f"<span>{escape(str(title))}</span>"
        f"{badge_html}"
        "</summary>"
        "<div class='gc-collapse-body'>"
        f"{body_html}"
        "</div>"
        "</details>"
    )


def _render_gc_columns_grid(columns: list[Any], columns_per_row: int = 6) -> str:
    if not columns:
        return "<div class='log-line warning'>⚠️ Sin columnas para mostrar.</div>"

    html = [
        "<div class='gc-values-grid gc-values-grid-six'>",
    ]

    for idx, col in enumerate(columns, start=1):
        html.append(
            "<div class='gc-value-pill'>"
            f"<b>{idx}</b>"
            f"<span>{escape(str(col))}</span>"
            "</div>"
        )

    html.append("</div>")

    return "".join(html)


def _render_gc_values_unique_grid(rows: list[dict[str, Any]], max_items: int = 300) -> str:
    if not rows:
        return "<div class='log-line success'>✅ Sin valores para mostrar.</div>"

    limited = rows[:max_items]

    html = [
        "<div class='gc-values-grid gc-values-grid-six'>",
    ]

    for row in limited:
        desc = (
            row.get("Descripcion Codigo De Gestion")
            or row.get("Descripción Código De Gestión")
            or row.get("descripcion")
            or row.get("valor")
            or ""
        )
        total = row.get("total", "")

        html.append(
            "<div class='gc-value-pill'>"
            f"<span>{escape(str(desc))}</span>"
            f"<b>{escape(str(total))}</b>"
            "</div>"
        )

    html.append("</div>")

    if len(rows) > max_items:
        html.append(
            f"<div class='gc-mini-note'>Mostrando {max_items} de {len(rows)} valores únicos. Revise el Excel generado para ver todo.</div>"
        )

    return "".join(html)


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value or 0).replace(",", ".")))
    except Exception:
        return 0


def _render_gc_donut_card(title: str, total: int, value: int, label_value: str = "Reemplazados") -> str:
    total = max(0, _safe_int(total))
    value = max(0, _safe_int(value))

    pct = 0

    if total:
        pct = round((value / total) * 100, 2)

    if pct < 0:
        pct = 0

    if pct > 100:
        pct = 100

    restante = round(100 - pct, 2)

    return (
        "<div class='gc-donut-card'>"
        f"<h4>{escape(str(title))}</h4>"
        "<div class='gc-donut-layout'>"
        "<svg class='gc-donut' viewBox='0 0 42 42' role='img'>"
        "<circle class='gc-donut-bg' cx='21' cy='21' r='15.9155'></circle>"
        f"<circle class='gc-donut-fill' cx='21' cy='21' r='15.9155' stroke-dasharray='{pct} {restante}' stroke-dashoffset='25'></circle>"
        f"<text x='21' y='22.5' class='gc-donut-text'>{escape(str(round(pct, 1)))}%</text>"
        "</svg>"
        "<div>"
        f"<p><b>{escape(str(value))}</b> {escape(label_value)}</p>"
        f"<p>Total base: <b>{escape(str(total))}</b></p>"
        "</div>"
        "</div>"
        "</div>"
    )

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
            body = [
                "<div class='gc-table-wrap'><table class='gc-table'>",
                "<thead><tr><th>Tipo</th><th>Columna</th></tr></thead><tbody>",
            ]

            for col in encabezados.get("faltan_en_orion", []):
                body.append(f"<tr><td>Falta en ORION</td><td>{escape(str(col))}</td></tr>")

            for col in encabezados.get("sobran_en_orion", []):
                body.append(f"<tr><td>Sobra en ORION</td><td>{escape(str(col))}</td></tr>")

            body.append("</tbody></table></div>")

            html.append(
                _render_gc_collapsible(
                    "Detalle de encabezados incompatibles",
                    _gc_count_badge(
                        len(encabezados.get("faltan_en_orion", [])) + len(encabezados.get("sobran_en_orion", [])),
                        "columnas",
                    ),
                    "".join(body),
                    open_default=True,
                )
            )

        return "".join(html)

    columnas = resultado.get("columnas", []) or []

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
    ]

    encabezados = resultado.get("encabezados") or {}

    html.append(
        _render_gc_collapsible(
            "Encabezados finales",
            _gc_count_badge(len(columnas), "columnas"),
            _render_gc_columns_grid(columnas, 6),
            open_default=False,
        )
    )

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

    valores = resultado.get("valores_unicos") or []
    tel_incompleto = resultado.get("tel_incompleto_preview") or []
    tel_duplicados = resultado.get("tel_duplicados_preview") or []
    tel_eliminados = resultado.get("tel_eliminados_preview") or []

    html.append(
        _render_gc_collapsible(
            "C1. Valores únicos en Descripcion Codigo De Gestion",
            _gc_count_badge(totales.get("valores_unicos_descripcion", len(valores)), "valores"),
            _render_gc_values_unique_grid(valores, 300),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "C2. Registros TEL sin Asesor o Grabador",
            _gc_count_badge(totales.get("tel_sin_asesor_grabador", len(tel_incompleto))),
            _render_gc_table_from_dicts(tel_incompleto, 80),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "C3. Duplicados TEL por Cliente Nro.",
            _gc_count_badge(totales.get("tel_duplicados_detectados", len(tel_duplicados))),
            _render_gc_table_from_dicts(tel_duplicados, 80),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Registros eliminados por duplicidad TEL",
            _gc_count_badge(totales.get("tel_duplicados_eliminados", len(tel_eliminados))),
            _render_gc_table_from_dicts(tel_eliminados, 80),
            open_default=False,
        )
    )

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

def render_ajuste_no_contestan_gestion(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        return (
            render_alert("error", f"❌ Error aplicando ajuste No contestan: {resultado.get('error', '')}")
            + "<div class='gc-result-card'><h4>Archivo entrada</h4><p>"
            + escape(str(resultado.get("ruta_entrada", "")))
            + "</p></div>"
        )

    detalle = resultado.get("detalle", []) or []
    reemplazados_preview = resultado.get("reemplazados_preview") or []

    total_encontrados = sum(_safe_int(item.get("Total encontrados", 0)) for item in detalle)
    total_reemplazos = _safe_int(resultado.get("total_reemplazos", 0))

    total_home = sum(
        _safe_int(item.get("Total encontrados", 0))
        for item in detalle
        if str(item.get("Tipo Cartera", "")).lower() == "home"
    )
    repl_home = sum(
        _safe_int(item.get("Total reemplazados", 0))
        for item in detalle
        if str(item.get("Tipo Cartera", "")).lower() == "home"
    )

    total_mobile = sum(
        _safe_int(item.get("Total encontrados", 0))
        for item in detalle
        if str(item.get("Tipo Cartera", "")).lower() == "mobile"
    )
    repl_mobile = sum(
        _safe_int(item.get("Total reemplazados", 0))
        for item in detalle
        if str(item.get("Tipo Cartera", "")).lower() == "mobile"
    )

    html = [
        render_alert("success", "✅ Ajuste No contestan aplicado correctamente. Control de filas válido."),
        "<div class='gc-result-grid'>",
        "<div class='gc-result-card'><h4>Total filas antes</h4><p><b>",
        escape(str(resultado.get("total_inicial", 0))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Total filas después</h4><p><b>",
        escape(str(resultado.get("total_final", 0))),
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Control filas iguales</h4><p><b>",
        "✅ SI" if resultado.get("control_filas_ok") else "❌ NO",
        "</b></p></div>",
        "<div class='gc-result-card'><h4>Porcentaje aplicado</h4><p><b>",
        escape(str(resultado.get("porcentaje", ""))),
        "%</b></p></div>",
        "<div class='gc-result-card'><h4>Total reemplazos</h4><p><b>",
        escape(str(resultado.get("total_reemplazos", 0))),
        "</b></p></div>",
        "</div>",
    ]

    html.append("<div class='gc-donut-row'>")
    html.append(_render_gc_donut_card("Reemplazos globales", total_encontrados, total_reemplazos))
    html.append(_render_gc_donut_card("Home", total_home, repl_home))
    html.append(_render_gc_donut_card("Mobile", total_mobile, repl_mobile))
    html.append("</div>")

    columnas = resultado.get("columnas") or {}

    html.append("<h4>Columnas usadas</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Uso</th><th>Columna detectada</th></tr></thead><tbody>")

    for key, value in columnas.items():
        html.append(f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>")

    html.append("</tbody></table></div>")

    tabla_detalle = [
        "<div class='gc-table-wrap'><table class='gc-table'>",
        "<thead><tr>"
        "<th>Tipo Cartera</th>"
        "<th>Descripción original</th>"
        "<th>Total encontrados</th>"
        "<th>Porcentaje aplicado</th>"
        "<th>Total reemplazados</th>"
        "<th>Nuevo valor</th>"
        "</tr></thead><tbody>",
    ]

    for item in detalle:
        tabla_detalle.append(
            "<tr>"
            f"<td>{escape(str(item.get('Tipo Cartera', '')))}</td>"
            f"<td>{escape(str(item.get('Descripcion original', '')))}</td>"
            f"<td>{escape(str(item.get('Total encontrados', 0)))}</td>"
            f"<td>{escape(str(item.get('Porcentaje aplicado', '')))}%</td>"
            f"<td>{escape(str(item.get('Total reemplazados', 0)))}</td>"
            f"<td>{escape(str(item.get('Nuevo valor', '')))}</td>"
            "</tr>"
        )

    tabla_detalle.append("</tbody></table></div>")

    html.append(
        _render_gc_collapsible(
            "Detalle de reemplazos por cartera y descripción",
            _gc_count_badge(len(detalle), "reglas"),
            "".join(tabla_detalle),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Vista previa de registros reemplazados",
            _gc_count_badge(len(reemplazados_preview)),
            _render_gc_table_from_dicts(reemplazados_preview, 80),
            open_default=False,
        )
    )

    html.append("<h4>Archivos generados</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Tipo</th><th>Nombre</th><th>Ruta</th></tr></thead><tbody>")
    html.append(
        f"<tr><td>Ajuste No contestan</td><td>{escape(str(resultado.get('archivo_salida', '')))}</td><td>{escape(str(resultado.get('ruta_salida', '')))}</td></tr>"
    )
    html.append(
        f"<tr><td>Reporte</td><td>{escape(str(resultado.get('archivo_reporte', '')))}</td><td>{escape(str(resultado.get('ruta_reporte', '')))}</td></tr>"
    )
    html.append("</tbody></table></div>")

    return "".join(html)

