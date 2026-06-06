from __future__ import annotations

from flask import Blueprint, render_template, request

from app.services.integral_v2_phase_service import IntegralPhaseTimer, ejecutar_placeholder

integral_diario_v2_bp = Blueprint("integral_diario_v2", __name__)


@integral_diario_v2_bp.get("/integral-diario-v2")
def vista_integral_diario_v2():
    return render_template("integral_diario_v2/index.html")


@integral_diario_v2_bp.post("/accion/integral-diario-v2/contexto")
def accion_integral_diario_v2_contexto():
    from flask import render_template, request
    from app.services.integral_connection_service import construir_contexto_integral_v2

    contexto = construir_contexto_integral_v2(request.form)
    return render_template(
        "integral_diario_v2/partials/_context_summary.html",
        contexto=contexto,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/entidades")
def accion_integral_diario_v2_entidades():
    from flask import render_template, request
    from app.services.integral_v2_entidades_service import obtener_entidades_integral_v2

    resultado = obtener_entidades_integral_v2(request.form)
    status_code = 200 if resultado.get("ok") else 500

    return (
        render_template(
            "integral_diario_v2/partials/_entidades_resultado.html",
            resultado=resultado,
        ),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/archivos")
def accion_integral_diario_v2_archivos():
    from flask import render_template, request
    from app.services.integral_v2_archivo_service import gestionar_archivo_integral_v2

    resultado = gestionar_archivo_integral_v2(request.form)
    status_code = 200 if resultado.get("estado") == "Correcto" else 409

    return (
        render_template("integral_diario_v2/partials/_archivo_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/validar-archivo")
def accion_integral_diario_v2_validar_archivo():
    from flask import render_template, request
    from app.services.integral_v2_comparacion_service import comparar_entidades_integral_v2

    resultado = comparar_entidades_integral_v2(request.form)

    # Alias antiguo de Fase D. Mantiene contrato nuevo.
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template(
            "integral_diario_v2/partials/_comparar_entidades_resultado.html",
            resultado=resultado,
        ),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/ejecutar-sql")
def accion_integral_diario_v2_ejecutar_sql():
    from flask import render_template, request
    from app.services.integral_v2_sql_limpieza_service import ejecutar_sql_limpieza_integral_v2

    resultado = ejecutar_sql_limpieza_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_sql_limpieza_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/fase-contexto")
def accion_integral_diario_v2_fase_contexto():
    from flask import render_template, request
    from app.services.integral_connection_service import construir_contexto_integral_v2
    from app.services.integral_v2_phase_service import IntegralPhaseTimer

    with IntegralPhaseTimer("A", "Cargar contexto") as resultado:
        contexto = construir_contexto_integral_v2(request.form)

        ok_items = [
            contexto.get("servidor_estado") == "ok",
            contexto.get("origen_estado") == "ok",
            contexto.get("aster_estado") == "ok",
            contexto.get("vencorp_estado") == "ok",
        ]

        resultado.estado = "Correcto" if all(ok_items) else "Revisar"
        resultado.mensaje = "Contexto cargado. La pantalla queda lista para ejecutar entidades, archivo y procesamiento."
        resultado.registros_entrada = "-"
        resultado.registros_salida = "-"
        resultado.detalle = {
            "Servidor": contexto.get("servidor", ""),
            "Origen": contexto.get("origen", ""),
            "Tablas": contexto.get("tablas", ""),
            "Fecha SQL": contexto.get("fecha_sql", ""),
            "Fecha archivo": contexto.get("fecha_ddmmaaaa", ""),
            "Mes gestión": contexto.get("mes_gestion_codigo", ""),
            "Aster": contexto.get("aster_texto", ""),
            "Vencorp": contexto.get("vencorp_texto", ""),
        }

        contexto_tabla = {
            "servidor": contexto.get("servidor", ""),
            "origen": contexto.get("origen", ""),
            "tablas": contexto.get("tablas", ""),
            "aster_texto": contexto.get("aster_texto", ""),
            "vencorp_texto": contexto.get("vencorp_texto", ""),
            "aster_estado_texto": "Activo" if contexto.get("aster_estado") == "ok" else "Sin conexión",
            "vencorp_estado_texto": "Activo" if contexto.get("vencorp_estado") == "ok" else "Sin conexión",
            "fecha_sql": contexto.get("fecha_sql", ""),
            "fecha_ddmmaaaa": contexto.get("fecha_ddmmaaaa", ""),
            "mes_gestion_codigo": contexto.get("mes_gestion_codigo", ""),
        }

    return render_template(
        "integral_diario_v2/partials/_contexto_resultado.html",
        resultado=resultado,
        contexto=contexto_tabla,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/sincronizar-origen")
def accion_integral_diario_v2_sincronizar_origen():
    from flask import render_template, request
    from app.services.integral_v2_sync_origen_service import sincronizar_origen_integral_v2

    resultado = sincronizar_origen_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_sync_origen_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/gestionar-archivo")
def accion_integral_diario_v2_gestionar_archivo():
    from flask import render_template, request
    from app.services.integral_v2_archivo_service import gestionar_archivo_integral_v2

    resultado = gestionar_archivo_integral_v2(request.form)
    status_code = 200 if resultado.get("estado") == "Correcto" else 409

    return (
        render_template("integral_diario_v2/partials/_archivo_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/cargar-tabla-inicial")
def accion_integral_diario_v2_cargar_tabla_inicial():
    from flask import render_template, request
    from app.services.integral_v2_carga_inicial_service import cargar_tabla_inicial_integral_v2

    resultado = cargar_tabla_inicial_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_carga_inicial_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/copiar-finales")
def accion_integral_diario_v2_copiar_finales():
    resultado = ejecutar_placeholder(
        "I",
        "Copiar archivos finales",
        "Esta fase copiará archivos oficiales a rutas finales de red.",
        {
            "Procesado": "Cobranzas Integrales Procesado",
            "Microvoz": "Microvoz_MM_YY",
        },
    )
    return render_template("integral_diario_v2/partials/_fase_resultado.html", resultado=resultado)


@integral_diario_v2_bp.post("/accion/integral-diario-v2/eliminar-duplicidad-fase-e")
def accion_integral_diario_v2_eliminar_duplicidad_fase_e():
    from flask import render_template, request
    from app.services.integral_v2_sync_origen_service import eliminar_duplicidad_fase_e_integral_v2

    resultado = eliminar_duplicidad_fase_e_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_fase_e_eliminar_duplicidad_resultado.html", resultado=resultado),
        status_code,
    )

@integral_diario_v2_bp.post("/accion/integral-diario-v2/eliminar-duplicidad-fase-f")
def accion_integral_diario_v2_eliminar_duplicidad_fase_f():
    from flask import render_template, request
    from app.services.integral_v2_carga_inicial_service import eliminar_duplicidad_fase_f_integral_v2

    resultado = eliminar_duplicidad_fase_f_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_fase_f_eliminar_duplicidad_resultado.html", resultado=resultado),
        status_code,
    )

# --- Fase H: Generar archivo oficial real ---
@integral_diario_v2_bp.post("/accion/integral-diario-v2/generar-oficial")
def accion_integral_diario_v2_generar_oficial():
    from flask import render_template, request
    from app.services.integral_v2_oficial_service import generar_oficial_integral_v2

    resultado = generar_oficial_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_oficial_resultado.html", resultado=resultado),
        status_code,
    )


# --- Fase H: Alias compatible con botón actual del panel central ---
@integral_diario_v2_bp.post("/accion/integral-diario-v2/generar-oficiales")
def accion_integral_diario_v2_generar_oficiales():
    from flask import render_template, request
    from app.services.integral_v2_oficial_service import generar_oficial_integral_v2

    resultado = generar_oficial_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_oficial_resultado.html", resultado=resultado),
        status_code,
    )

# --- Fase I: Vencorp / Cubo - carga real a BD; cubo en stand by ---
def _integral_v2_render_fase_i_vencorp_bd():
    from flask import render_template, request
    from app.services.integral_v2_vencorp_service import cargar_vencorp_integral_v2

    resultado = cargar_vencorp_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_vencorp_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/vencorp-cubo")
def accion_integral_diario_v2_vencorp_cubo():
    return _integral_v2_render_fase_i_vencorp_bd()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/cargar-vencorp")
def accion_integral_diario_v2_cargar_vencorp():
    return _integral_v2_render_fase_i_vencorp_bd()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/vencorp")
def accion_integral_diario_v2_vencorp():
    return _integral_v2_render_fase_i_vencorp_bd()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/eliminar-duplicidad-fase-i")
def accion_integral_diario_v2_eliminar_duplicidad_fase_i():
    from flask import render_template, request
    from app.services.integral_v2_vencorp_service import eliminar_duplicidad_fase_i_integral_v2

    resultado = eliminar_duplicidad_fase_i_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_fase_i_eliminar_duplicidad_resultado.html", resultado=resultado),
        status_code,
    )

