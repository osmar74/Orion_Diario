from flask import Blueprint, jsonify, render_template, request

from app.services.orion_diario_v2_dashboard_service import (
    construir_contexto_orion_v2,
    construir_estadisticas_orion_v2,
)


orion_diario_v2_bp = Blueprint("orion_diario_v2", __name__)


@orion_diario_v2_bp.route("/orion-diario-v2")
def vista_orion_diario_v2():
    return render_template("orion_diario_v2/index.html")


@orion_diario_v2_bp.route("/api/orion-diario-v2/contexto")
def api_orion_diario_v2_contexto():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    conexion = request.args.get("conexion", "local").strip().lower()

    data = construir_contexto_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
    )

    return jsonify(data)


@orion_diario_v2_bp.route("/api/orion-diario-v2/estadisticas")
def api_orion_diario_v2_estadisticas():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    conexion = request.args.get("conexion", "local").strip().lower()

    rutas_base = request.args.getlist("rutas_base")

    data = construir_estadisticas_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
        rutas_base=rutas_base,
    )

    return jsonify(data)
