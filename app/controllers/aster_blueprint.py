"""
Blueprint para Gestión Diaria ASTER.

Fase A:
- Captura del total diario por OCR.
- Captura manual del total general.
"""

import base64
import os
from typing import Any

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor


aster_bp = Blueprint("aster", __name__)


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