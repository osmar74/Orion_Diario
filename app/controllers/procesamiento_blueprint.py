"""
Blueprint para la fase F: Procesamiento de Discador, Causales, Lotes y Comparación.
"""

import os
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
from app.services.orion_processing_renderer import (
    render_causales_result,
    render_comparacion_lotes_result,
    render_discador_campaign_debug,
    render_discador_not_found,
    render_discador_result,
    render_log_error,
    render_lotes_result,
)


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
        return render_discador_not_found()

    debug_html = render_discador_campaign_debug(ruta_disc)

    res = disc.procesar(
        ruta_disc,
        total_esperado,
        carpeta_consolidados,
    )

    return render_discador_result(
        res=res,
        ruta_disc=ruta_disc,
        total_esperado=total_esperado,
        debug_html=debug_html,
    )
    

@proc_bp.route("/accion/procesar-causales")
def accion_procesar_causales():
    fecha = request.args.get("fecha", "202605_12")

    caus = CausalesProcessor(log_service=obtener_log_service())
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    carpeta_causales = os.path.join(carpeta_diaria, "Causales")

    carpeta_consolidados = os.path.join(carpeta_diaria, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    if not os.path.isdir(carpeta_causales):
        return render_log_error("No existe la carpeta Causales.")

    res = caus.procesar_carpeta_causales(
        carpeta_causales,
        carpeta_consolidados,
    )

    return render_causales_result(res)



@proc_bp.route("/accion/procesar-lotes")
def accion_procesar_lotes():
    fecha = request.args.get("fecha", "202605_12")

    lotes = LotesProcessor(log_service=obtener_log_service())
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    carpeta_lotes = os.path.join(carpeta_diaria, "Lotes")

    carpeta_consolidados = os.path.join(carpeta_diaria, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    if not os.path.isdir(carpeta_lotes):
        return render_log_error("No existe la carpeta Lotes.")

    ruta_disc = buscar_archivo_discador_para_lotes(carpeta_diaria)

    res = lotes.procesar_carpeta_lotes(
        carpeta_lotes,
        fecha,
        ruta_disc,
        carpeta_salida=carpeta_consolidados,
    )

    return render_lotes_result(
        res=res,
        ruta_disc=ruta_disc,
    )




@proc_bp.route("/accion/comparar-lotes")
def accion_comparar_lotes():
    fecha = request.args.get("fecha", "202605_12")
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)

    res = comparar_lotes_orion(
        carpeta_orion=carpeta_diaria,
        fecha=fecha,
    )

    return render_comparacion_lotes_result(res)


