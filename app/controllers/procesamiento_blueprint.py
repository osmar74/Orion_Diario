"""
Blueprint para la fase F: Procesamiento de Discador, Causales, Lotes y Comparación.
"""
import os
import pandas as pd
from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.services.discador_processor import DiscadorProcessor
from app.services.causales_processor import CausalesProcessor
from app.services.lotes_processor import LotesProcessor
from app.controllers.helpers import obtener_log_service

proc_bp = Blueprint('procesamiento', __name__)


@proc_bp.route('/accion/procesar-discador')
def accion_procesar_discador():
    fecha = request.args.get('fecha', '202605_12')
    total_esperado = session.get('totales_orion')
    if total_esperado is None:
        total_esperado = request.args.get('total', 0, type=int)

    disc = DiscadorProcessor(log_service=obtener_log_service())
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    archivos = [f for f in os.listdir(carpeta_diaria) if f.lower().endswith('.xlsx') and 'discador' in f.lower()]
    if not archivos:
        return "<div class='log-line error'>❌ No se encontró archivo Discador en la carpeta diaria.</div>"
    ruta_disc = os.path.join(carpeta_diaria, archivos[0])

    # Debug de valores únicos de Campaña
    debug_html = ''
    try:
        df_temp = pd.read_excel(ruta_disc, dtype=str)
        if 'Campaña' in df_temp.columns:
            unicos = df_temp['Campaña'].dropna().unique()[:10]
            debug_html = (
                "<details style='margin-bottom:8px;'>"
                "<summary style='font-size:0.75rem; color:#ffc107; cursor:pointer;'>"
                "🔍 Valores únicos de Campaña</summary>"
                f"<ul style='font-size:0.7rem; color:#ffc107;'>{''.join(f'<li>{v}</li>' for v in unicos)}</ul></details>"
            )
    except Exception:
        pass

    res = disc.procesar(ruta_disc, total_esperado, carpeta_diaria)

    if res['success']:
        html = debug_html + "<div class='log-line success'>✅ Discador procesado correctamente.</div>"
        if 'pasos_filtrado' in res:
            pasos = res['pasos_filtrado']
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Proceso de filtrado:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Paso</th><th>Cantidad</th></tr>"
            html += f"<tr><td>Registros originales</td><td>{pasos['original']}</td></tr>"
            html += f"<tr><td>Tras filtro Campaña</td><td>{pasos['despues_campania']}</td></tr>"
            html += f"<tr><td>Tras filtro Estado (válidos)</td><td>{pasos['valido']}</td></tr>"
            html += "</table>"
        if 'reemplazos' in res and res['reemplazos']:
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>🔄 Reemplazos de '-' por NULL:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Columna</th><th>Cantidad</th></tr>"
            for col, cantidad in res['reemplazos'].items():
                html += f"<tr><td>{col}</td><td>{cantidad}</td></tr>"
            html += "</table>"
        html += "<table class='dataframe' style='width:100%;'><tr><th>Indicador</th><th>Valor</th></tr>"
        html += f"<tr><td>Total esperado (OCR)</td><td>{res['total_esperado']}</td></tr>"
        html += f"<tr><td>Total válidos</td><td>{res['total_validos']}</td></tr>"
        html += f"<tr><td>Total no válidos</td><td>{res['total_no_validos']}</td></tr>"
        html += f"<tr><td>Cuadre</td><td>{'✅ Correcto' if res['cuadre_ok'] else '❌ No coincide'}</td></tr>"
        html += "</table>"
        html += f"<p style='font-size:0.75rem; color:#aaa;'>{res['mensaje']}</p>"
        if res['ruta_limpio']:
            try:
                df = pd.read_excel(res['ruta_limpio'])
                html += (
                    "<details style='margin-top:8px;'>"
                    "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                    "📋 Vista previa (primeras 5 filas)</summary>"
                    + df.head(5).to_html(index=False, classes='dataframe') +
                    "</details>"
                )
            except Exception:
                pass
    else:
        html = debug_html + f"<div class='log-line error'>❌ {res['mensaje']}</div>"
    return html


