from flask import Blueprint, jsonify, render_template, request

from app.config import DATA_DIR

from app.services.orion_diario_v2_dashboard_service import (
    construir_contexto_orion_v2,
    construir_estadisticas_orion_v2,
    preparar_distribucion_orion_v2,
    copiar_distribucion_orion_v2,
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

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN ===

@orion_diario_v2_bp.route("/api/orion-diario-v2/distribucion/preparar")
def api_orion_diario_v2_distribucion_preparar():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    rutas_base = request.args.getlist("rutas_base")

    data = preparar_distribucion_orion_v2(
        data_dir=DATA_DIR,
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        rutas_base=rutas_base,
    )

    status = 200 if data.get("success") else 400
    return jsonify(data), status


@orion_diario_v2_bp.route("/api/orion-diario-v2/distribucion/copiar", methods=["POST"])
def api_orion_diario_v2_distribucion_copiar():
    payload = request.get_json(silent=True) or {}

    fecha_proceso = str(
        payload.get("fecha_proceso")
        or payload.get("fecha")
        or "20260429"
    ).strip()

    mes_gestion = str(payload.get("mes_gestion") or "abril").strip()
    rutas_base = payload.get("rutas_base") or []
    seleccionados = payload.get("seleccionados") or []

    if not isinstance(rutas_base, list):
        rutas_base = []

    if not isinstance(seleccionados, list):
        seleccionados = []

    data = copiar_distribucion_orion_v2(
        data_dir=DATA_DIR,
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        seleccionados=seleccionados,
        rutas_base=rutas_base,
    )

    status = 200 if data.get("success") else 400
    return jsonify(data), status

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_END ===

# === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_BEGIN ===

@orion_diario_v2_bp.route("/api/orion-diario-v2/carga/precheck", methods=["GET", "POST"])
def api_orion_diario_v2_carga_precheck():
    from flask import jsonify, request
    from app.config import DATA_DIR
    from app.services.orion_diario_v2_dashboard_service import precheck_carga_orion_v2

    payload = request.get_json(silent=True) or {}

    fecha_proceso = (
        request.args.get("fecha_proceso")
        or request.args.get("fecha")
        or payload.get("fecha_proceso")
        or payload.get("fecha")
        or "20260429"
    )

    tipo = (
        request.args.get("tipo")
        or payload.get("tipo")
        or ""
    )

    conexion = (
        request.args.get("conexion")
        or payload.get("conexion")
        or "local"
    )

    data = precheck_carga_orion_v2(
        data_dir=DATA_DIR,
        fecha_proceso=fecha_proceso,
        tipo=tipo,
        conexion=conexion,
    )

    return jsonify(data), 200

# === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_END ===
