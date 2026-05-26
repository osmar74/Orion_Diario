from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, render_template, request

from app.services.gestion_consolidada_service import (
    consultar_resumen_sql,
    preparar_proceso,
    unir_archivos_gestion,
    verificar_calidad_gestion,
    aplicar_ajuste_no_contestan_gestion,
    limpiar_nota_gestion,
    procesar_compromiso_gestion,
    generar_archivo_final_gestion,
    listar_archivos_generados_gestion,
)
from app.services.gestion_consolidada_renderer_service import (
    render_preparar_proceso,
    render_resumen_sql,
    render_unir_archivos_gestion,
    render_verificar_calidad_gestion,
    render_ajuste_no_contestan_gestion,
    render_limpiar_nota_gestion,
    render_compromiso_gestion,
    render_archivo_final_gestion,
    render_archivos_generados_gestion,
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



@gestion_consolidada_bp.route("/accion/gestion-consolidada/ajuste-no-contestan", methods=["POST"])
def accion_gestion_consolidada_ajuste_no_contestan():
    fecha = request.form.get("fecha", "")
    porcentaje = request.form.get("porcentaje_no_contestan", "12")

    resultado = aplicar_ajuste_no_contestan_gestion(_data_dir(), fecha, porcentaje)

    return render_ajuste_no_contestan_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/limpiar-nota", methods=["POST"])
def accion_gestion_consolidada_limpiar_nota():
    fecha = request.form.get("fecha", "")

    resultado = limpiar_nota_gestion(_data_dir(), fecha)

    return render_limpiar_nota_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/compromiso", methods=["POST"])
def accion_gestion_consolidada_compromiso():
    fecha = request.form.get("fecha", "")

    resultado = procesar_compromiso_gestion(_data_dir(), fecha)

    return render_compromiso_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/archivo-final", methods=["POST"])
def accion_gestion_consolidada_archivo_final():
    fecha = request.form.get("fecha", "")

    resultado = generar_archivo_final_gestion(_data_dir(), fecha)

    return render_archivo_final_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/archivos-generados", methods=["POST"])
def accion_gestion_consolidada_archivos_generados():
    fecha = request.form.get("fecha", "")

    resultado = listar_archivos_generados_gestion(_data_dir(), fecha)

    return render_archivos_generados_gestion(resultado)
