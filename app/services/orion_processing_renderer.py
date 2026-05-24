"""
Renderer temporal para ORION Fase F.

Responsabilidad:
- Generar HTML de resultados visuales.
- Mantener los controladores más pequeños.
- Preparar el camino para mover luego este HTML a templates/partials.
"""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd


def render_log_error(mensaje: str) -> str:
    return f"<div class='log-line error'>❌ {escape(str(mensaje))}</div>"


def render_discador_not_found() -> str:
    return """
    <div class='log-line error'>
        ❌ No se encontró archivo Discador.
    </div>
    <div class='log-line warning'>
        Se buscó en la carpeta diaria y en la subcarpeta Discador.
    </div>
    """


def render_discador_campaign_debug(ruta_disc: str) -> str:
    """
    Genera detalle opcional de valores únicos de Campaña.
    """
    try:
        df_temp = pd.read_excel(ruta_disc, dtype=str)

        if "Campaña" not in df_temp.columns:
            return ""

        unicos = df_temp["Campaña"].dropna().unique()[:10]

        return (
            "<details style='margin-bottom:8px;'>"
            "<summary style='font-size:0.75rem; color:#ffc107; cursor:pointer;'>"
            "🔍 Valores únicos de Campaña</summary>"
            f"<ul style='font-size:0.7rem; color:#ffc107;'>"
            f"{''.join(f'<li>{escape(str(v))}</li>' for v in unicos)}"
            "</ul></details>"
        )

    except Exception:
        return ""


def render_discador_result(
    res: dict[str, Any],
    ruta_disc: str,
    total_esperado: int,
    debug_html: str = "",
) -> str:
    """
    HTML resultado Procesar Discador.
    """
    if not res.get("success"):
        return debug_html + f"<div class='log-line error'>❌ {escape(str(res.get('mensaje', 'Error desconocido')))}</div>"

    html = (
        debug_html
        + "<div class='log-line success'>✅ Discador procesado correctamente.</div>"
    )

    html += f"""
    <div class='log-line info'>
        📌 Discador usado:
        <code>{escape(str(ruta_disc))}</code>
    </div>
    """

    if "pasos_filtrado" in res:
        pasos = res["pasos_filtrado"]
        html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Proceso de filtrado:</p>"
        html += "<table class='dataframe' style='width:100%;'><tr><th>Paso</th><th>Cantidad</th></tr>"
        html += f"<tr><td>Registros originales</td><td>{escape(str(pasos.get('original', 0)))}</td></tr>"
        html += f"<tr><td>Tras filtro Campaña</td><td>{escape(str(pasos.get('despues_campania', 0)))}</td></tr>"
        html += f"<tr><td>Tras filtro Estado (válidos)</td><td>{escape(str(pasos.get('valido', 0)))}</td></tr>"
        html += "</table>"

    if res.get("reemplazos"):
        html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>🔄 Reemplazos de '-' por NULL:</p>"
        html += "<table class='dataframe' style='width:100%;'><tr><th>Columna</th><th>Cantidad</th></tr>"

        for col, cantidad in res["reemplazos"].items():
            html += f"<tr><td>{escape(str(col))}</td><td>{escape(str(cantidad))}</td></tr>"

        html += "</table>"

    html += "<table class='dataframe' style='width:100%;'><tr><th>Indicador</th><th>Valor</th></tr>"
    html += f"<tr><td>Total esperado (OCR)</td><td>{escape(str(res.get('total_esperado', total_esperado)))}</td></tr>"
    html += f"<tr><td>Total válidos</td><td>{escape(str(res.get('total_validos', 0)))}</td></tr>"
    html += f"<tr><td>Total no válidos</td><td>{escape(str(res.get('total_no_validos', 0)))}</td></tr>"
    html += f"<tr><td>Cuadre</td><td>{'✅ Correcto' if res.get('cuadre_ok') else '❌ No coincide'}</td></tr>"
    html += "</table>"

    html += f"<p style='font-size:0.75rem; color:#aaa;'>{escape(str(res.get('mensaje', '')))}</p>"

    html += (
        '<div id="discador-data" style="display:none;" '
        f'data-valido="{escape(str(res.get("total_validos", 0)))}" '
        f'data-esperado="{escape(str(total_esperado))}" '
        f'data-cuadre="{escape(str(res.get("cuadre_ok", False)))}">'
        "</div>"
    )

    ruta_limpio = res.get("ruta_limpio")

    if ruta_limpio:
        try:
            df = pd.read_excel(ruta_limpio)
            html += (
                "<details style='margin-top:8px;'>"
                "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                "📋 Vista previa (primeras 5 filas)</summary>"
                + df.head(5).to_html(index=False, classes="dataframe")
                + "</details>"
            )
        except Exception:
            pass

    return html


