"""
Blueprint para Gestión Diaria ASTER.

Fase A:
- Captura del total diario por OCR.
- Captura manual del total general.
"""

import base64
import os
import re
import shutil
from typing import Any

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor


aster_bp = Blueprint("aster", __name__)

RUTAS_ASTER_DEFAULT = [
    r"Z:\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"\\10.24.90.118\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"F:\Vencorp\ff\unidad_red_Data\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO"
]


def _crear_html_total_aster(total: int | None, origen: str, previews: list[tuple[str, str]]) -> str:
    """
    Genera respuesta HTML para mostrar el total ASTER detectado o ingresado.
    """
    html = "<div class='ocr-result-container'>"

    html += "<div class='ocr-images'>"

    if previews:
        for nombre, img_b64 in previews:
            html += (
                "<div class='ocr-thumb'>"
                f"<img src='data:image/png;base64,{img_b64}' alt='{nombre}'/>"
                f"<small>{nombre}</small>"
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
            f"<span class='value'>{total}</span>"
            "</div>"
        )
        html += "</div>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:10px;'>"
            "<tr><th colspan='2' style='background:#1e3a5f; color:#fff;'>Detalle de captura</th></tr>"
            f"<tr><td><b>Origen</b></td><td>{origen}</td></tr>"
            f"<tr><td><b>Total general</b></td><td>{total}</td></tr>"
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
        f"data-total='{total if total is not None else ''}'>"
        "</div>"
    )

    return html


def _extraer_total_aster_desde_texto(ocr: OCRProcessor, texto: str) -> int | None:
    """
    Intenta obtener un total ASTER desde texto OCR usando métodos reutilizables.

    Se prueban métodos genéricos porque el formato de WhatsApp puede variar.
    """
    numeros = ocr.extraer_totales_generico(texto)

    if numeros:
        return int(numeros[0])

    for palabra_clave in ["Total general", "Total", "ASTER", "Aster"]:
        numero = ocr.extraer_numero_cercano(texto, palabra_clave)

        if numero:
            return int(numero)

    return None

def _normalizar_fecha_aster(fecha_raw: str) -> str:
    """
    Convierte una fecha recibida en distintos formatos a YYYYMMDD.

    Acepta ejemplos:
    - 20260429
    - 2026-04-29
    - 202604_29
    """
    fecha_limpia = re.sub(r"[^0-9]", "", fecha_raw or "")

    if len(fecha_limpia) < 8:
        raise ValueError(
            "La fecha del proceso debe tener al menos 8 dígitos. Ejemplo: 20260429."
        )

    return fecha_limpia[:8]


def _claves_busqueda_fecha(fecha_yyyymmdd: str) -> list[str]:
    """
    Genera claves de búsqueda para tolerar variaciones de nombre.

    Para 20260429:
    - 20260429
    - 260429
    - 0429
    """
    yyyy = fecha_yyyymmdd[0:4]
    yy = fecha_yyyymmdd[2:4]
    mm = fecha_yyyymmdd[4:6]
    dd = fecha_yyyymmdd[6:8]

    return [
        f"{yyyy}{mm}{dd}",
        f"{yy}{mm}{dd}",
        f"{mm}{dd}",
    ]


def _archivo_aster_corresponde_fecha(nombre_archivo: str, fecha_yyyymmdd: str) -> bool:
    """
    Determina si un archivo .xlsx pertenece a la fecha ASTER.

    Se exige:
    - extensión .xlsx
    - nombre que empiece con After
    - que contenga alguna clave de fecha relevante
    """
    nombre_lower = nombre_archivo.lower()

    if not nombre_lower.endswith(".xlsx"):
        return False

    if not nombre_lower.startswith("after"):
        return False

    solo_digitos = re.sub(r"[^0-9]", "", nombre_archivo)
    claves = _claves_busqueda_fecha(fecha_yyyymmdd)

    return any(clave in solo_digitos for clave in claves)


def _buscar_archivo_aster_en_ruta(ruta_base: str, fecha_yyyymmdd: str) -> str | None:
    """
    Busca el primer archivo ASTER de la fecha indicada dentro de una ruta.
    """
    if not ruta_base or not os.path.isdir(ruta_base):
        return None

    candidatos: list[str] = []

    for nombre in os.listdir(ruta_base):
        ruta_archivo = os.path.join(ruta_base, nombre)

        if not os.path.isfile(ruta_archivo):
            continue

        if _archivo_aster_corresponde_fecha(nombre, fecha_yyyymmdd):
            candidatos.append(ruta_archivo)

    candidatos.sort()

    if candidatos:
        return candidatos[0]

    return None


def _generar_html_archivo_aster(
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
            <td><b>{etiqueta}</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{valor}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-archivo-data' style='display:none;' "
        f"data-fecha='{fecha_yyyymmdd}' "
        f"data-ruta='{ruta_destino}' "
        f"data-archivo='{nombre_archivo}'>"
        "</div>"
    )

    return html


