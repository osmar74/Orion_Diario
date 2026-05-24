"""
Blueprint para la Fase G: Carga de datos a SQL Server.
"""

import json

from flask import Blueprint, request, session

from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO

from app.services.orion_load_renderer import (
    render_consolidado_consulta_orion,
    render_gestion_orion_exportada,
    render_insercion_orion_resultado,
    render_log_error,
    render_prueba_conexion_orion,
    render_prueba_lectura_orion,
    render_tabla_estadisticas_consolidado,
    render_verificacion_carga_orion,
)

from app.services.orion_gestion_export_service import (
    exportar_gestion_orion_desde_temporal,
)

from app.services.orion_load_verification_service import verificar_carga_orion
from app.services.orion_load_insert_service import insertar_datos_orion
from app.services.orion_consolidado_query_service import (
    ejecutar_consulta_consolidado_orion,
)

from app.services.orion_connection_service import (
    probar_conexion_sql_server,
    probar_lectura_tabla_sql_server,
)

carga_bp = Blueprint("carga", __name__)


@carga_bp.route("/accion/probar-conexion", methods=["POST"])
def accion_probar_conexion():
    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    cfg = {
        "server": servidor,
        "port": puerto,
        "database": basedatos,
        "auth": autenticacion,
        "username": usuario,
        "password": password,
    }

    resultado = probar_conexion_sql_server(cfg)

    return render_prueba_conexion_orion(resultado)


@carga_bp.route("/accion/probar-lectura", methods=["POST"])
def accion_probar_lectura():
    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    cfg = {
        "server": servidor,
        "port": puerto,
        "database": basedatos,
        "auth": autenticacion,
        "username": usuario,
        "password": password,
    }

    resultado = probar_lectura_tabla_sql_server(
        cfg_sql=cfg,
        tabla="Causales",
        limite=5,
    )

    return render_prueba_lectura_orion(resultado)



@carga_bp.route("/accion/verificar-carga", methods=["POST"])
def accion_verificar_carga():
    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")

    resultado = verificar_carga_orion(
        data_dir=DATA_DIR,
        fecha=fecha,
        tipo=tipo,
        conexion=conexion,
        cfg_sql=cfg,
    )

    return render_verificacion_carga_orion(resultado)




@carga_bp.route("/accion/insertar-datos", methods=["POST"])
def accion_insertar_datos():
    """
    Inserta los datos ORION.

    La lógica de negocio vive en:
    app.services.orion_load_insert_service
    """
    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")
    fecha = session.get("ultima_fecha", "202605_12")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    resultado = insertar_datos_orion(
        data_dir=DATA_DIR,
        fecha=fecha,
        tipo=tipo,
        conexion=conexion,
        cfg_sql=cfg,
    )

    return render_insercion_orion_resultado(resultado)


@carga_bp.route("/accion/probar-conexion-consolidado")
def accion_probar_conexion_consolidado():
    """
    Prueba la conexión para el panel de consolidado ORION.
    """
    conexion = request.args.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    resultado = probar_conexion_sql_server(cfg)

    return render_prueba_conexion_orion(resultado)


@carga_bp.route("/accion/consolidar-consulta", methods=["POST"])
def accion_consolidar_consulta():
    """
    Ejecuta la consulta SQL de consolidación ORION.

    La lógica de negocio vive en:
    app.services.orion_consolidado_query_service
    """
    fecha = request.form.get("fecha", "2026-05-05")
    meses = request.form.get("meses", "202605")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    resultado = ejecutar_consulta_consolidado_orion(
        data_dir=DATA_DIR,
        fecha=fecha,
        meses=meses,
        cfg_sql=cfg,
    )

    return render_consolidado_consulta_orion(resultado)




@carga_bp.route("/accion/consolidar-aplicar", methods=["POST"])
def accion_consolidar_aplicar():
    """
    Aplica filtros seleccionados y exporta el Excel final de Gestión ORION.

    La lógica de negocio está en:
    app.services.orion_gestion_export_service
    """
    fecha = request.form.get("fecha", "2026-05-05")
    temp_id = request.form.get("temp_id")

    try:
        seleccionados = json.loads(request.form.get("seleccionados", "[]"))
    except Exception:
        seleccionados = []

    if not isinstance(seleccionados, list):
        seleccionados = []

    resultado = exportar_gestion_orion_desde_temporal(
        data_dir=DATA_DIR,
        fecha=fecha,
        seleccionados=seleccionados,
        temp_id=temp_id,
    )

    if not resultado.get("success"):
        return render_log_error(resultado.get("error", "Error desconocido."))

    html_estadisticas = render_tabla_estadisticas_consolidado(
        "Estadísticas después de aplicar filtro y exportar",
        resultado["estadisticas"],
    )

    return render_gestion_orion_exportada(
        html_estadisticas=html_estadisticas,
        nombre_archivo=resultado["nombre_archivo"],
        ruta_salida=resultado["ruta_salida"],
        ruta_relativa_descarga=resultado["ruta_relativa_descarga"],
    )
    
