from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request
from app.config import DATA_DIR

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
    cargar_informacion_gestion_sql,
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
    render_carga_sql_gestion,
)

from app.services.gestion_consolidada_ui_service import GestionConsolidadaUiService
from app.services.gestion_consolidada_state_service import GestionConsolidadaStateService

gestion_consolidada_bp = Blueprint("gestion_consolidada", __name__)


# === CONSOLIDAR_V2_FASE_I_AUDITORIA_TIEMPOS_V2_BEGIN ===

def _gc_fase_i_perf_now():
    from time import perf_counter
    return perf_counter()


def _gc_fase_i_clock_now():
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _gc_fase_i_add_timing(auditoria, paso, inicio_perf, inicio_clock, detalle=""):
    fin_perf = _gc_fase_i_perf_now()
    fin_clock = _gc_fase_i_clock_now()

    auditoria.append({
        "paso": paso,
        "inicio": inicio_clock,
        "fin": fin_clock,
        "segundos": round(fin_perf - inicio_perf, 3),
        "detalle": detalle or "",
    })

    return fin_perf, fin_clock


def _gc_fase_i_html_tiempos(auditoria):
    total = sum(float(x.get("segundos") or 0) for x in auditoria if not str(x.get("paso", "")).lower().startswith("tiempo total"))

    rows = []

    for item in auditoria:
        rows.append(
            "<tr>"
            f"<td>{item.get('paso', '')}</td>"
            f"<td>{item.get('inicio', '')}</td>"
            f"<td>{item.get('fin', '')}</td>"
            f"<td class='gc-fase-i-tiempo-num'>{item.get('segundos', '')}</td>"
            f"<td>{item.get('detalle', '')}</td>"
            "</tr>"
        )

    rows.append(
        "<tr class='gc-fase-i-tiempo-total'>"
        "<td><b>Tiempo total medido</b></td>"
        "<td></td>"
        "<td></td>"
        f"<td class='gc-fase-i-tiempo-num'><b>{round(total, 3)}</b></td>"
        "<td>Tiempo total registrado en backend.</td>"
        "</tr>"
    )

    return (
        "<section class='gc-fase-i-tiempo-box'>"
        "<h3>⏱ Auditoría de tiempos — Fase I</h3>"
        "<table class='gc-fase-i-tiempo-table'>"
        "<thead>"
        "<tr>"
        "<th>Paso</th>"
        "<th>Inicio</th>"
        "<th>Fin</th>"
        "<th>Segundos</th>"
        "<th>Detalle</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody>"
        "</table>"
        "</section>"
    )


def _gc_fase_i_append_html(response, extra_html):
    if response is None:
        return extra_html

    if isinstance(response, str):
        return response + extra_html

    if isinstance(response, tuple):
        body = response[0]

        if isinstance(body, str):
            return (body + extra_html, *response[1:])

        if hasattr(body, "get_data") and hasattr(body, "set_data"):
            data = body.get_data(as_text=True)
            body.set_data(data + extra_html)
            return response

        return response

    if hasattr(response, "get_data") and hasattr(response, "set_data"):
        try:
            data = response.get_data(as_text=True)
            response.set_data(data + extra_html)
            return response
        except Exception:
            return response

    return response

# === CONSOLIDAR_V2_FASE_I_AUDITORIA_TIEMPOS_V2_END ===

def _data_dir():
    """
    Raíz de datos para Consolidar Gestión.

    Debe respetar la configuración central app.config.DATA_DIR.
    No debe volver a la carpeta local del proyecto salvo que no exista configuración.
    """
    configured = current_app.config.get("DATA_DIR") or DATA_DIR
    return Path(str(configured)).expanduser()


# === GC V2 BACKEND STATE HELPERS ===

def _gc_state_service():
    instance = Path(current_app.instance_path)
    instance.mkdir(parents=True, exist_ok=True)
    return GestionConsolidadaStateService(instance / "gestion_consolidada_estado.json")


def _gc_estado_desde_resultado(codigo_fase, resultado):
    if not isinstance(resultado, dict):
        return "Error", "El servicio no devolvió un resultado válido."

    if resultado.get("error"):
        return "Error", resultado.get("error", "")

    codigo_fase = str(codigo_fase or "").upper()

    if codigo_fase == "C":
        if resultado.get("observaciones") or resultado.get("advertencias"):
            return "Revisar", "Verificación completada con observaciones."

    return "Correcto", resultado.get("mensaje", "Fase ejecutada correctamente.")


