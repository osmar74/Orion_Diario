"""
Blueprint para la Fase G: Carga de datos a SQL Server.
"""

import json
import os
from html import escape

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

def _obtener_fecha_fase_g_orion() -> str:
    """
    Obtiene la fecha activa para Fase G.

    Prioridad:
    1. request.form["fecha"]
    2. session["ultima_fecha"]
    3. valor fallback

    Se normaliza a YYYYMMDD para usar la estructura nueva:
    data\\YYYYMMDD\\Orion\\Consolidados
    """
    fecha_raw = (
        request.form.get("fecha")
        or session.get("ultima_fecha")
        or "20260512"
    )

    try:
        fecha = normalizar_fecha_yyyymmdd(fecha_raw)
    except Exception:
        fecha = str(fecha_raw or "").strip()

    session["ultima_fecha"] = fecha

    return fecha


def _patron_consolidado_orion(tipo: str) -> str:
    tipo_limpio = str(tipo or "").strip().lower()

    patrones = {
        "causales": "Causales_Consolidado*.xlsx",
        "lote": "Lote_Consolidado*.xlsx",
        "discador": "*Discador*Consolidado.xlsx",
    }

    return patrones.get(tipo_limpio, "*.xlsx")


def _render_info_busqueda_consolidado_orion(
    fecha: str,
    tipo: str,
    resultado: dict | None = None,
) -> str:
    """
    Muestra en el panel de Fase G dónde se está buscando el consolidado.
    """
    resultado = resultado or {}

    carpeta_orion = os.path.join(str(DATA_DIR), str(fecha), "Orion")
    carpeta_consolidados = os.path.join(carpeta_orion, "Consolidados")

    ruta_archivo = (
        resultado.get("ruta_archivo")
        or resultado.get("ruta_consolidado")
        or resultado.get("archivo")
        or ""
    )
    nombre_archivo = (
        resultado.get("nombre_archivo")
        or resultado.get("nombre_consolidado")
        or (os.path.basename(str(ruta_archivo)) if ruta_archivo else "")
        or ""
    )

    if ruta_archivo:
        estado = "✅ Archivo encontrado"
        estado_clase = "success"
    else:
        estado = "⚠️ Archivo no encontrado"
        estado_clase = "warning"

    return f"""
    <div class="orion-lookup-card">
        <div class="log-line {estado_clase}">
            {estado}: {escape(str(nombre_archivo or 'Sin archivo'))}
        </div>

        <table class="dataframe ui-table-compact">
            <tr>
                <th colspan="2">Diagnóstico de búsqueda Fase G - {escape(str(tipo).upper())}</th>
            </tr>
            <tr>
                <td><b>Fecha usada</b></td>
                <td>{escape(str(fecha))}</td>
            </tr>
            <tr>
                <td><b>Carpeta ORION</b></td>
                <td>{escape(str(carpeta_orion))}</td>
            </tr>
            <tr>
                <td><b>Carpeta Consolidados</b></td>
                <td>{escape(str(carpeta_consolidados))}</td>
            </tr>
            <tr>
                <td><b>Patrón esperado</b></td>
                <td>{escape(_patron_consolidado_orion(tipo))}</td>
            </tr>
            <tr>
                <td><b>Ruta archivo</b></td>
                <td>{escape(str(ruta_archivo or 'No encontrado'))}</td>
            </tr>
        </table>
    </div>
    """




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

    fecha = _obtener_fecha_fase_g_orion()

    resultado = verificar_carga_orion(
        data_dir=DATA_DIR,
        fecha=fecha,
        tipo=tipo,
        conexion=conexion,
        cfg_sql=cfg,
    )

    return _render_info_busqueda_consolidado_orion(fecha, tipo, resultado) + render_verificacion_carga_orion(resultado)




@carga_bp.route("/accion/insertar-datos", methods=["POST"])
def accion_insertar_datos():
    """
    Inserta los datos ORION.

    La lógica de negocio vive en:
    app.services.orion_load_insert_service
    """
    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")
    fecha = _obtener_fecha_fase_g_orion()

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    resultado = insertar_datos_orion(
        data_dir=DATA_DIR,
        fecha=fecha,
        tipo=tipo,
        conexion=conexion,
        cfg_sql=cfg,
    )

    return _render_info_busqueda_consolidado_orion(fecha, tipo, resultado) + render_insercion_orion_resultado(resultado)


@carga_bp.route("/accion/probar-conexion-consolidado")
def accion_probar_conexion_consolidado():
    """
    Prueba la conexión para el panel de consolidado ORION.
    """
    conexion = request.args.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    resultado = probar_conexion_sql_server(cfg)

    return render_prueba_conexion_orion(resultado)




def _normalizar_fecha_consolidado_orion_v2(valor: str) -> str:
    """
    Acepta YYYYMMDD o YYYY-MM-DD y devuelve YYYY-MM-DD.
    """
    raw = str(valor or "").strip().replace("/", "-")

    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"

    return raw


def _normalizar_meses_consolidado_orion_v2(fecha: str, meses: str = "", mes_gestion: str = "") -> str:
    """
    Devuelve YYYYMM para el consolidado.

    Prioridad:
    1. meses si ya viene como YYYYMM.
    2. derivar desde fecha YYYY-MM-DD.
    3. derivar desde fecha YYYYMMDD.
    """
    raw_meses = str(meses or "").strip()

    if len(raw_meses) == 6 and raw_meses.isdigit():
        return raw_meses

    raw_fecha = str(fecha or "").strip().replace("-", "").replace("/", "")

    if len(raw_fecha) >= 6 and raw_fecha[:6].isdigit():
        return raw_fecha[:6]

    return raw_meses or "202605"

@carga_bp.route("/accion/consolidar-consulta", methods=["POST"])
def accion_consolidar_consulta():
    """
    Ejecuta la consulta SQL de consolidación ORION.

    La lógica de negocio vive en:
    app.services.orion_consolidado_query_service
    """
    fecha_raw = (
        request.form.get("fecha")
        or request.form.get("fecha_proceso")
        or "2026-05-05"
    )

    fecha = _normalizar_fecha_consolidado_orion_v2(fecha_raw)

    meses = _normalizar_meses_consolidado_orion_v2(
        fecha=fecha,
        meses=request.form.get("meses", ""),
        mes_gestion=request.form.get("mes_gestion", ""),
    )

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
    
