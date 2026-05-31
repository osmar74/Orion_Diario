from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.orion_aster_config_service import (
    get_config,
    save_config,
    probar_configuracion,
)
from app.services.orion_aster_config_renderer import (
    render_config_panel,
    render_config_test_result,
)

orion_aster_config_bp = Blueprint("orion_aster_config", __name__)


@orion_aster_config_bp.get("/api/config/global")
def api_config_global_json():
    return jsonify(get_config())


@orion_aster_config_bp.get("/api/config/global/html")
def api_config_global_html():
    return render_config_panel(get_config())


@orion_aster_config_bp.post("/api/config/global")
def api_config_global_save():
    payload = request.get_json(silent=True) or {}
    config = save_config(payload)
    return jsonify({"ok": True, "config": config})


@orion_aster_config_bp.get("/api/config/probar/html")
def api_config_probar_html():
    conexion = request.args.get("conexion", "local")
    data = probar_configuracion(conexion)
    return render_config_test_result(data)


@orion_aster_config_bp.get("/api/config/probar")
def api_config_probar_json():
    conexion = request.args.get("conexion", "local")
    return jsonify(probar_configuracion(conexion))