# --- Fase I: alias real para botón cargar-vencorp-cubo ---
@integral_diario_v2_bp.post("/accion/integral-diario-v2/cargar-vencorp-cubo")
def accion_integral_diario_v2_cargar_vencorp_cubo_real():
    from flask import render_template, request
    from app.services.integral_v2_vencorp_service import cargar_vencorp_integral_v2

    resultado = cargar_vencorp_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_vencorp_resultado.html", resultado=resultado),
        status_code,
    )

# --- Fase J: Validación final / copia final real ---
def _integral_v2_render_validacion_final():
    from flask import render_template, request
    from app.services.integral_v2_validacion_final_service import validar_final_integral_v2

    resultado = validar_final_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_validacion_final_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/validacion-final")
def accion_integral_diario_v2_validacion_final():
    return _integral_v2_render_validacion_final()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/copiar-validar-final")
def accion_integral_diario_v2_copiar_validar_final():
    return _integral_v2_render_validacion_final()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/validar-final")
def accion_integral_diario_v2_validar_final():
    return _integral_v2_render_validacion_final()

# --- Fase B: preparar entorno / carpetas y rutas ---
def _integral_v2_render_preparar_entorno():
    from flask import render_template, request
    from app.services.integral_v2_entorno_service import preparar_entorno_integral_v2

    resultado = preparar_entorno_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template("integral_diario_v2/partials/_entorno_resultado.html", resultado=resultado),
        status_code,
    )


