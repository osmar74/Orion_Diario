from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from app.services.aster_diario_v2_context_service import (
    construir_contexto_aster_v2,
    probar_configuracion_aster_v2,
)
from app.services.aster_diario_v2_actions_service import ejecutar_accion_aster_v2

aster_diario_v2_bp = Blueprint("aster_diario_v2", __name__)


@aster_diario_v2_bp.get("/aster-diario-v2")
def vista_aster_diario_v2():
    return render_template("aster_diario_v2/index.html")


@aster_diario_v2_bp.get("/api/aster-diario-v2/contexto")
def api_aster_diario_v2_contexto():
    fecha = request.args.get("fecha_proceso") or request.args.get("fecha") or "20260429"
    conexion = request.args.get("conexion") or "local"

    data = construir_contexto_aster_v2(
        fecha_proceso=fecha,
        conexion=conexion,
    )

    return jsonify(data)


@aster_diario_v2_bp.get("/api/aster-diario-v2/probar-config")
def api_aster_diario_v2_probar_config():
    conexion = request.args.get("conexion") or "local"
    data = probar_configuracion_aster_v2(conexion)
    return jsonify(data)
@aster_diario_v2_bp.post("/api/aster-diario-v2/accion")
def api_aster_diario_v2_accion():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}

    accion = payload.get("accion") or request.args.get("accion") or ""
    fecha = (
        payload.get("fecha_proceso")
        or payload.get("fecha")
        or request.args.get("fecha_proceso")
        or "20260429"
    )
    conexion = (
        payload.get("conexion")
        or request.args.get("conexion")
        or "local"
    )

    data = ejecutar_accion_aster_v2(
        accion=accion,
        fecha_proceso=fecha,
        conexion=conexion,
    )

    status = 200 if data.get("ok") or data.get("estado") in {"revisar", "pendiente"} else 400

    return jsonify(data), status
