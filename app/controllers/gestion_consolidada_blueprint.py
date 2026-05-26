from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, render_template, request

from app.services.gestion_consolidada_service import (
    consultar_resumen_sql,
    preparar_proceso,
    unir_archivos_gestion,
    verificar_calidad_gestion,
)
from app.services.gestion_consolidada_renderer_service import (
    render_preparar_proceso,
    render_resumen_sql,
    render_unir_archivos_gestion,
    render_verificar_calidad_gestion,
)


gestion_consolidada_bp = Blueprint("gestion_consolidada", __name__)


def _data_dir() -> Path:
    configured = current_app.config.get("DATA_DIR")

    if configured:
        return Path(configured)

    return Path(current_app.root_path).parent / "data"


@gestion_consolidada_bp.route("/gestion-consolidada", methods=["GET"])
def vista_gestion_consolidada():
    return render_template("gestion_consolidada.html")


@gestion_consolidada_bp.route("/accion/gestion-consolidada/resumen", methods=["POST"])
def accion_gestion_consolidada_resumen():
    fecha = request.form.get("fecha", "")
    conexion = request.form.get("conexion", "local")

    resultado = consultar_resumen_sql(fecha, conexion)

    return render_resumen_sql(resultado)


@gestion_consolidada_bp.route("/accion/gestion-consolidada/preparar", methods=["POST"])
def accion_gestion_consolidada_preparar():
    fecha = request.form.get("fecha", "")

    resultado = preparar_proceso(_data_dir(), fecha)

    return render_preparar_proceso(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/unir", methods=["POST"])
def accion_gestion_consolidada_unir():
    fecha = request.form.get("fecha", "")

    resultado = unir_archivos_gestion(_data_dir(), fecha)

    return render_unir_archivos_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/verificar-calidad", methods=["POST"])
def accion_gestion_consolidada_verificar_calidad():
    fecha = request.form.get("fecha", "")

    resultado = verificar_calidad_gestion(_data_dir(), fecha)

    return render_verificar_calidad_gestion(resultado)