@aster_bp.route("/accion/aster-ocr-subir", methods=["POST"])
def accion_aster_ocr_subir():
    """
    Recibe imágenes de WhatsApp y trata de detectar el total diario ASTER por OCR.
    """
    fecha = request.form.get("fecha", "202605_12")
    archivos = request.files.getlist("imagenes")

    archivos_validos = [
        archivo
        for archivo in archivos
        if (archivo.filename or "").strip()
    ]

    if not archivos_validos:
        return "<div class='log-line error'>❌ No se seleccionó ninguna imagen ASTER.</div>"

    carpeta_destino = os.path.join(
        DATA_DIR,
        f"orion_{fecha}",
        "Reporte_Imagen_ASTER",
    )
    os.makedirs(carpeta_destino, exist_ok=True)

    log_srv = obtener_log_service()
    ocr = OCRProcessor(TESSERACT_PATH, log_service=log_srv)

    total_detectado: int | None = None
    previews: list[tuple[str, str]] = []
    archivos_guardados: list[str] = []

    for idx, archivo in enumerate(archivos_validos):
        nombre_original = archivo.filename or ""

        if not nombre_original.strip():
            continue

        nombre_base = secure_filename(nombre_original)

        if not nombre_base:
            continue

        nombre_unico = f"aster_{idx}_{nombre_base}"
        ruta_guardada = os.path.join(carpeta_destino, nombre_unico)

        archivo.save(ruta_guardada)
        archivos_guardados.append(nombre_unico)

        if len(previews) < 3:
            with open(ruta_guardada, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                previews.append((nombre_unico, img_b64))

        texto = ocr.extraer_texto(ruta_guardada)
        total_archivo = _extraer_total_aster_desde_texto(ocr, texto)

        if total_archivo is not None:
            total_detectado = total_archivo
            break

    session["total_aster"] = total_detectado
    session["ultima_fecha_aster"] = fecha

    html = _crear_html_total_aster(
        total=total_detectado,
        origen="OCR WhatsApp ASTER",
        previews=previews,
    )

    if archivos_guardados:
        html += (
            "<details class='archivos-guardados' style='margin-top:10px;'>"
            f"<summary>📁 Archivos guardados ({len(archivos_guardados)})</summary>"
            "<ul>"
        )

        for nombre in archivos_guardados:
            html += f"<li>{nombre}</li>"

        html += "</ul></details>"

    return html


@aster_bp.route("/accion/aster-consolidar-total", methods=["POST"])
def accion_aster_consolidar_total():
    """
    Guarda manualmente el total diario ASTER en sesión.
    """
    try:
        total_raw = request.form.get("total_aster", "").strip()

        if not total_raw:
            return "<div class='log-line error'>❌ Debe ingresar el Total general ASTER.</div>"

        total = int(total_raw)

        if total < 0:
            return "<div class='log-line error'>❌ El Total general ASTER no puede ser negativo.</div>"

        session["total_aster"] = total

        return _crear_html_total_aster(
            total=total,
            origen="Ingreso manual",
            previews=[],
        )

    except ValueError:
        return "<div class='log-line error'>❌ El Total general ASTER debe ser numérico.</div>"

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error al guardar total ASTER: {exc}</div>"


@aster_bp.route("/accion/aster-buscar-archivo", methods=["POST"])
def accion_aster_buscar_archivo():
    """
    Busca el archivo After del día y lo copia a la carpeta local ASTER.

    Destino:
    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD
    """
    try:
        fecha_raw = request.form.get("fecha_proceso", "").strip()
        ruta_base_usuario = request.form.get("ruta_base", "").strip()

        if not fecha_raw:
            return "<div class='log-line error'>❌ Debe ingresar la fecha del proceso ASTER.</div>"

        fecha_yyyymmdd = _normalizar_fecha_aster(fecha_raw)

        rutas_busqueda = []

        if ruta_base_usuario:
            rutas_busqueda.append(ruta_base_usuario)

        rutas_busqueda.extend(RUTAS_ASTER_DEFAULT)

        ruta_origen: str | None = None

        for ruta_base in rutas_busqueda:
            ruta_encontrada = _buscar_archivo_aster_en_ruta(
                ruta_base,
                fecha_yyyymmdd,
            )

            if ruta_encontrada:
                ruta_origen = ruta_encontrada
                break

        if not ruta_origen:
            rutas_html = "<br>".join(
                f"<code>{ruta}</code>" for ruta in rutas_busqueda
            )

            return f"""
            <div class='log-line error'>
                ❌ No se encontró archivo ASTER para la fecha {fecha_yyyymmdd}.
            </div>
            <div class='log-line warning'>
                Rutas revisadas:<br>{rutas_html}
            </div>
            """

        carpeta_destino = os.path.join(
            DATA_DIR,
            fecha_yyyymmdd,
            "Aster",
            f"aster_{fecha_yyyymmdd}",
        )
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(ruta_origen)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        shutil.copy2(ruta_origen, ruta_destino)

        session["aster_fecha_proceso"] = fecha_yyyymmdd
        session["aster_archivo_origen"] = ruta_origen
        session["aster_archivo_copiado"] = ruta_destino

        return _generar_html_archivo_aster(
            fecha_yyyymmdd=fecha_yyyymmdd,
            ruta_origen=ruta_origen,
            ruta_destino=ruta_destino,
            nombre_archivo=nombre_archivo,
        )

    except ValueError as exc:
        return f"<div class='log-line error'>❌ {exc}</div>"

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error buscando archivo ASTER: {exc}</div>"

@aster_bp.route("/accion/aster-total-actual", methods=["GET"])
def accion_aster_total_actual():
    """
    Devuelve el total ASTER actual guardado en sesión.
    """
    total: Any = session.get("total_aster")

    if total is None:
        return "<div class='log-line warning'>⚠️ Todavía no hay total ASTER registrado.</div>"

    return _crear_html_total_aster(
        total=int(total),
        origen="Sesión actual",
        previews=[],
    )