def render_causales_result(res: dict[str, Any]) -> str:
    """
    HTML resultado Procesar Causales.
    """
    if not res.get("success"):
        mensajes = res.get("mensajes", [])
        return f"<div class='log-line error'>❌ {escape(' '.join(map(str, mensajes)))}</div>"

    html = "<div class='log-line success'>✅ Causales procesados correctamente. ({} archivos)</div>".format(
        escape(str(res.get("total_archivos", 0)))
    )

    if res.get("estadisticas_archivos"):
        html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
        html += (
            "<table class='dataframe' style='width:100%;'>"
            "<tr><th>Archivo</th><th>Original</th><th>Tras Campaña</th><th>Tras Evento</th><th>Normalizados</th></tr>"
        )

        for est in res["estadisticas_archivos"]:
            html += (
                f"<tr><td>{escape(str(est.get('archivo', '')))}</td>"
                f"<td>{escape(str(est.get('original', 0)))}</td>"
                f"<td>{escape(str(est.get('tras_campania', 0)))}</td>"
                f"<td>{escape(str(est.get('tras_evento', 0)))}</td>"
                f"<td>{escape(str(est.get('normalizaciones', 0)))}</td></tr>"
            )

        total_orig = sum(e.get("original", 0) for e in res["estadisticas_archivos"])
        total_camp = sum(e.get("tras_campania", 0) for e in res["estadisticas_archivos"])
        total_event = sum(e.get("tras_evento", 0) for e in res["estadisticas_archivos"])
        total_norm = sum(e.get("normalizaciones", 0) for e in res["estadisticas_archivos"])

        html += (
            f"<tr style='font-weight:bold;'><td>TOTAL</td><td>{total_orig}</td>"
            f"<td>{total_camp}</td><td>{total_event}</td><td>{total_norm}</td></tr>"
        )
        html += "</table>"

    html += (
        "<table class='dataframe' style='width:100%; margin-top:8px;'>"
        "<tr><th>Indicador</th><th>Valor</th></tr>"
    )
    html += f"<tr><td>Total archivos procesados</td><td>{escape(str(res.get('total_archivos', 0)))}</td></tr>"
    html += f"<tr><td>Total filas consolidadas</td><td>{escape(str(res.get('total_filas', 0)))}</td></tr>"
    html += "</table>"

    if res.get("preview_html"):
        html += (
            "<details style='margin-top:8px;'>"
            "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
            "📋 Vista previa (primeras 10 filas)</summary>"
            + str(res["preview_html"])
            + "</details>"
        )

    return html


