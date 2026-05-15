"""
Blueprint para rutas generales: inicio, logs, reset y prueba de conexión.
"""

from flask import Blueprint, render_template, request, session

from app.config import LOG_DB_PATH
from app.controllers.helpers import obtener_log_service

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Página principal con los valores actuales de la sesión."""
    totales_orion = session.get("totales_orion")
    totales_aister = session.get("totales_aister")
    ultima_fecha = session.get("ultima_fecha", "202605_12")

    if totales_orion is None:
        totales_orion = "--"
    if totales_aister is None:
        totales_aister = "--"

    return render_template(
        "index.html",
        titulo="Orion Procesos",
        totales_orion=totales_orion,
        totales_aister=totales_aister,
        ultima_fecha=ultima_fecha,
    )


@main_bp.route("/logs")
def logs():
    """Página de visualización de logs con filtros."""
    log_srv = obtener_log_service()
    fase = request.args.get("fase", None)
    resultado = request.args.get("resultado", None)

    logs_list = log_srv.obtener_logs(fase=fase, resultado=resultado, limite=500)

    fases_posibles = ["2.1", "2.2", "2.3", "3.2", "4.1", "4.2", "4.3", "Reset"]
    resultados_posibles = ["éxito", "error", "info", "advertencia"]

    # Leer totales de la sesión para pasarlos a la plantilla
    totales_orion = session.get("totales_orion")
    totales_aister = session.get("totales_aister")
    ultima_fecha = session.get("ultima_fecha", "202605_12")
    if totales_orion is None:
        totales_orion = "--"
    if totales_aister is None:
        totales_aister = "--"

    return render_template(
        "logs.html",
        logs=logs_list,
        fase_actual=fase,
        resultado_actual=resultado,
        fases=fases_posibles,
        resultados=resultados_posibles,
        totales_orion=totales_orion,
        totales_aister=totales_aister,
        ultima_fecha=ultima_fecha,
    )


@main_bp.route("/reset")
def reset_proceso():
    """Limpia la sesión y registra el reinicio en los logs."""
    log_srv = obtener_log_service()
    log_srv.log(
        "Reset",
        "Reinicio del proceso",
        "info",
        "El usuario solicitó reiniciar todo el proceso.",
    )
    session.clear()
    return "<div class='log-line success'>✅ Sesión reiniciada. Redirigiendo...</div>"


@main_bp.route("/reset-logs", methods=["POST"])
def reset_logs():
    """Vacia la tabla de logs."""
    import sqlite3

    try:
        with sqlite3.connect(LOG_DB_PATH) as conn:
            conn.execute("DELETE FROM action_log")
            conn.commit()
        return "<div class='log-line success'>✅ Logs eliminados correctamente.</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al resetear logs: {e}</div>"


@main_bp.route("/accion/probar-conexion-activa")
def accion_probar_conexion_activa():
    """Prueba la conexión usando la configuración activa (local o remoto)."""
    conexion = request.args.get("conexion", "local")
    from app.config import SQL_LOCAL, SQL_REMOTO
    from app.controllers.helpers import construir_cadena_conexion
    import pyodbc

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL
    try:
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return "<div class='log-line success'>✅ Conexión exitosa</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error: {e}</div>"