def _gc_guardar_estado_fase(codigo_fase, fecha, resultado):
    conexion = request.form.get("conexion", "local")
    estado, detalle = _gc_estado_desde_resultado(codigo_fase, resultado)

    _gc_state_service().actualizar_fase(
        fecha=fecha,
        conexion=conexion,
        codigo=codigo_fase,
        estado=estado,
        detalle=detalle,
        tiene_detalle=True,
    )


def _gc_fases_con_estado(fecha, conexion):
    estados = _gc_state_service().obtener_estados(fecha, conexion)
    return GestionConsolidadaUiService().obtener_fases(estados)


@gestion_consolidada_bp.route("/gestion-consolidada", methods=["GET"])
@gestion_consolidada_bp.route("/consolidar-gestion-v2", methods=["GET"])
def vista_gestion_consolidada():
    embedded = request.args.get("embedded", "0") == "1"
    fecha = request.args.get("fecha", "20260429")
    conexion = request.args.get("conexion", "local")
    return render_template(
        "gestion_consolidada.html",
        embedded=embedded,
        fecha_proceso=fecha,
        conexion=conexion,
        gc_fases=_gc_fases_con_estado(fecha, conexion),
    )


@gestion_consolidada_bp.route("/accion/gestion-consolidada/reiniciar-estado", methods=["POST"])
def accion_gestion_consolidada_reiniciar_estado():
    fecha = request.form.get("fecha", "20260429")
    conexion = request.form.get("conexion", "local")

    _gc_state_service().reiniciar(fecha, conexion)

    return jsonify(
        {
            "ok": True,
            "fecha": fecha,
            "conexion": conexion,
            "fases": _gc_fases_con_estado(fecha, conexion),
        }
    )