@proc_bp.route('/accion/procesar-causales')
def accion_procesar_causales():
    fecha = request.args.get('fecha', '202605_12')
    caus = CausalesProcessor(log_service=obtener_log_service())
    carpeta_causales = os.path.join(DATA_DIR, f"orion_{fecha}", "Causales")
    if not os.path.isdir(carpeta_causales):
        return "<div class='log-line error'>❌ No existe la carpeta Causales.</div>"

    res = caus.procesar_carpeta_causales(carpeta_causales, carpeta_causales)
    if res['success']:
        html = "<div class='log-line success'>✅ Causales procesados correctamente. ({} archivos)</div>".format(
            res['total_archivos'])
        if res.get('estadisticas_archivos'):
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
            html += (
                "<table class='dataframe' style='width:100%;'>"
                "<tr><th>Archivo</th><th>Original</th><th>Tras Campaña</th><th>Tras Evento</th><th>Normalizados</th></tr>"
            )
            for est in res['estadisticas_archivos']:
                html += (
                    f"<tr><td>{est['archivo']}</td><td>{est['original']}</td>"
                    f"<td>{est['tras_campania']}</td><td>{est['tras_evento']}</td>"
                    f"<td>{est['normalizaciones']}</td></tr>"
                )
            total_orig = sum(e['original'] for e in res['estadisticas_archivos'])
            total_camp = sum(e['tras_campania'] for e in res['estadisticas_archivos'])
            total_event = sum(e['tras_evento'] for e in res['estadisticas_archivos'])
            total_norm = sum(e['normalizaciones'] for e in res['estadisticas_archivos'])
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
        html += f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        html += "</table>"
        if res.get('preview_html'):
            html += (
                "<details style='margin-top:8px;'>"
                "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                "📋 Vista previa (primeras 10 filas)</summary>"
                + res['preview_html'] +
                "</details>"
            )
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
    return html


@proc_bp.route('/accion/procesar-lotes')
def accion_procesar_lotes():
    fecha = request.args.get('fecha', '202605_12')
    lotes = LotesProcessor(log_service=obtener_log_service())
    carpeta_lotes = os.path.join(DATA_DIR, f"orion_{fecha}", "Lotes")
    if not os.path.isdir(carpeta_lotes):
        return "<div class='log-line error'>❌ No existe la carpeta Lotes.</div>"

    ruta_disc = os.path.join(DATA_DIR, f"orion_{fecha}", "discador_ejemplo_limpio.xlsx")
    res = lotes.procesar_carpeta_lotes(carpeta_lotes, fecha,
                                       ruta_disc if os.path.isfile(ruta_disc) else None)

    if res['success']:
        html = "<div class='log-line success'>✅ Lotes procesados correctamente.</div>"
        if res.get('estadisticas_archivos'):
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
            html += (
                "<table class='dataframe' style='width:100%;'>"
                "<tr><th>Archivo</th><th>Pivoteo</th><th>Filas orig.</th>"
                "<th>Filas tras piv.</th><th>Cod.Cliente texto</th><th>Filas Cuenta con dato</th></tr>"
            )
            for est in res['estadisticas_archivos']:
                pivoteo = 'Sí' if est['pivot_aplicado'] else 'No'
                cod_cliente = 'Sí' if est.get('codigo_cliente_forzado') else 'No'
                cuenta_dato = est.get('cuenta_filas_con_dato', 0)
                html += (
                    f"<tr><td>{est['archivo']}</td><td>{pivoteo}</td>"
                    f"<td>{est['filas_originales']}</td><td>{est['filas_despues_pivot']}</td>"
                    f"<td>{cod_cliente}</td><td>{cuenta_dato}</td></tr>"
                )
            html += "</table>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:8px;'>"
            "<tr><th>Indicador</th><th>Valor</th></tr>"
        )
        html += f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        if res.get('validacion_cruzada'):
            estado = '✅ OK' if res['validacion_cruzada']['ok'] else '❌ Fallo'
            html += f"<tr><td>Validación cruzada</td><td>{estado}</td></tr>"
        html += "</table>"
        for msg in res.get('mensajes', []):
            html += f"<p style='font-size:0.7rem; color:#aaa; margin:3px 0;'>{msg}</p>"
        if res.get('preview_html'):
            html += (
                "<details style='margin-top:8px;'>"
                "<summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>"
                "📋 Vista previa (primeras 10 filas)</summary>"
                + res['preview_html'] +
                "</details>"
            )
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
    return html


