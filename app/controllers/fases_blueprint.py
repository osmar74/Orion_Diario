"""
Blueprint para las fases A-B y D:
- Crear estructura diaria
- Verificar red y carpetas
- Distribuir archivos
"""

import os
from html import escape

from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.services.file_manager import FileManager
from app.controllers.helpers import obtener_log_service

fases_ab_bp = Blueprint("fases_ab", __name__)

def _normalizar_fecha_orion(fecha_raw: str) -> str:
    """
    Normaliza fecha ORION a formato YYYYMM_DD.

    Acepta:
    - 202604_29
    - 20260429
    - 2026-04-29
    """
    fecha = str(fecha_raw or "").strip()

    if "_" in fecha and len(fecha.replace("_", "")) == 8:
        return fecha

    digitos = "".join(ch for ch in fecha if ch.isdigit())

    if len(digitos) == 8:
        return f"{digitos[:6]}_{digitos[6:8]}"

    return fecha

@fases_ab_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_12"))
    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    res = fm.crear_estructura_diaria(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Estructura creada para {fecha}</div>"
        html += f"""<div class='log-line info'>
                        📌 DATA_DIR activo: {DATA_DIR}
                    </div>
                    """
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
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_06"))
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


def _destino_categoria_orion(carpeta_diaria: str, categoria: str) -> str:
    """
    Devuelve carpeta destino por categoría ORION.
    """
    destinos = {
        "Causales": os.path.join(carpeta_diaria, "Causales"),
        "Lotes": os.path.join(carpeta_diaria, "Lotes"),
        "Discador": os.path.join(carpeta_diaria, "Discador"),
    }

    return destinos.get(categoria, carpeta_diaria)


def _generar_html_preparar_distribucion_orion(
    fecha: str,
    rutas_validadas: dict,
    archivos_encontrados: dict,
    carpeta_diaria: str,
) -> str:
    """
    Muestra archivos encontrados para que el usuario seleccione cuáles copiar.
    """
    html = f"""
    <div class='log-line success'>
        ✅ Archivos ubicados correctamente para {escape(fecha)}.
    </div>
    <div class='log-line info'>
        Seleccione qué archivos desea copiar hacia la carpeta diaria ORION.
    </div>
    <div class='log-line info'>
        📁 Carpeta diaria destino: <code>{escape(carpeta_diaria)}</code>
    </div>
    """

    categorias = ["Causales", "Lotes", "Discador"]

    total_archivos = 0

    for categoria in categorias:
        ruta_origen = rutas_validadas.get(categoria, "")
        archivos = archivos_encontrados.get(categoria, []) or []
        destino_dir = _destino_categoria_orion(carpeta_diaria, categoria)

        html += f"""
        <details class='panel-monitor' open style='margin-top:10px;'>
            <summary>
                <span class='panel-icon'>📁</span>
                {escape(categoria)} - {len(archivos)} archivo(s)
            </summary>
            <div class='panel-body'>
                <div class='log-line info'>
                    <b>Ruta origen:</b> <code>{escape(str(ruta_origen))}</code>
                </div>
                <div class='log-line info'>
                    <b>Ruta destino:</b> <code>{escape(str(destino_dir))}</code>
                </div>
        """

        if not archivos:
            html += """
                <div class='log-line warning'>
                    ⚠️ No se encontraron archivos para esta categoría.
                </div>
            </div>
        </details>
            """
            continue

        html += """
                <table class='dataframe' style='width:100%; margin-top:8px;'>
                    <tr>
                        <th>Copiar</th>
                        <th>Archivo</th>
                        <th>Ruta origen</th>
                        <th>Ruta destino</th>
                        <th>Estado destino</th>
                    </tr>
        """

        for archivo in archivos:
            total_archivos += 1

            ruta_destino = os.path.join(destino_dir, archivo)
            existe_destino = os.path.isfile(ruta_destino)

            if existe_destino:
                estado_destino = "⚠️ Ya existe, se reemplazará"
                color_estado = "#ffc107"
            else:
                estado_destino = "✅ Nuevo"
                color_estado = "#28a745"

            html += f"""
                    <tr>
                        <td style='text-align:center;'>
                            <input
                                type='checkbox'
                                class='chk-distribucion-orion'
                                checked
                                data-categoria='{escape(categoria, quote=True)}'
                                data-archivo='{escape(str(archivo), quote=True)}'
                            >
                        </td>
                        <td><b>{escape(str(archivo))}</b></td>
                        <td style='font-size:0.7rem; word-break:break-all;'>
                            {escape(str(ruta_origen))}
                        </td>
                        <td style='font-size:0.7rem; word-break:break-all;'>
                            {escape(str(ruta_destino))}
                        </td>
                        <td style='font-weight:bold; color:{color_estado};'>
                            {estado_destino}
                        </td>
                    </tr>
            """

        html += """
                </table>
            </div>
        </details>
        """

    if total_archivos == 0:
        html += """
        <div class='log-line error'>
            ❌ No hay archivos disponibles para copiar.
        </div>
        """
    else:
        html += f"""
        <div style='margin-top:12px;'>
            <button type='button' onclick='copiarDistribucionSeleccionada(this)'>
                Copiar seleccionados
            </button>
        </div>
        <div class='log-line warning' style='margin-top:8px;'>
            ⚠️ No se copiará nada hasta presionar <b>Copiar seleccionados</b>.
        </div>
        """

    return html


@fases_ab_bp.route("/accion/distribuir")
def accion_distribuir():
    """
    Fase D - Preparar distribución.

    Ya no copia inmediatamente.
    Primero muestra los archivos encontrados para que el usuario seleccione cuáles copiar.
    """
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_12"))

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    red_base = session.get("red_base_activa")

    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)

    if not res_verif["success"]:
        return f"<div class='log-line error'>❌ No se puede preparar distribución: {escape(res_verif['error'])}</div>"

    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    os.makedirs(carpeta_diaria, exist_ok=True)

    session["orion_distribucion_fecha"] = fecha

    return _generar_html_preparar_distribucion_orion(
        fecha=fecha,
        rutas_validadas=res_verif["rutas_validadas"],
        archivos_encontrados=res_verif["archivos_encontrados"],
        carpeta_diaria=carpeta_diaria,
    )
    