@gestion_consolidada_bp.route("/accion/gestion-consolidada/estado", methods=["POST"])
def accion_gestion_consolidada_estado():
    fecha = request.form.get("fecha", "20260429")
    conexion = request.form.get("conexion", "local")

    return jsonify(
        {
            "ok": True,
            "fecha": fecha,
            "conexion": conexion,
            "fases": _gc_fases_con_estado(fecha, conexion),
        }
    )


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

    _gc_guardar_estado_fase("A", fecha, resultado)
    return render_preparar_proceso(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/unir", methods=["POST"])
def accion_gestion_consolidada_unir():
    fecha = request.form.get("fecha", "")

    resultado = unir_archivos_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("B", fecha, resultado)
    return render_unir_archivos_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/verificar-calidad", methods=["POST"])
def accion_gestion_consolidada_verificar_calidad():
    fecha = request.form.get("fecha", "")

    resultado = verificar_calidad_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("C", fecha, resultado)
    return render_verificar_calidad_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/ajuste-no-contestan", methods=["POST"])
def accion_gestion_consolidada_ajuste_no_contestan():
    fecha = request.form.get("fecha", "")
    porcentaje = request.form.get("porcentaje_no_contestan", "12")

    resultado = aplicar_ajuste_no_contestan_gestion(_data_dir(), fecha, porcentaje)

    _gc_guardar_estado_fase("D", fecha, resultado)
    return render_ajuste_no_contestan_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/limpiar-nota", methods=["POST"])
def accion_gestion_consolidada_limpiar_nota():
    fecha = request.form.get("fecha", "")

    resultado = limpiar_nota_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("E", fecha, resultado)
    return render_limpiar_nota_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/compromiso", methods=["POST"])
def accion_gestion_consolidada_compromiso():
    fecha = request.form.get("fecha", "")

    resultado = procesar_compromiso_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("F", fecha, resultado)
    return render_compromiso_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/archivo-final", methods=["POST"])
def accion_gestion_consolidada_archivo_final():
    fecha = request.form.get("fecha", "")

    resultado = generar_archivo_final_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("G", fecha, resultado)
    return render_archivo_final_gestion(resultado)



@gestion_consolidada_bp.route("/accion/gestion-consolidada/archivos-generados", methods=["POST"])
def accion_gestion_consolidada_archivos_generados():
    fecha = request.form.get("fecha", "")

    resultado = listar_archivos_generados_gestion(_data_dir(), fecha)

    _gc_guardar_estado_fase("H", fecha, resultado)
    return render_archivos_generados_gestion(resultado)



# === CONSOLIDAR_V2_MOSTRAR_AUDITORIA_SERVICIO_BEGIN ===

def _gc_fase_i_html_auditoria_servicio(resultado):
    """
    Renderiza la auditoría interna devuelta por cargar_informacion_gestion_sql.
    """
    auditoria = []

    if isinstance(resultado, dict):
        auditoria = resultado.get("auditoria_servicio") or []

    if not auditoria:
        return (
            "<section class='gc-fase-i-servicio-box gc-fase-i-servicio-warning'>"
            "<h3>🔎 Auditoría interna del servicio</h3>"
            "<p>No se recibió auditoría interna del servicio. "
            "Esto indica que el patch de medición interna aún no está activo dentro de "
            "<code>cargar_informacion_gestion_sql</code> o que el resultado no está devolviendo "
            "el campo <code>auditoria_servicio</code>.</p>"
            "</section>"
        )

    rows = []

    for item in auditoria:
        rows.append(
            "<tr>"
            f"<td>{item.get('paso', '')}</td>"
            f"<td>{item.get('inicio', '')}</td>"
            f"<td>{item.get('fin', '')}</td>"
            f"<td class='gc-fase-i-tiempo-num'>{item.get('segundos', '')}</td>"
            f"<td>{item.get('detalle', '')}</td>"
            "</tr>"
        )

    total = sum(
        float(x.get("segundos") or 0)
        for x in auditoria
        if not str(x.get("paso", "")).lower().startswith("total")
    )

    return (
        "<section class='gc-fase-i-servicio-box'>"
        "<h3>🔎 Auditoría interna del servicio — cargar_informacion_gestion_sql</h3>"
        "<table class='gc-fase-i-servicio-table'>"
        "<thead>"
        "<tr>"
        "<th>Paso interno</th>"
        "<th>Inicio</th>"
        "<th>Fin</th>"
        "<th>Segundos</th>"
        "<th>Detalle</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "".join(rows)
        + "<tr class='gc-fase-i-tiempo-total'>"
        "<td><b>Total interno sin duplicar</b></td>"
        "<td></td>"
        "<td></td>"
        f"<td class='gc-fase-i-tiempo-num'><b>{round(total, 3)}</b></td>"
        "<td>Suma de pasos internos, excluyendo filas tipo Total.</td>"
        "</tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )


def _gc_fase_i_adjuntar_auditoria_servicio(response, resultado):
    html = _gc_fase_i_html_auditoria_servicio(resultado)
    return _gc_fase_i_append_html(response, html)

# === CONSOLIDAR_V2_MOSTRAR_AUDITORIA_SERVICIO_END ===

@gestion_consolidada_bp.route("/accion/gestion-consolidada/cargar-sql", methods=["POST"])

def accion_gestion_consolidada_cargar_sql():
    auditoria = []

    inicio_total_perf = _gc_fase_i_perf_now()
    inicio_total_clock = _gc_fase_i_clock_now()

    # 1. Parámetros recibidos desde la pantalla
    inicio_params_perf = _gc_fase_i_perf_now()
    inicio_params_clock = _gc_fase_i_clock_now()

    fecha = request.form.get("fecha", "")
    conexion = request.form.get("conexion", "local")

    _gc_fase_i_add_timing(
        auditoria,
        "Lectura de parámetros",
        inicio_params_perf,
        inicio_params_clock,
        f"fecha={fecha}; conexion={conexion}",
    )

    # 2. Servicio principal de carga SQL
    inicio_servicio_perf = _gc_fase_i_perf_now()
    inicio_servicio_clock = _gc_fase_i_clock_now()

    resultado = cargar_informacion_gestion_sql(_data_dir(), fecha, conexion)

    _gc_fase_i_add_timing(
        auditoria,
        "Ejecución servicio cargar_informacion_gestion_sql",
        inicio_servicio_perf,
        inicio_servicio_clock,
        "Aquí se mide lectura, validación y carga SQL interna de la Fase I.",
    )

    # 3. Renderizado de respuesta
    inicio_render_perf = _gc_fase_i_perf_now()
    inicio_render_clock = _gc_fase_i_clock_now()

    response = render_carga_sql_gestion(resultado)
    _gc_guardar_estado_fase("I", fecha, resultado)

    _gc_fase_i_add_timing(
        auditoria,
        "Renderizado de resultado",
        inicio_render_perf,
        inicio_render_clock,
        "Construcción visual de la respuesta de Fase I.",
    )

    # 4. Total general de esta ruta
    _gc_fase_i_add_timing(
        auditoria,
        "Tiempo total ruta Fase I",
        inicio_total_perf,
        inicio_total_clock,
        "Incluye parámetros, servicio y renderizado.",
    )

    html = _gc_fase_i_html_tiempos(auditoria)

    response = _gc_fase_i_append_html(response, html)
    response = _gc_fase_i_adjuntar_auditoria_servicio(response, resultado)

    return response

