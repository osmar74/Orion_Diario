"""
Blueprint para la fase C: OCR y totales.
"""

import base64
import os

import pandas as pd
from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor


ocr_bp = Blueprint("ocr", __name__)


@ocr_bp.route("/accion/ocr-subir", methods=["POST"])
def accion_ocr_subir():
    """Recibe imágenes, las guarda en Reporte_Imagen y ejecuta OCR."""
    fecha = request.form.get("fecha", "202605_12")
    archivos = request.files.getlist("imagenes")

    archivos_validos = [
        archivo
        for archivo in archivos
        if (archivo.filename or "").strip()
    ]

    if not archivos_validos:
        return "<div class='log-line error'>❌ No se seleccionó ninguna imagen.</div>"

    carpeta_destino = os.path.join(DATA_DIR, f"orion_{fecha}", "Reporte_Imagen")
    os.makedirs(carpeta_destino, exist_ok=True)

    log_srv = obtener_log_service()
    ocr = OCRProcessor(TESSERACT_PATH, log_service=log_srv)

    # Tipado explícito para evitar que Pylance infiera dict[str, None].
    totales_finales: dict[str, int | None] = {
        "orion": None,
        "aister": None,
    }

    archivos_procesados: list[str] = []
    preview_imagenes: list[tuple[str, str]] = []

    for idx, archivo in enumerate(archivos_validos):
        nombre_original = archivo.filename or ""

        if not nombre_original.strip():
            continue

        nombre_base = secure_filename(nombre_original)

        if not nombre_base:
            continue

        nombre_lower = nombre_base.lower()

        nombre_unico = f"{pd.Timestamp.now().strftime('%H%M%S')}_{idx}_{nombre_base}"
        ruta_guardada = os.path.join(carpeta_destino, nombre_unico)

        archivo.save(ruta_guardada)
        archivos_procesados.append(nombre_unico)

        if len(preview_imagenes) < 3:
            with open(ruta_guardada, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode("utf-8")

            preview_imagenes.append((nombre_unico, img_b64))

        texto = ocr.extraer_texto(ruta_guardada)

        es_orion = "orion" in nombre_lower
        es_aister = "aister" in nombre_lower or "aster" in nombre_lower

        # 1. Método específico: Total general Orion/Aister
        totales_especificos = ocr.extraer_totales(texto)

        total_orion = totales_especificos.get("orion")
        total_aister = totales_especificos.get("aister")

        if totales_finales["orion"] is None and total_orion:
            totales_finales["orion"] = int(total_orion)

        if totales_finales["aister"] is None and total_aister:
            totales_finales["aister"] = int(total_aister)

        # 2. Método genérico: Total general
        if totales_finales["orion"] is None or totales_finales["aister"] is None:
            numeros_gen = ocr.extraer_totales_generico(texto)

            if numeros_gen:
                if len(numeros_gen) == 1:
                    if es_orion and totales_finales["orion"] is None:
                        totales_finales["orion"] = int(numeros_gen[0])
                    elif es_aister and totales_finales["aister"] is None:
                        totales_finales["aister"] = int(numeros_gen[0])

                elif len(numeros_gen) >= 2:
                    if es_orion and totales_finales["orion"] is None:
                        totales_finales["orion"] = int(numeros_gen[0])
                    elif es_aister and totales_finales["aister"] is None:
                        totales_finales["aister"] = int(numeros_gen[-1])
                    else:
                        if totales_finales["orion"] is None:
                            totales_finales["orion"] = int(numeros_gen[0])
                        if totales_finales["aister"] is None:
                            totales_finales["aister"] = int(numeros_gen[-1])

        # 3. Respaldo: buscar número cerca de Orion o Aister
        if totales_finales["orion"] is None and es_orion:
            num = ocr.extraer_numero_cercano(texto, "Orion")

            if num:
                totales_finales["orion"] = int(num)

        if totales_finales["aister"] is None and es_aister:
            num = ocr.extraer_numero_cercano(texto, "Aister")

            if num:
                totales_finales["aister"] = int(num)

    # Guardar en sesión
    session["totales_orion"] = totales_finales["orion"]
    session["totales_aister"] = totales_finales["aister"]
    session["ultima_fecha"] = fecha

    # Construir HTML con diseño de dos columnas
    html = '<div class="ocr-result-container">'
    html += '<div class="ocr-images">'

    if preview_imagenes:
        for nombre, img_b64 in preview_imagenes:
            html += (
                "<div class='ocr-thumb'>"
                f"<img src='data:image/png;base64,{img_b64}' alt='{nombre}'/>"
                f"<small>{nombre}</small>"
                "</div>"
            )
    else:
        html += "<p style='color:#888;'>No hay imágenes disponibles.</p>"

    html += "</div>"
    html += '<div class="ocr-results">'

    if totales_finales["orion"] is not None or totales_finales["aister"] is not None:
        html += "<div class='log-line success'>✅ OCR completado</div>"
        html += '<div class="totales-archivos-row">'
        html += '<div class="totales-grid">'
        html += (
            "<div class='total-card'>"
            "<span class='label'>🔹 Orion</span>"
            f"<span class='value'>{totales_finales['orion']}</span>"
            "</div>"
        )
        html += (
            "<div class='total-card'>"
            "<span class='label'>🔹 Aister</span>"
            f"<span class='value'>{totales_finales['aister']}</span>"
            "</div>"
        )
        html += "</div>"
        html += (
            "<details class='archivos-guardados'>"
            f"<summary>📁 Archivos guardados ({len(archivos_procesados)})</summary>"
            "<ul>"
        )

        for nombre in archivos_procesados:
            html += f"<li>{nombre}</li>"

        html += "</ul></details>"
        html += "</div>"
    else:
        html += "<div class='log-line warning'>⚠️ No se detectaron totales en las imágenes.</div>"

    html += "</div>"
    html += (
        '<div id="ocr-data" style="display:none;" '
        f'data-orion="{totales_finales["orion"]}" '
        f'data-aister="{totales_finales["aister"]}">'
        "</div>"
    )
    html += "</div>"

    return html


@ocr_bp.route("/accion/consolidar-totales", methods=["POST"])
def accion_consolidar_totales():
    """Recibe totales manuales desde el frontend y los guarda en sesión."""
    try:
        orion = request.form.get("orion", type=int)
        aister = request.form.get("aister", type=int)

        session["totales_orion"] = orion
        session["totales_aister"] = aister

        return "<div class='log-line success'>✅ Totales consolidados correctamente.</div>"

    except Exception as e:
        return f"<div class='log-line error'>❌ Error: {e}</div>"