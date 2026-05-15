"""
Blueprint para las fases A-B y D:
- Crear estructura diaria
- Verificar red y carpetas
- Distribuir archivos
"""

import os
from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.services.file_manager import FileManager
from app.controllers.helpers import obtener_log_service

fases_ab_bp = Blueprint("fases_ab", __name__)


@fases_ab_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    res = fm.crear_estructura_diaria(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Estructura creada para {fecha}</div>"
        html += "<table class='dataframe'><tr><th>Carpeta</th><th>Ruta</th></tr>"
        for nombre in ["principal", "Reporte_Imagen", "Causales", "Lotes", "Discador"]:
            if nombre in res["rutas"]:
                ruta = res["rutas"][nombre]
                html += f"<tr><td>{nombre}</td><td style='font-size:0.75rem;'>{ruta}</td></tr>"
        html += "</table>"
    else:
        html = f"<div class='log-line error'>❌ {res['error']}</div>"
    return html


@fases_ab_bp.route("/accion/verificar-red")
def accion_verificar_red():
    fecha = request.args.get("fecha", "202605_06")
    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    res = fm.verificar_red_y_carpetas(fecha)

    if res["success"]:
        session["red_base_activa"] = res.get("red_base_usada")
        red_usada = res.get("red_base_usada", "No especificada")

        html = "<div class='log-line success'>✅ Red verificada correctamente</div>"
        html += f"<p style='margin:5px 0; font-size:0.8rem;'>📍 <b>Unidad de red:</b> {red_usada}</p>"

        rutas = res.get("rutas_validadas", {})
        if "anio" in rutas:
            html += (
                f"<p style='font-size:0.7rem; color:#ccc;'>📂 Año: {rutas['anio']}</p>"
            )
        if "mes" in rutas:
            html += (
                f"<p style='font-size:0.7rem; color:#ccc;'>📅 Mes: {rutas['mes']}</p>"
            )

        html += "<table class='dataframe' style='width:100%;'><tr><th>Subcarpeta</th><th>Ruta</th><th>Archivos encontrados</th></tr>"
        for sub, ruta_sub in rutas.items():
            if sub in ["Causales", "Discador", "Lotes"]:
                archivos = res.get("archivos_encontrados", {}).get(sub, [])
                if archivos:
                    html += f"<tr><td>{sub}</td><td style='font-size:0.6rem;'>{ruta_sub}</td><td>{', '.join(archivos)}</td></tr>"
                else:
                    html += f"<tr><td>{sub}</td><td style='font-size:0.6rem;'>{ruta_sub}</td><td style='color:#ffc107;'>Ninguno</td></tr>"
        html += "</table>"

        for msg in res.get("mensajes", []):
            if "Advertencia" in msg or "anterior" in msg:
                html += f"<p style='color:#ffc107; font-size:0.7rem;'>{msg}</p>"
            else:
                html += f"<p style='font-size:0.7rem; color:#aaa;'>{msg}</p>"
    else:
        red_probada = res.get("red_base_usada", "No disponible")
        html = f"<div class='log-line error'>❌ {res.get('error', 'Error desconocido')}</div>"
        html += f"<p style='font-size:0.7rem;'>Ruta probada: {red_probada}</p>"

    return html


@fases_ab_bp.route("/accion/distribuir")
def accion_distribuir():
    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    red_base = session.get("red_base_activa")
    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)
    if not res_verif["success"]:
        return f"<div class='log-line error'>❌ No se puede distribuir: {res_verif['error']}</div>"

    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    os.makedirs(carpeta_diaria, exist_ok=True)

    res_dist = fm.distribuir_archivos(
        res_verif["rutas_validadas"], carpeta_diaria, res_verif["archivos_encontrados"]
    )

    if res_dist["success"]:
        html = "<div class='log-line success'>✅ Archivos distribuidos correctamente.</div>"
        html += "<table class='dataframe'><tr><th>Origen</th><th>Archivo</th><th>Destino</th></tr>"
        for destino in res_dist["copiados"]:
            nombre = os.path.basename(destino)
            origen = "Red"
            for cat, ruta_red in res_verif["rutas_validadas"].items():
                if cat in ["Causales", "Lotes", "Discador"]:
                    if (
                        os.path.join(carpeta_diaria, nombre) == destino
                        or os.path.join(carpeta_diaria, cat, nombre) == destino
                    ):
                        origen = cat
                        break
            html += f"<tr><td>{origen}</td><td>{nombre}</td><td style='font-size:0.7rem;'>{destino}</td></tr>"
        html += "</table>"
    else:
        html = (
            "<div class='log-line warning'>⚠️ Distribución parcial o con errores.</div>"
        )
        if res_dist.get("errores"):
            html += "<ul style='color:#ffc107; font-size:0.7rem;'>"
            for error in res_dist["errores"]:
                html += f"<li>{error}</li>"
            html += "</ul>"
        if res_dist.get("copiados"):
            html += "<p style='font-size:0.7rem;'>Archivos copiados exitosamente:</p><ul style='font-size:0.7rem;'>"
            for f in res_dist["copiados"]:
                html += f"<li>{os.path.basename(f)}</li>"
            html += "</ul>"
    return html