@fases_ab_bp.route("/accion/distribuir-seleccionados", methods=["POST"])
def accion_distribuir_seleccionados():
    """
    Copia solo los archivos seleccionados por el usuario en Fase D.
    """
    data = request.get_json(silent=True) or {}

    fecha = _normalizar_fecha_orion(
        data.get("fecha") or session.get("orion_distribucion_fecha") or "202605_12"
    )

    seleccionados = data.get("seleccionados", [])

    if not seleccionados:
        return "<div class='log-line error'>❌ No seleccionó archivos para copiar.</div>"

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    red_base = session.get("red_base_activa")

    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)

    if not res_verif["success"]:
        return f"<div class='log-line error'>❌ No se puede copiar: {escape(res_verif['error'])}</div>"

    categorias_validas = {"Causales", "Lotes", "Discador"}

    archivos_filtrados = {
        "Causales": [],
        "Lotes": [],
        "Discador": [],
    }

    archivos_disponibles = res_verif.get("archivos_encontrados", {})

    for item in seleccionados:
        categoria = str(item.get("categoria", "")).strip()
        archivo = str(item.get("archivo", "")).strip()

        if categoria not in categorias_validas or not archivo:
            continue

        disponibles_categoria = archivos_disponibles.get(categoria, []) or []

        if archivo not in disponibles_categoria:
            continue

        archivos_filtrados[categoria].append(archivo)

    if not any(archivos_filtrados.values()):
        return """
        <div class='log-line error'>
            ❌ Ninguno de los archivos seleccionados está disponible en la ruta origen.
        </div>
        """

    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    os.makedirs(carpeta_diaria, exist_ok=True)

    res_dist = fm.distribuir_archivos(
        res_verif["rutas_validadas"],
        carpeta_diaria,
        archivos_filtrados,
    )

    if res_dist["success"]:
        html = "<div class='log-line success'>✅ Archivos seleccionados copiados correctamente.</div>"
    else:
        html = "<div class='log-line warning'>⚠️ Distribución parcial o con errores.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th>Categoría</th>
            <th>Archivo</th>
            <th>Destino</th>
        </tr>
    """

    for item in res_dist.get("copiados_detalle", []):
        html += f"""
        <tr>
            <td>{escape(str(item.get("categoria", "")))}</td>
            <td><b>{escape(str(item.get("archivo", "")))}</b></td>
            <td style='font-size:0.7rem; word-break:break-all;'>
                {escape(str(item.get("destino", "")))}
            </td>
        </tr>
        """

    html += "</table>"

    if res_dist.get("errores"):
        html += "<ul style='color:#ffc107; font-size:0.75rem;'>"

        for error in res_dist["errores"]:
            html += f"<li>{escape(str(error))}</li>"

        html += "</ul>"

    return html

