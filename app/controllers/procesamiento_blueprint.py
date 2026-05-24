"""
Blueprint para la fase F: Procesamiento de Discador, Causales, Lotes y Comparación.
"""

import os
import pandas as pd
from html import escape
from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.services.discador_processor import DiscadorProcessor
from app.services.causales_processor import CausalesProcessor
from app.services.lotes_processor import LotesProcessor
from app.controllers.helpers import obtener_log_service
from app.services.daily_paths import ruta_orion
from app.services.orion_file_lookup_service import (
    buscar_archivo_discador_para_lotes,
    buscar_archivo_discador_procesamiento,
)
from app.services.orion_comparison_service import comparar_lotes_orion


proc_bp = Blueprint("procesamiento", __name__)



@proc_bp.route("/accion/procesar-discador")
def accion_procesar_discador():
    fecha = request.args.get("fecha", "202605_12")
    total_esperado = session.get("totales_orion")
    if total_esperado is None:
        total_esperado = request.args.get("total", 0, type=int)

    disc = DiscadorProcessor(log_service=obtener_log_service())
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)

    carpeta_consolidados = os.path.join(carpeta_diaria, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    ruta_disc = buscar_archivo_discador_procesamiento(carpeta_diaria)

    if not ruta_disc:
        return """
        <div class='log-line error'>
            ❌ No se encontró archivo Discador.
        </div>
        <div class='log-line warning'>
            Se buscó en la carpeta diaria y en la subcarpeta Discador.
        </div>
        """

    # Debug de valores únicos de Campaña
    debug_html = ""
    try:
        df_temp = pd.read_excel(ruta_disc, dtype=str)
        if "Campaña" in df_temp.columns:
            unicos = df_temp["Campaña"].dropna().unique()[:10]
            debug_html = (
                "<details style='margin-bottom:8px;'>"
                "<summary style='font-size:0.75rem; color:#ffc107; cursor:pointer;'>"
                "🔍 Valores únicos de Campaña</summary>"
                f"<ul style='font-size:0.7rem; color:#ffc107;'>{''.join(f'<li>{v}</li>' for v in unicos)}</ul></details>"
            )
    except Exception:
        pass

    res = disc.procesar(ruta_disc, total_esperado, carpeta_consolidados)

    if res["success"]:
        html = (
            debug_html
            + "<div class='log-line success'>✅ Discador procesado correctamente.</div>"
        )
        html += f"""
                    <div class='log-line info'>
                        📌 Discador usado:
                        <code>{ruta_disc}</code>
                    </div>
                    """
        if "pasos_filtrado" in res:
            pasos = res["pasos_filtrado"]
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Proceso de filtrado:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Paso</th><th>Cantidad</th></tr>"
            html += (
                f"<tr><td>Registros originales</td><td>{pasos['original']}</td></tr>"
            )
            html += f"<tr><td>Tras filtro Campaña</td><td>{pasos['despues_campania']}</td></tr>"
            html += f"<tr><td>Tras filtro Estado (válidos)</td><td>{pasos['valido']}</td></tr>"
            html += "</table>"
        if "reemplazos" in res and res["reemplazos"]:
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>🔄 Reemplazos de '-' por NULL:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Columna</th><th>Cantidad</th></tr>"
            for col, cantidad in res["reemplazos"].items():
                html += f"<tr><td>{col}</td><td>{cantidad}</td></tr>"
            html += "</table>"
        html += "<table class='dataframe' style='width:100%;'><tr><th>Indicador</th><th>Valor</th></tr>"
        html += (
            f"<tr><td>Total esperado (OCR)</td><td>{res['total_esperado']}</td></tr>"
        )
        html += f"<tr><td>Total válidos</td><td>{res['total_validos']}</td></tr>"
        html += f"<tr><td>Total no válidos</td><td>{res['total_no_validos']}</td></tr>"
        html += f"<tr><td>Cuadre</td><td>{'✅ Correcto' if res['cuadre_ok'] else '❌ No coincide'}</td></tr>"
        html += "</table>"
        html += f"<p style='font-size:0.75rem; color:#aaa;'>{res['mensaje']}</p>"
        html += f'<div id="discador-data" style="display:none;" data-valido="{res.get("total_validos", 0)}" data-esperado="{total_esperado}" data-cuadre="{res.get("cuadre_ok", False)}"></div>'
        if res["ruta_limpio"]:
            try:
                df = pd.read_excel(res["ruta_limpio"])
                html += (
                    "<details style='margin-top:8px;'>"
                    "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                    "📋 Vista previa (primeras 5 filas)</summary>"
                    + df.head(5).to_html(index=False, classes="dataframe")
                    + "</details>"
                )
            except Exception:
                pass
    else:
        html = debug_html + f"<div class='log-line error'>❌ {res['mensaje']}</div>"
        # Insertar datos ocultos para JS (badges)
    
    
    return html


@proc_bp.route("/accion/procesar-causales")
def accion_procesar_causales():
    fecha = request.args.get("fecha", "202605_12")

    caus = CausalesProcessor(log_service=obtener_log_service())
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    carpeta_causales = os.path.join(carpeta_diaria, "Causales")

    carpeta_consolidados = os.path.join(carpeta_diaria, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    if not os.path.isdir(carpeta_causales):
        return "<div class='log-line error'>❌ No existe la carpeta Causales.</div>"

    res = caus.procesar_carpeta_causales(carpeta_causales, carpeta_consolidados)


    if res["success"]:
        html = "<div class='log-line success'>✅ Causales procesados correctamente. ({} archivos)</div>".format(
            res["total_archivos"]
        )
        if res.get("estadisticas_archivos"):
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
            html += (
                "<table class='dataframe' style='width:100%;'>"
                "<tr><th>Archivo</th><th>Original</th><th>Tras Campaña</th><th>Tras Evento</th><th>Normalizados</th></tr>"
            )
            for est in res["estadisticas_archivos"]:
                html += (
                    f"<tr><td>{est['archivo']}</td><td>{est['original']}</td>"
                    f"<td>{est['tras_campania']}</td><td>{est['tras_evento']}</td>"
                    f"<td>{est['normalizaciones']}</td></tr>"
                )
            total_orig = sum(e["original"] for e in res["estadisticas_archivos"])
            total_camp = sum(e["tras_campania"] for e in res["estadisticas_archivos"])
            total_event = sum(e["tras_evento"] for e in res["estadisticas_archivos"])
            total_norm = sum(e["normalizaciones"] for e in res["estadisticas_archivos"])
            html += (
                f"<tr style='font-weight:bold;'><td>TOTAL</td><td>{total_orig}</td>"
                f"<td>{total_camp}</td><td>{total_event}</td><td>{total_norm}</td></tr>"
            )
            html += "</table>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:8px;'>"
            "<tr><th>Indicador</th><th>Valor</th></tr>"
        )
        html += f"<tr><td>Total archivos procesados</td><td>{res['total_archivos']}</td></tr>"
        html += (
            f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        )
        html += "</table>"
        if res.get("preview_html"):
            html += (
                "<details style='margin-top:8px;'>"
                "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                "📋 Vista previa (primeras 10 filas)</summary>"
                + res["preview_html"]
                + "</details>"
            )
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
    return html


def _generar_html_reporte_nombre_lote_orion(reporte_lotes):
    """
    Genera tabla visual de asignación Nombre_Lote desde Discador[Lote].
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




@proc_bp.route("/accion/procesar-lotes")
def accion_procesar_lotes():
    fecha = request.args.get("fecha", "202605_12")

    lotes = LotesProcessor(log_service=obtener_log_service())
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    carpeta_lotes = os.path.join(carpeta_diaria, "Lotes")

    carpeta_consolidados = os.path.join(carpeta_diaria, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    if not os.path.isdir(carpeta_lotes):
        return "<div class='log-line error'>❌ No existe la carpeta Lotes.</div>"

    ruta_disc = buscar_archivo_discador_para_lotes(carpeta_diaria)

    res = lotes.procesar_carpeta_lotes(
        carpeta_lotes,
        fecha,
        ruta_disc,
        carpeta_salida=carpeta_consolidados,
    )

    if res["success"]:
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
            <b>{len(res.get("valores_lote_discador", []))}</b>
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
                pivoteo = "Sí" if est["pivot_aplicado"] else "No"
                cod_cliente = "Sí" if est.get("codigo_cliente_forzado") else "No"
                cuenta_dato = est.get("cuenta_filas_con_dato", 0)
                html += (
                    f"<tr><td>{est['archivo']}</td><td>{pivoteo}</td>"
                    f"<td>{est['filas_originales']}</td><td>{est['filas_despues_pivot']}</td>"
                    f"<td>{cod_cliente}</td><td>{cuenta_dato}</td></tr>"
                )

            html += "</table>"

        if res.get("reporte_lotes"):
            html += _generar_html_reporte_nombre_lote_orion(
                res.get("reporte_lotes", [])
            )

        html += (
            "<table class='dataframe' style='width:100%; margin-top:8px;'>"
            "<tr><th>Indicador</th><th>Valor</th></tr>"
        )


        html += (
            f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        )
        if res.get("validacion_cruzada"):
            estado = "✅ OK" if res["validacion_cruzada"]["ok"] else "❌ Fallo"
            html += f"<tr><td>Validación cruzada</td><td>{estado}</td></tr>"
        html += "</table>"
        for msg in res.get("mensajes", []):
            html += f"<p style='font-size:0.7rem; color:#aaa; margin:3px 0;'>{msg}</p>"
        if res.get("preview_html"):
            html += (
                "<details style='margin-top:8px;'>"
                "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                "📋 Vista previa (primeras 10 filas)</summary>"
                + res["preview_html"]
                + "</details>"
            )
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
    return html


def _generar_html_comparacion_lotes_orion(res: dict) -> str:
    """
    Genera HTML visual de comparación ORION desde resultado estructurado.
    Temporalmente queda aquí hasta mover HTML a partials.
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

@proc_bp.route("/accion/comparar-lotes")
def accion_comparar_lotes():
    fecha = request.args.get("fecha", "202605_12")
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)

    res = comparar_lotes_orion(
        carpeta_orion=carpeta_diaria,
        fecha=fecha,
    )

    return _generar_html_comparacion_lotes_orion(res)

