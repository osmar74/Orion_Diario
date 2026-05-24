"""
Blueprint para las fases A-B y D:
- Crear estructura diaria
- Verificar red y carpetas
- Distribuir archivos
"""

from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.controllers.helpers import obtener_log_service

from app.services.orion_fases_service import (
    crear_estructura_diaria_orion,
    distribuir_archivos_seleccionados_orion,
    normalizar_fecha_orion,
    preparar_distribucion_archivos_orion,
    verificar_red_carpetas_orion,
)

from app.services.orion_fases_renderer import (
    render_crear_estructura_orion,
    render_distribucion_seleccionados_orion,
    render_log_error,
    render_preparar_distribucion_orion,
    render_verificar_red_orion,
)


fases_ab_bp = Blueprint("fases_ab", __name__)


@fases_ab_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha_raw = request.args.get("fecha", "202605_12")

    respuesta = crear_estructura_diaria_orion(
        data_dir=DATA_DIR,
        fecha_raw=fecha_raw,
        log_service=obtener_log_service(),
    )

    return render_crear_estructura_orion(
        fecha=respuesta["fecha"],
        data_dir=DATA_DIR,
        resultado=respuesta["resultado"],
    )


@fases_ab_bp.route("/accion/verificar-red")
def accion_verificar_red():
    fecha_raw = request.args.get("fecha", "202605_06")

    respuesta = verificar_red_carpetas_orion(
        data_dir=DATA_DIR,
        fecha_raw=fecha_raw,
        log_service=obtener_log_service(),
    )

    resultado = respuesta["resultado"]

    if resultado.get("success"):
        session["red_base_activa"] = respuesta.get("red_base_activa")

    return render_verificar_red_orion(resultado)


@fases_ab_bp.route("/accion/distribuir")
def accion_distribuir():
    """
    Fase D - Preparar distribución.

    No copia inmediatamente.
    Primero muestra los archivos encontrados para que el usuario seleccione cuáles copiar.
    """
    fecha_raw = request.args.get("fecha", "202605_12")
    red_base = session.get("red_base_activa")

    respuesta = preparar_distribucion_archivos_orion(
        data_dir=DATA_DIR,
        fecha_raw=fecha_raw,
        red_base=red_base,
        log_service=obtener_log_service(),
    )

    if not respuesta.get("success"):
        return render_log_error(respuesta.get("error", "Error preparando distribución ORION."))

    fecha = respuesta["fecha"]
    session["orion_distribucion_fecha"] = fecha

    return render_preparar_distribucion_orion(
        fecha=fecha,
        rutas_validadas=respuesta["rutas_validadas"],
        archivos_encontrados=respuesta["archivos_encontrados"],
        carpeta_diaria=respuesta["carpeta_diaria"],
    )


@fases_ab_bp.route("/accion/distribuir-seleccionados", methods=["POST"])
def accion_distribuir_seleccionados():
    """
    Copia solo los archivos seleccionados por el usuario en Fase D.
    """
    data = request.get_json(silent=True) or {}

    fecha_raw = (
        data.get("fecha")
        or session.get("orion_distribucion_fecha")
        or "202605_12"
    )

    seleccionados = data.get("seleccionados", [])

    if not isinstance(seleccionados, list):
        seleccionados = []

    respuesta = distribuir_archivos_seleccionados_orion(
        data_dir=DATA_DIR,
        fecha_raw=fecha_raw,
        seleccionados=seleccionados,
        red_base=session.get("red_base_activa"),
        log_service=obtener_log_service(),
    )

    if respuesta.get("error_simple"):
        return render_log_error(respuesta.get("error", "Error copiando archivos ORION."))

    return render_distribucion_seleccionados_orion(respuesta)


def _normalizar_fecha_orion(fecha_raw: str) -> str:
    """
    Compatibilidad temporal.

    Usar directamente:
    app.services.orion_fases_service.normalizar_fecha_orion
    """
    return normalizar_fecha_orion(fecha_raw)