@integral_diario_v2_bp.post("/accion/integral-diario-v2/preparar-entorno")
def accion_integral_diario_v2_preparar_entorno():
    return _integral_v2_render_preparar_entorno()


@integral_diario_v2_bp.post("/accion/integral-diario-v2/carpetas-rutas")
def accion_integral_diario_v2_carpetas_rutas():
    return _integral_v2_render_preparar_entorno()

# --- Fase D: Obtener y comparar entidades ---
@integral_diario_v2_bp.post("/accion/integral-diario-v2/comparar-entidades")
def accion_integral_diario_v2_comparar_entidades():
    from flask import render_template, request
    from app.services.integral_v2_comparacion_service import comparar_entidades_integral_v2

    resultado = comparar_entidades_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template(
            "integral_diario_v2/partials/_comparar_entidades_resultado.html",
            resultado=resultado,
        ),
        status_code,
    )


# --- Fase D: aplicar entidades comparadas seleccionadas ---
@integral_diario_v2_bp.post("/accion/integral-diario-v2/aplicar-entidades-comparadas")
def accion_integral_diario_v2_aplicar_entidades_comparadas():
    from flask import render_template, request
    from app.services.integral_v2_entidades_seleccionadas_service import aplicar_entidades_comparadas_integral_v2

    resultado = aplicar_entidades_comparadas_integral_v2(request.form)
    status_code = 500 if resultado.get("estado") == "Error" else 200

    return (
        render_template(
            "integral_diario_v2/partials/_entidades_seleccionadas_resultado.html",
            resultado=resultado,
        ),
        status_code,
    )