def _render_reporte_nombre_lote_orion(reporte_lotes: list[dict[str, Any]]) -> str:
    """
    Tabla visual de asignación Nombre_Lote desde Discador[Lote].
    """
    if not reporte_lotes:
        return """
        <div class='log-line warning'>
            ⚠️ No se generó reporte de asignación Nombre_Lote.
        </div>
        """

    html = """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='6' style='background:#1e3a5f; color:#fff;'>
                Asignación Nombre_Lote desde Discador[Lote]
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Archivo lote</th>
            <th>Nombre base</th>
            <th>Nombre_Lote asignado</th>
            <th>Similitud</th>
            <th>Estado</th>
        </tr>
    """

    for idx, fila in enumerate(reporte_lotes, start=1):
        estado = str(fila.get("estado", ""))

        if estado == "OK":
            color = "#28a745"
            texto_estado = "✅ OK"
        elif estado == "REVISAR":
            color = "#ffc107"
            texto_estado = "⚠️ Revisar"
        else:
            color = "#dc3545"
            texto_estado = "❌ Sin coincidencia confiable"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(fila.get("archivo_lote", "")))}</td>
            <td>{escape(str(fila.get("nombre_base", "")))}</td>
            <td><b>{escape(str(fila.get("nombre_lote_asignado", "")))}</b></td>
            <td>{escape(str(fila.get("similitud", "")))}</td>
            <td style='font-weight:bold; color:{color};'>{texto_estado}</td>
        </tr>
        """

    html += "</table>"

    return html


def render_lotes_result(res: dict[str, Any], ruta_disc: str | None) -> str:
    """
    HTML resultado Procesar Lotes.
    """
    if not res.get("success"):
        mensajes = res.get("mensajes", [])
        return f"<div class='log-line error'>❌ {escape(' '.join(map(str, mensajes)))}</div>"

    html = "<div class='log-line success'>✅ Lotes procesados correctamente.</div>"

    if ruta_disc:
        html += f"""
        <div class='log-line info'>
            📌 Discador usado para Nombre_Lote:
            <code>{escape(str(ruta_disc))}</code>
        </div>
        """
    else:
        html += """
        <div class='log-line warning'>
            ⚠️ No se encontró archivo Discador consolidado/limpio. La asignación Nombre_Lote no pudo compararse contra Discador[Lote].
        </div>
        """

    html += f"""
    <div class='log-line info'>
        📊 Valores únicos encontrados en Discador[Lote]:
        <b>{escape(str(len(res.get("valores_lote_discador", []))))}</b>
    </div>
    """

    if res.get("estadisticas_archivos"):
        html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
        html += (
            "<table class='dataframe' style='width:100%;'>"
            "<tr><th>Archivo</th><th>Pivoteo</th><th>Filas orig.</th>"
            "<th>Filas tras piv.</th><th>Cod.Cliente texto</th><th>Filas Cuenta con dato</th></tr>"
        )

        for est in res["estadisticas_archivos"]:
            pivoteo = "Sí" if est.get("pivot_aplicado") else "No"
            cod_cliente = "Sí" if est.get("codigo_cliente_forzado") else "No"
            cuenta_dato = est.get("cuenta_filas_con_dato", 0)

            html += (
                f"<tr><td>{escape(str(est.get('archivo', '')))}</td>"
                f"<td>{pivoteo}</td>"
                f"<td>{escape(str(est.get('filas_originales', 0)))}</td>"
                f"<td>{escape(str(est.get('filas_despues_pivot', 0)))}</td>"
                f"<td>{cod_cliente}</td>"
                f"<td>{escape(str(cuenta_dato))}</td></tr>"
            )

        html += "</table>"

    if res.get("reporte_lotes"):
        html += _render_reporte_nombre_lote_orion(res.get("reporte_lotes", []))

    html += (
        "<table class='dataframe' style='width:100%; margin-top:8px;'>"
        "<tr><th>Indicador</th><th>Valor</th></tr>"
    )
    html += f"<tr><td>Total filas consolidadas</td><td>{escape(str(res.get('total_filas', 0)))}</td></tr>"

    if res.get("validacion_cruzada"):
        estado = "✅ OK" if res["validacion_cruzada"].get("ok") else "❌ Fallo"
        html += f"<tr><td>Validación cruzada</td><td>{estado}</td></tr>"

    html += "</table>"

    for msg in res.get("mensajes", []):
        html += f"<p style='font-size:0.7rem; color:#aaa; margin:3px 0;'>{escape(str(msg))}</p>"

    if res.get("preview_html"):
        html += (
            "<details style='margin-top:8px;'>"
            "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
            "📋 Vista previa (primeras 10 filas)</summary>"
            + str(res["preview_html"])
            + "</details>"
        )

    return html


def render_comparacion_lotes_result(res: dict[str, Any]) -> str:
    """
    HTML resultado Comparar Lotes.
    """
    rutas = res.get("rutas", {})
    faltantes = res.get("faltantes", [])
    errores = res.get("errores", [])
    comparacion = res.get("comparacion", [])

    html = """
    <p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>
        📁 Archivos limpios generados:
    </p>
    """

    html += """
    <table class='dataframe' style='width:100%;'>
        <tr>
            <th>Tipo</th>
            <th>Ruta</th>
        </tr>
    """

    html += f"""
        <tr>
            <td>Discador Consolidado</td>
            <td>{escape(str(rutas.get("discador") or "No encontrado"))}</td>
        </tr>
        <tr>
            <td>Causales Consolidado</td>
            <td>{escape(str(rutas.get("causales") or "No encontrado"))}</td>
        </tr>
        <tr>
            <td>Lotes Consolidado</td>
            <td>{escape(str(rutas.get("lotes") or "No encontrado"))}</td>
        </tr>
    """

    html += "</table>"

    if faltantes:
        html += (
            "<p style='color:#ffc107; font-size:0.75rem;'>"
            "⚠️ Falta(n) archivo(s) consolidado(s) de: "
            + escape(", ".join(faltantes))
            + ". Ejecute primero los procesamientos correspondientes.</p>"
        )

    if errores:
        for error in errores:
            html += f"""
            <p style='color:#dc3545; font-size:0.75rem;'>
                ❌ {escape(str(error))}
            </p>
            """

    if comparacion:
        html += """
        <p style='font-size:0.75rem; color:#ccc; margin:10px 0 5px 0;'>
            🔍 Comparación de lotes:
        </p>
        <table class='dataframe' style='width:100%;'>
            <tr>
                <th>Lote</th>
                <th>En Discador</th>
                <th>En Lotes</th>
            </tr>
        """

        for fila in comparacion:
            en_discador = "✅" if fila.get("en_discador_bool") else "❌"
            en_lotes = "✅" if fila.get("en_lotes_bool") else "❌"

            html += f"""
            <tr>
                <td>{escape(str(fila.get("Lote", "")))}</td>
                <td>{en_discador}</td>
                <td>{en_lotes}</td>
            </tr>
            """

        html += "</table>"

        if res.get("match_ok"):
            html += """
            <p style='color:#28a745; font-size:0.8rem;'>
                ✅ Todos los lotes coinciden.
            </p>
            """
        else:
            faltan_en_discador = res.get("faltan_en_discador", [])
            faltan_en_lotes = res.get("faltan_en_lotes", [])

            if faltan_en_discador:
                html += (
                    "<p style='color:#ffc107; font-size:0.8rem;'>"
                    "⚠️ Lotes en archivo Lotes que no están en Discador: "
                    + escape(", ".join(faltan_en_discador))
                    + "</p>"
                )

            if faltan_en_lotes:
                html += (
                    "<p style='color:#ffc107; font-size:0.8rem;'>"
                    "⚠️ Lotes en Discador que no están en archivo Lotes: "
                    + escape(", ".join(faltan_en_lotes))
                    + "</p>"
                )

    ruta_resumen = res.get("ruta_resumen")

    if ruta_resumen:
        html += (
            f"<p style='color:#28a745; font-size:0.8rem; margin-top:10px;'>"
            f"📊 Resumen Excel generado: {escape(str(ruta_resumen))}</p>"
        )

    return html