@proc_bp.route('/accion/comparar-lotes')
def accion_comparar_lotes():
    fecha = request.args.get('fecha', '202605_12')
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    archivos_disc = [f for f in os.listdir(carpeta_diaria)
                     if f.lower().endswith('.xlsx') and 'discador' in f.lower()
                     and 'consolidado' in f.lower()]
    ruta_disc = os.path.join(carpeta_diaria, archivos_disc[0]) if archivos_disc else None

    carpeta_lotes = os.path.join(carpeta_diaria, 'Lotes')
    archivos_lotes = [f for f in os.listdir(carpeta_lotes)
                      if f.lower().startswith('lote_consolidado') and f.endswith('.xlsx')] \
        if os.path.isdir(carpeta_lotes) else []
    ruta_lotes = os.path.join(carpeta_lotes, archivos_lotes[0]) if archivos_lotes else None

    carpeta_causales = os.path.join(carpeta_diaria, 'Causales')
    archivos_caus = [f for f in os.listdir(carpeta_causales)
                     if f.lower().startswith('causales_consolidado') and f.endswith('.xlsx')] \
        if os.path.isdir(carpeta_causales) else []
    ruta_caus = os.path.join(carpeta_causales, archivos_caus[0]) if archivos_caus else None

    html = "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📁 Archivos limpios generados:</p>"
    html += "<table class='dataframe' style='width:100%;'><tr><th>Tipo</th><th>Ruta</th></tr>"
    html += f"<tr><td>Discador Consolidado</td><td>{ruta_disc or 'No encontrado'}</td></tr>"
    html += f"<tr><td>Causales Consolidado</td><td>{ruta_caus or 'No encontrado'}</td></tr>"
    html += f"<tr><td>Lotes Consolidado</td><td>{ruta_lotes or 'No encontrado'}</td></tr>"
    html += "</table>"

    if not ruta_disc or not ruta_caus or not ruta_lotes:
        faltantes = []
        if not ruta_disc:
            faltantes.append("Discador")
        if not ruta_caus:
            faltantes.append("Causales")
        if not ruta_lotes:
            faltantes.append("Lotes")
        html += (
            "<p style='color:#ffc107; font-size:0.75rem;'>⚠️ Falta(n) archivo(s) consolidado(s) de: "
            + ', '.join(faltantes)
            + ". Ejecute primero los procesamientos correspondientes.</p>"
        )

    datos_comparacion = []
    if ruta_disc and ruta_lotes:
        try:
            df_disc = pd.read_excel(ruta_disc, dtype=str)
            df_lotes = pd.read_excel(ruta_lotes, dtype=str)
            if 'Lote' in df_disc.columns and 'Nombre_Lote' in df_lotes.columns:
                lotes_disc = set(df_disc['Lote'].dropna().unique())
                lotes_lotes = set(df_lotes['Nombre_Lote'].dropna().unique())
                todos = sorted(lotes_disc.union(lotes_lotes))
                html += (
                    "<p style='font-size:0.75rem; color:#ccc; margin:10px 0 5px 0;'>"
                    "🔍 Comparación de lotes:</p>"
                    "<table class='dataframe' style='width:100%;'>"
                    "<tr><th>Lote</th><th>En Discador</th><th>En Lotes</th></tr>"
                )
                for lote in todos:
                    en_disc = '✅' if lote in lotes_disc else '❌'
                    en_lotes = '✅' if lote in lotes_lotes else '❌'
                    html += f"<tr><td>{lote}</td><td>{en_disc}</td><td>{en_lotes}</td></tr>"
                    datos_comparacion.append({
                        'Lote': lote,
                        'En Discador': 'Sí' if lote in lotes_disc else 'No',
                        'En Lotes': 'Sí' if lote in lotes_lotes else 'No'
                    })
                html += "</table>"
                faltan_en_disc = lotes_lotes - lotes_disc
                faltan_en_lotes = lotes_disc - lotes_lotes
                if not faltan_en_disc and not faltan_en_lotes:
                    html += "<p style='color:#28a745; font-size:0.8rem;'>✅ Todos los lotes coinciden.</p>"
                else:
                    if faltan_en_disc:
                        html += (
                            "<p style='color:#ffc107; font-size:0.8rem;'>⚠️ Lotes en archivo Lotes que no están en Discador: "
                            + ', '.join(faltan_en_disc) + "</p>"
                        )
                    if faltan_en_lotes:
                        html += (
                            "<p style='color:#ffc107; font-size:0.8rem;'>⚠️ Lotes en Discador que no están en archivo Lotes: "
                            + ', '.join(faltan_en_lotes) + "</p>"
                        )
        except Exception as e:
            html += f"<p style='color:#dc3545;'>❌ Error al comparar: {e}</p>"

    # Generar Excel de resumen
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        wb = Workbook()
        ws = wb.active
        ws.title = "Comparación"
        ws.append(["Lote", "En Discador", "En Lotes"])
        for fila in datos_comparacion:
            ws.append([fila['Lote'], fila['En Discador'], fila['En Lotes']])
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        for col in range(1, 4):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        fecha_archivo = fecha.replace('_', '')[4:]
        ruta_resumen = os.path.join(carpeta_diaria, f"Resumen_Comparacion_{fecha_archivo}.xlsx")
        wb.save(ruta_resumen)
        html += (
            f"<p style='color:#28a745; font-size:0.8rem; margin-top:10px;'>"
            f"📊 Resumen Excel generado: {ruta_resumen}</p>"
        )
    except Exception as e:
        html += f"<p style='color:#dc3545;'>❌ Error al generar Excel de resumen: {e}</p>"

    return html