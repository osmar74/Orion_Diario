"""
Blueprint para Gestión Diaria ASTER.

Fase A:
- Captura del total diario por OCR.
- Captura manual del total general.
"""

import base64
import json
import os
import re

from datetime import datetime
from html import escape
from typing import Any

from app.config import SQL_LOCAL, SQL_REMOTO

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor
from app.services.aster_file_service import (
    buscar_archivo_normalizado_aster_en_disco,
    copiar_archivo_aster,
)

from app.services.aster_normalization_service import normalizar_archivo_aster
from app.services.aster_entity_service import analizar_entidades_excel_aster
from app.services.aster_sql_entity_service import consultar_entidades_sql_aster

from app.services.aster_classification_service import (
    aplicar_exclusiones_aster,
    guardar_clasificacion_aster,
    preparar_depuracion_aster,
)

from app.services.aster_reconciliation_service import (
    conciliar_entidades_aster,
    normalizar_entidades_excel_aster,
    obtener_entidades_sql_validables_aster as obtener_entidades_sql_validables_aster_service,
)

from app.services.aster_history_service import (
    obtener_historial_cargas_aster,
    registrar_historial_carga_aster,
)

from app.services.aster_sqlserver_service import (
    obtener_cadena_sqlserver_aster as obtener_cadena_sqlserver_aster_service,
    obtener_columnas_sqlserver_tabla,
    probar_conexion_tabla_sqlserver_aster,
)

from app.services.aster_entities_export_service import (
    generar_excel_entidades_aster as generar_excel_entidades_aster_service,
    normalizar_entidades_filtradas_finales_aster,
)

from app.services.aster_insert_prepare_service import preparar_insercion_aster
from app.services.aster_insert_service import insertar_datos_aster
from app.services.aster_phase_i_prepare_service import (
    obtener_fecha_fase_i as obtener_fecha_fase_i_service,
    preparar_fase_i_aster,
    probar_conexiones_fase_i_aster,
)
from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster
from app.services.aster_gestion_export_service import generar_gestion_aster_fase_i
from app.services.aster_renderer_service import (
    render_archivo_aster,
    render_clasificacion_final_aster,
    render_conciliacion_aster,
    render_consulta_sql_aster,
    render_duplicados_aster,
    render_entidades_excel_aster,
    render_errores_validacion_insert_aster,
    render_exclusiones_aplicadas_aster,
    render_historial_cargas_aster,
    render_insert_ok_aster,
    render_normalizacion_aster,
    render_preparacion_insercion_aster,
    render_preparar_depuracion_aster,
    render_reporte_final_aster,
    render_total_aster,
    render_claves_invalidas_comentarios_fase_i,
    render_duplicados_comentarios_fase_i,
    render_gestion_aster_excel,
    render_preparacion_fase_i,
    render_reporte_fase_i,
)


aster_bp = Blueprint("aster", __name__)

RUTAS_ASTER_DEFAULT = [
    r"Z:\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"\\10.24.90.118\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_aster\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO"
]

ASTER_TABLA_INSERCION = "aster_dia_nc"
ASTER_SCHEMA_INSERCION = "dbo"
ASTER_BASE_INSERCION = "Aster_Api"

ASTER_HISTORIAL_DB = os.path.join(DATA_DIR, "aster_load_history.db")

ASTER_FASE_I_BASE = "Aster_Api"
ASTER_FASE_I_SCHEMA = "dbo"
ASTER_FASE_I_TABLA_USUARIOS = "usuarios"
ASTER_FASE_I_TABLA_COMENTARIOS = "comentarios"

ASTER_MYSQL_DB_USUARIOS = os.getenv("ASTER_MYSQL_DB_USUARIOS", "usuarios")
ASTER_MYSQL_DB_GESTION = os.getenv("ASTER_MYSQL_DB_GESTION", "gestioncomercial")


def _extraer_total_aster_desde_texto(ocr: OCRProcessor, texto: str) -> int | None:
    """
    Intenta obtener un total ASTER desde texto OCR usando métodos reutilizables.

    Se prueban métodos genéricos porque el formato de WhatsApp puede variar.
    """
    numeros = ocr.extraer_totales_generico(texto)

    if numeros:
        return int(numeros[0])

    for palabra_clave in ["Total general", "Total", "ASTER", "Aster"]:
        numero = ocr.extraer_numero_cercano(texto, palabra_clave)

        if numero:
            return int(numero)

    return None







def _obtener_entidades_excel_aster_desde_sesion() -> list[str]:
    """
    Compatibilidad temporal.
    La normalización real vive en app.services.aster_reconciliation_service.
    """
    return normalizar_entidades_excel_aster(
        session.get("aster_entidades_excel") or []
    )


def _obtener_entidades_sql_validables_aster() -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_reconciliation_service.
    """
    return obtener_entidades_sql_validables_aster_service(
        cobranza=session.get("aster_bases_cobranza") or [],
        integral=session.get("aster_bases_integral") or [],
        no_seleccionadas=session.get("aster_bases_no_seleccionadas") or [],
    )






def _obtener_columnas_sqlserver_aster(conexion: str) -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sqlserver_service.
    """
    return obtener_columnas_sqlserver_tabla(
        conexion=conexion,
        sql_local=SQL_LOCAL,
        sql_remoto=SQL_REMOTO,
        base=ASTER_BASE_INSERCION,
        schema=ASTER_SCHEMA_INSERCION,
        tabla=ASTER_TABLA_INSERCION,
    )


def _obtener_cadena_sqlserver_aster(conexion: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sqlserver_service.
    """
    return obtener_cadena_sqlserver_aster_service(
        conexion=conexion,
        sql_local=SQL_LOCAL,
        sql_remoto=SQL_REMOTO,
        database_default=ASTER_BASE_INSERCION,
    )
    





def _obtener_fecha_proceso_aster() -> str:
    """
    Obtiene la fecha del proceso ASTER en formato YYYYMMDD.
    """
    fecha = str(
        session.get("aster_fecha_proceso")
        or session.get("ultima_fecha_aster")
        or session.get("aster_fecha_sql")
        or ""
    ).strip()

    fecha_limpia = re.sub(r"[^0-9]", "", fecha)

    if len(fecha_limpia) >= 8:
        return fecha_limpia[:8]

    return datetime.now().strftime("%Y%m%d")


def _buscar_archivo_normalizado_aster_en_disco(fecha_yyyymmdd: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_file_service.
    """
    return buscar_archivo_normalizado_aster_en_disco(
        DATA_DIR,
        fecha_yyyymmdd,
    )

def _resolver_archivo_aster_normalizado() -> str:
    """
    Devuelve la ruta del archivo normalizado ASTER que deben usar
    Fase D y fases posteriores.

    Regla:
    - Primero usa session["aster_archivo_normalizado"] si existe físicamente.
    - Si no existe en sesión, busca en carpeta Normalizado.
    - No permite usar Archivo_Original.
    """
    ruta_sesion = str(session.get("aster_archivo_normalizado") or "").strip()

    if ruta_sesion and os.path.isfile(ruta_sesion):
        return ruta_sesion

    fecha_yyyymmdd = str(session.get("aster_fecha_proceso") or "").strip()

    if not fecha_yyyymmdd:
        fecha_yyyymmdd = _obtener_fecha_proceso_aster()

    ruta_disco = _buscar_archivo_normalizado_aster_en_disco(fecha_yyyymmdd)

    if ruta_disco and os.path.isfile(ruta_disco):
        session["aster_archivo_normalizado"] = ruta_disco
        return ruta_disco

    raise FileNotFoundError(
        "No se encontró archivo ASTER normalizado. "
        "Debe ejecutar primero la Fase C: Normalización de encabezados."
    )
    

def _obtener_entidades_filtradas_finales_aster() -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_entities_export_service.
    """
    return normalizar_entidades_filtradas_finales_aster(
        entidades_validadas=session.get("aster_entidades_sql_validadas") or [],
        cobranza=session.get("aster_bases_cobranza") or [],
        integral=session.get("aster_bases_integral") or [],
        no_seleccionadas=session.get("aster_bases_no_seleccionadas") or [],
    )


def _generar_excel_entidades_aster(
    fecha_yyyymmdd: str,
) -> tuple[str, str, int]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_entities_export_service.
    """
    entidades = _obtener_entidades_filtradas_finales_aster()

    resultado = generar_excel_entidades_aster_service(
        data_dir=DATA_DIR,
        fecha_yyyymmdd=fecha_yyyymmdd,
        entidades=entidades,
    )

    if not resultado.get("success"):
        raise RuntimeError(
            str(resultado.get("error", "Error generando Excel de entidades ASTER."))
        )

    return (
        str(resultado["ruta_archivo"]),
        str(resultado["nombre_archivo"]),
        int(resultado["total_entidades"]),
    )




def _normalizar_fecha_yyyymmdd_aster_para_fase_i(fecha_raw: str) -> str:
    """Normaliza fecha a YYYYMMDD sin depender del frontend."""
    fecha_limpia = "".join(ch for ch in str(fecha_raw or "") if ch.isdigit())

    if len(fecha_limpia) >= 8:
        return fecha_limpia[:8]

    raise ValueError(f"Fecha ASTER inválida para Fase I: {fecha_raw}")


def _ruta_excel_entidades_aster_para_fase_i(fecha_raw: str) -> str:
    """Ruta canónica del Excel de entidades que consume Fase I."""
    fecha_limpia = _normalizar_fecha_yyyymmdd_aster_para_fase_i(fecha_raw)

    return os.path.join(
        DATA_DIR,
        fecha_limpia,
        "Aster",
        f"aster_{fecha_limpia}",
        "Entidades",
        f"entidades_aster_{fecha_limpia}.xlsx",
    )


def _asegurar_excel_entidades_aster_para_fase_i(fecha_raw: str) -> tuple[str, str, int]:
    """
    Garantiza que exista entidades_aster_YYYYMMDD.xlsx antes de Fase I.

    La fuente sigue siendo la información validada en sesión por las fases
    previas ASTER. No altera ORION ni otras fases.
    """
    ruta_esperada = _ruta_excel_entidades_aster_para_fase_i(fecha_raw)

    if os.path.exists(ruta_esperada):
        return (
            ruta_esperada,
            os.path.basename(ruta_esperada),
            int(session.get("aster_fase_i_total_entidades") or 0),
        )

    ruta_generada, nombre_generado, total_entidades = _generar_excel_entidades_aster(
        fecha_raw
    )

    if not ruta_generada or not os.path.exists(ruta_generada):
        raise ValueError(
            "No se pudo generar el archivo de entidades ASTER requerido por Fase I. "
            "Revise que las fases de Entidades, Consulta SQL, Depuración y Conciliación "
            "hayan dejado entidades validadas en sesión."
        )

    session["aster_reporte_entidades"] = ruta_generada
    session["aster_fase_i_ruta_entidades"] = ruta_generada
    session["aster_fase_i_total_entidades"] = int(total_entidades or 0)

    return ruta_generada, nombre_generado, int(total_entidades or 0)

def _registrar_historial_carga_aster(
    fecha_proceso: str,
    archivo_excel: str,
    conexion: str,
    total_general_aster: int | None,
    filas_excel: int,
    registros_insertados: int,
    estado: str,
    mensaje: str,
    archivo_reporte_entidades: str = "",
    ruta_reporte_entidades: str = "",
) -> None:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_history_service.
    """
    registrar_historial_carga_aster(
        db_path=ASTER_HISTORIAL_DB,
        fecha_proceso=fecha_proceso,
        archivo_excel=archivo_excel,
        conexion=conexion,
        total_general_aster=total_general_aster,
        filas_excel=filas_excel,
        registros_insertados=registros_insertados,
        estado=estado,
        mensaje=mensaje,
        archivo_reporte_entidades=archivo_reporte_entidades,
        ruta_reporte_entidades=ruta_reporte_entidades,
    )


def _obtener_historial_cargas_aster(limite: int = 30) -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_history_service.
    """
    return obtener_historial_cargas_aster(
        db_path=ASTER_HISTORIAL_DB,
        limite=limite,
    )








@aster_bp.route("/accion/aster-ocr-subir", methods=["POST"])
def accion_aster_ocr_subir():
    """
    Recibe imágenes de WhatsApp y trata de detectar el total diario ASTER por OCR.
    """
    fecha = request.form.get("fecha", "202605_12")
    archivos = request.files.getlist("imagenes")

    archivos_validos = [
        archivo
        for archivo in archivos
        if (archivo.filename or "").strip()
    ]

    if not archivos_validos:
        return "<div class='log-line error'>❌ No se seleccionó ninguna imagen ASTER.</div>"

    carpeta_destino = os.path.join(
        DATA_DIR,
        f"orion_{fecha}",
        "Reporte_Imagen_ASTER",
    )
    os.makedirs(carpeta_destino, exist_ok=True)

    log_srv = obtener_log_service()
    ocr = OCRProcessor(TESSERACT_PATH, log_service=log_srv)

    total_detectado: int | None = None
    previews: list[tuple[str, str]] = []
    archivos_guardados: list[str] = []

    for idx, archivo in enumerate(archivos_validos):
        nombre_original = archivo.filename or ""

        if not nombre_original.strip():
            continue

        nombre_base = secure_filename(nombre_original)

        if not nombre_base:
            continue

        nombre_unico = f"aster_{idx}_{nombre_base}"
        ruta_guardada = os.path.join(carpeta_destino, nombre_unico)

        archivo.save(ruta_guardada)
        archivos_guardados.append(nombre_unico)

        if len(previews) < 3:
            with open(ruta_guardada, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                previews.append((nombre_unico, img_b64))

        texto = ocr.extraer_texto(ruta_guardada)
        total_archivo = _extraer_total_aster_desde_texto(ocr, texto)

        if total_archivo is not None:
            total_detectado = total_archivo
            break

    session["total_aster"] = total_detectado
    session["ultima_fecha_aster"] = fecha

    html = render_total_aster(
        total=total_detectado,
        origen="OCR WhatsApp ASTER",
        previews=previews,
    )

    if archivos_guardados:
        html += (
            "<details class='archivos-guardados' style='margin-top:10px;'>"
            f"<summary>📁 Archivos guardados ({len(archivos_guardados)})</summary>"
            "<ul>"
        )

        for nombre in archivos_guardados:
            html += f"<li>{nombre}</li>"

        html += "</ul></details>"

    return html


@aster_bp.route("/accion/aster-consolidar-total", methods=["POST"])
def accion_aster_consolidar_total():
    """
    Guarda manualmente el total diario ASTER en sesión.
    """
    try:
        total_raw = request.form.get("total_aster", "").strip()

        if not total_raw:
            return "<div class='log-line error'>❌ Debe ingresar el Total general ASTER.</div>"

        total = int(total_raw)

        if total < 0:
            return "<div class='log-line error'>❌ El Total general ASTER no puede ser negativo.</div>"

        session["total_aster"] = total

        return render_total_aster(
            total=total,
            origen="Ingreso manual",
            previews=[],
        )

    except ValueError:
        return "<div class='log-line error'>❌ El Total general ASTER debe ser numérico.</div>"

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error al guardar total ASTER: {exc}</div>"


@aster_bp.route("/accion/aster-buscar-archivo", methods=["POST"])
def accion_aster_buscar_archivo():
    """
    Busca el archivo After del día y lo copia a Archivo_Original.

    La lógica de búsqueda y copia vive en:
    app.services.aster_file_service
    """
    try:
        fecha_raw = request.form.get("fecha_proceso", "").strip()
        ruta_base_usuario = request.form.get("ruta_base", "").strip()

        if not fecha_raw:
            return "<div class='log-line error'>❌ Debe ingresar la fecha del proceso ASTER.</div>"

        resultado = copiar_archivo_aster(
            data_dir=DATA_DIR,
            fecha_raw=fecha_raw,
            ruta_base_usuario=ruta_base_usuario,
            rutas_default=RUTAS_ASTER_DEFAULT,
        )

        if not resultado.get("success"):
            fecha_yyyymmdd = str(resultado.get("fecha_yyyymmdd") or "")
            rutas_busqueda = resultado.get("rutas_busqueda") or []

            rutas_html = "<br>".join(
                f"<code>{escape(str(ruta))}</code>"
                for ruta in rutas_busqueda
            )

            return f"""
            <div class='log-line error'>
                ❌ No se encontró archivo ASTER para la fecha {escape(fecha_yyyymmdd)}.
            </div>
            <div class='log-line warning'>
                Rutas revisadas:<br>{rutas_html}
            </div>
            """

        fecha_yyyymmdd = str(resultado["fecha_yyyymmdd"])
        ruta_origen = str(resultado["ruta_origen"])
        ruta_destino = str(resultado["ruta_destino"])
        nombre_archivo = str(resultado["nombre_archivo"])

        session["aster_fecha_proceso"] = fecha_yyyymmdd
        session["aster_archivo_origen"] = ruta_origen
        session["aster_archivo_copiado"] = ruta_destino

        return render_archivo_aster(
            fecha_yyyymmdd=fecha_yyyymmdd,
            ruta_origen=ruta_origen,
            ruta_destino=ruta_destino,
            nombre_archivo=nombre_archivo,
        )

    except ValueError as exc:
        return f"<div class='log-line error'>❌ {escape(str(exc))}</div>"

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error buscando archivo ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-normalizar-encabezados", methods=["POST"])
def accion_aster_normalizar_encabezados():
    """
    Normaliza encabezados del archivo ASTER copiado en Fase B.

    La lógica vive en:
    app.services.aster_normalization_service
    """
    try:
        ruta_archivo = request.form.get("ruta_archivo", "").strip()

        if not ruta_archivo:
            ruta_archivo = str(session.get("aster_archivo_copiado") or "")

        fecha_yyyymmdd = str(session.get("aster_fecha_proceso") or "").strip()

        resultado = normalizar_archivo_aster(
            data_dir=DATA_DIR,
            ruta_archivo=ruta_archivo,
            fecha_yyyymmdd=fecha_yyyymmdd,
        )

        if not resultado.get("success"):
            html = f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error normalizando archivo ASTER.")))}
            </div>
            """

            if resultado.get("ruta_archivo"):
                html += f"""
                <div class='log-line warning'>
                    Ruta: <code>{escape(str(resultado.get("ruta_archivo")))}</code>
                </div>
                """

            return html

        ruta_normalizado = str(resultado["ruta_normalizado"])
        columnas_originales = resultado["columnas_originales"]
        columnas_normalizadas = resultado["columnas_normalizadas"]

        session["aster_archivo_normalizado"] = ruta_normalizado
        session["aster_columnas_originales"] = columnas_originales
        session["aster_columnas_normalizadas"] = columnas_normalizadas

        return render_normalizacion_aster(
            ruta_archivo=ruta_normalizado,
            columnas_originales=columnas_originales,
            columnas_normalizadas=columnas_normalizadas,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error normalizando encabezados ASTER: {escape(str(exc))}</div>"
    

@aster_bp.route("/accion/aster-entidades-excel", methods=["POST"])
def accion_aster_entidades_excel():
    """
    Obtiene valores únicos de la columna Entidad del Excel ASTER normalizado.

    La lógica de análisis vive en:
    app.services.aster_entity_service
    """
    try:
        try:
            ruta_archivo = _resolver_archivo_aster_normalizado()
        except FileNotFoundError as exc:
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(exc))}
            </div>
            """

        resultado = analizar_entidades_excel_aster(ruta_archivo)

        if not resultado.get("success"):
            status = str(resultado.get("status") or "")

            if status == "archivo_no_existe":
                return f"""
                <div class='log-line error'>
                    ❌ {escape(str(resultado.get("error", "El archivo ASTER no existe.")))}
                </div>
                <div class='log-line warning'>
                    Ruta: <code>{escape(str(resultado.get("ruta_archivo", "")))}</code>
                </div>
                """

            if status == "sin_columna_entidad":
                columnas = resultado.get("columnas") or []

                columnas_html = "<br>".join(
                    f"<code>{escape(str(col))}</code>"
                    for col in columnas
                )

                return f"""
                <div class='log-line error'>
                    ❌ {escape(str(resultado.get("error", "No se encontró la columna Entidad.")))}
                </div>
                <div class='log-line warning'>
                    Columnas disponibles:<br>{columnas_html}
                </div>
                """

            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error analizando entidades ASTER.")))}
            </div>
            """

        conteo_entidades = resultado["conteo_entidades"]

        session["aster_entidades_excel"] = resultado["entidades"]
        session["aster_total_entidades_excel"] = resultado["total_entidades"]
        session["aster_total_registros_excel"] = resultado["total_registros"]

        return render_entidades_excel_aster(
            ruta_archivo=str(resultado["ruta_archivo"]),
            total_registros=int(resultado["total_registros"]),
            conteo_entidades=conteo_entidades,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error analizando entidades ASTER: {escape(str(exc))}</div>"
    

@aster_bp.route("/accion/aster-consulta-sql", methods=["POST"])
def accion_aster_consulta_sql():
    """
    Ejecuta consulta SQL/MySQL ASTER para obtener entidades del día.

    La lógica de consulta vive en:
    app.services.aster_sql_entity_service
    """
    try:
        fecha_raw = request.form.get("fecha_consulta", "").strip()

        if not fecha_raw:
            fecha_raw = str(
                session.get("aster_fecha_proceso")
                or session.get("ultima_fecha_aster")
                or ""
            )

        if not fecha_raw:
            return """
            <div class='log-line error'>
                ❌ Debe ingresar la fecha de consulta ASTER.
            </div>
            """

        resultado = consultar_entidades_sql_aster(fecha_raw)

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error ejecutando consulta SQL ASTER.")))}
            </div>
            """

        fecha_sql = str(resultado["fecha_sql"])
        resultados = resultado["resultados"]

        session["aster_fecha_sql"] = fecha_sql
        session["aster_resultados_sql"] = resultados
        session["aster_total_entidades_sql"] = resultado["total_entidades"]
        session["aster_total_registros_sql"] = resultado["total_registros"]

        return render_consulta_sql_aster(
            fecha_sql=fecha_sql,
            resultados=resultados,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error ejecutando consulta SQL ASTER: {escape(str(exc))}</div>"
    
 
@aster_bp.route("/accion/aster-conciliar-entidades", methods=["POST"])
def accion_aster_conciliar_entidades():
    """
    Compara entidades del Excel ASTER contra entidades SQL depuradas.

    La lógica de conciliación vive en:
    app.services.aster_reconciliation_service
    """
    try:
        entidades_excel = _obtener_entidades_excel_aster_desde_sesion()
        entidades_sql = _obtener_entidades_sql_validables_aster()

        if not entidades_excel:
            return """
            <div class='log-line error'>
                ❌ No hay entidades del Excel ASTER en sesión. Ejecute primero la Fase D.
            </div>
            """

        if not entidades_sql:
            return """
            <div class='log-line error'>
                ❌ No hay entidades SQL clasificadas en sesión. Ejecute primero la Fase F.
            </div>
            """

        resultado = conciliar_entidades_aster(
            entidades_excel=entidades_excel,
            entidades_sql=entidades_sql,
            entidades_no_tomar=set(),
        )

        session["aster_entidades_no_tomar"] = []

        if resultado.get("match_ok"):
            session["aster_informacion_verificada"] = True
            session["aster_entidades_sql_validadas"] = resultado.get(
                "entidades_sql_ajustadas",
                [],
            )
        else:
            session["aster_informacion_verificada"] = False
            session["aster_entidades_sql_validadas"] = []

        return render_conciliacion_aster(resultado)

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error conciliando entidades ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-ajustar-conciliacion", methods=["POST"])
def accion_aster_ajustar_conciliacion():
    """
    Aplica entidades SQL que no se tomarán en cuenta y vuelve a validar.

    La lógica de conciliación vive en:
    app.services.aster_reconciliation_service
    """
    try:
        entidades_excel = _obtener_entidades_excel_aster_desde_sesion()
        entidades_sql = _obtener_entidades_sql_validables_aster()

        entidades_no_tomar = {
            str(entidad).strip()
            for entidad in request.form.getlist("entidades_no_tomar")
            if str(entidad).strip()
        }

        resultado = conciliar_entidades_aster(
            entidades_excel=entidades_excel,
            entidades_sql=entidades_sql,
            entidades_no_tomar=entidades_no_tomar,
        )

        session["aster_entidades_no_tomar"] = sorted(entidades_no_tomar)

        if resultado.get("match_ok"):
            session["aster_informacion_verificada"] = True
            session["aster_entidades_sql_validadas"] = resultado.get(
                "entidades_sql_ajustadas",
                [],
            )
        else:
            session["aster_informacion_verificada"] = False
            session["aster_entidades_sql_validadas"] = []

        return render_conciliacion_aster(resultado)

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error ajustando conciliación ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-probar-conexion-insercion", methods=["POST"])
def accion_aster_probar_conexion_insercion():
    """
    Prueba conexión SQL Server ASTER para inserción.
    No inserta datos.

    La lógica de conexión vive en:
    app.services.aster_sqlserver_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        resultado = probar_conexion_tabla_sqlserver_aster(
            conexion=conexion,
            sql_local=SQL_LOCAL,
            sql_remoto=SQL_REMOTO,
            base=ASTER_BASE_INSERCION,
            schema=ASTER_SCHEMA_INSERCION,
            tabla=ASTER_TABLA_INSERCION,
        )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error verificando conexión ASTER.")))}
            </div>
            """

        tipo = "REMOTA - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - PRUEBAS"

        advertencia = ""

        if conexion == "remoto":
            advertencia = """
            <div class='log-line warning'>
                ⚠️ Esta conexión es REMOTA y corresponde a producción. No usar para pruebas.
            </div>
            """

        return f"""
        <div class='log-line success'>
            ✅ Conexión ASTER verificada correctamente.
        </div>
        {advertencia}
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                    Verificación de conexión ASTER
                </th>
            </tr>
            <tr>
                <td><b>Conexión</b></td>
                <td>{escape(tipo)}</td>
            </tr>
            <tr>
                <td><b>Base actual</b></td>
                <td>{escape(str(resultado.get("base_actual", "")))}</td>
            </tr>
            <tr>
                <td><b>Tabla destino</b></td>
                <td>{escape(f'{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}')}</td>
            </tr>
            <tr>
                <td><b>Columnas detectadas</b></td>
                <td>{escape(str(resultado.get("total_columnas", 0)))}</td>
            </tr>
        </table>
        """

    except Exception as exc:
        return f"""
        <div class='log-line error'>
            ❌ Error verificando conexión ASTER: {escape(str(exc))}
        </div>
        """


@aster_bp.route("/accion/aster-preparar-insercion", methods=["POST"])
def accion_aster_preparar_insercion():
    """
    Prepara inserción ASTER comparando Excel normalizado vs tabla SQL.
    No inserta datos.

    La lógica vive en:
    app.services.aster_insert_prepare_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        try:
            ruta_archivo = _resolver_archivo_aster_normalizado()
        except FileNotFoundError as exc:
            session["aster_preparacion_insercion_ok"] = False
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(exc))}
            </div>
            """

        columnas_sql = _obtener_columnas_sqlserver_aster(conexion)

        resultado = preparar_insercion_aster(
            ruta_archivo=ruta_archivo,
            columnas_sql=columnas_sql,
        )

        if not resultado.get("success"):
            session["aster_preparacion_insercion_ok"] = False

            status = str(resultado.get("status") or "")

            if status == "archivo_no_existe":
                return f"""
                <div class='log-line error'>
                    ❌ {escape(str(resultado.get("error", "El archivo ASTER no existe.")))}
                </div>
                <div class='log-line warning'>
                    Ruta: <code>{escape(str(resultado.get("ruta_archivo", "")))}</code>
                </div>
                """

            if status == "errores_validacion":
                return render_errores_validacion_insert_aster(
                    resultado.get("errores_validacion", [])
                )

            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error preparando inserción ASTER.")))}
            </div>
            """

        comparacion = resultado["comparacion"]

        session["aster_conexion_insercion"] = conexion
        session["aster_preparacion_insercion_ok"] = True
        session["aster_columnas_comparacion_sql"] = comparacion

        return render_preparacion_insercion_aster(
            conexion=conexion,
            tabla_destino=f"{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}",
            ruta_archivo=str(resultado["ruta_archivo"]),
            total_registros=int(resultado["total_registros"]),
            comparacion=comparacion,
        )

    except Exception as exc:
        session["aster_preparacion_insercion_ok"] = False
        return f"<div class='log-line error'>❌ Error preparando inserción ASTER: {escape(str(exc))}</div>"
    

@aster_bp.route("/accion/aster-insertar-datos", methods=["POST"])
def accion_aster_insertar_datos():
    """
    Inserta datos ASTER en SQL Server con validación anti-duplicados.

    La lógica de inserción vive en:
    app.services.aster_insert_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()
        confirmar_remoto = request.form.get("confirmar_remoto", "").strip().upper()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        if conexion == "remoto" and confirmar_remoto != "SI":
            return """
            <div class='log-line error'>
                ❌ Inserción remota bloqueada. REMOTO es producción.
            </div>
            <div class='log-line warning'>
                Para insertar en remoto debe confirmar explícitamente. No use remoto para pruebas.
            </div>
            """

        if not bool(session.get("aster_informacion_verificada")):
            return """
            <div class='log-line error'>
                ❌ No se puede insertar. Primero debe completar Fase G con Información Verificada.
            </div>
            """

        if not bool(session.get("aster_preparacion_insercion_ok")):
            return """
            <div class='log-line error'>
                ❌ No se puede insertar. Primero debe ejecutar Preparar inserción ASTER sin errores.
            </div>
            """

        try:
            ruta_archivo = _resolver_archivo_aster_normalizado()
        except FileNotFoundError as exc:
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(exc))}
            </div>
            """

        columnas_sql = _obtener_columnas_sqlserver_aster(conexion)
        cadena = _obtener_cadena_sqlserver_aster(conexion)

        resultado = insertar_datos_aster(
            ruta_archivo=ruta_archivo,
            columnas_sql=columnas_sql,
            cadena_sqlserver=cadena,
            base=ASTER_BASE_INSERCION,
            schema=ASTER_SCHEMA_INSERCION,
            tabla=ASTER_TABLA_INSERCION,
            total_general_aster=session.get("total_aster"),
        )

        status = str(resultado.get("status") or "")

        if status in {"errores_validacion", "errores_sql_reales"}:
            return render_errores_validacion_insert_aster(
                resultado.get("errores", [])
            )

        if status == "duplicados":
            return render_duplicados_aster(
                total_duplicados=int(resultado.get("total_duplicados", 0)),
                columnas_clave=resultado.get("columnas_clave", []),
                ejemplos=resultado.get("ejemplos_duplicados", []),
            )

        if status == "cuadre_fallido":
            fecha_yyyymmdd = _obtener_fecha_proceso_aster()
            ruta_entidades, nombre_entidades, total_entidades = _generar_excel_entidades_aster(
                fecha_yyyymmdd
            )

            detalle_cuadre = resultado.get("detalle_cuadre", {})

            _registrar_historial_carga_aster(
                fecha_proceso=fecha_yyyymmdd,
                archivo_excel=os.path.basename(str(resultado.get("ruta_archivo", ""))),
                conexion=conexion,
                total_general_aster=detalle_cuadre.get("total_general_aster"),
                filas_excel=detalle_cuadre.get("filas_excel") or 0,
                registros_insertados=detalle_cuadre.get("registros_insertados") or 0,
                estado="FALLÓ_CUADRE",
                mensaje="No coincide filas Excel = registros insertados = Total general ASTER.",
                archivo_reporte_entidades=nombre_entidades,
                ruta_reporte_entidades=ruta_entidades,
            )

            return render_reporte_final_aster(
                fecha_yyyymmdd=fecha_yyyymmdd,
                detalle_cuadre=detalle_cuadre,
                ruta_entidades=ruta_entidades,
                nombre_entidades=nombre_entidades,
                total_entidades=total_entidades,
            )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Error insertando datos ASTER.")))}
            </div>
            """

        fecha_yyyymmdd = _obtener_fecha_proceso_aster()
        ruta_entidades, nombre_entidades, total_entidades = _generar_excel_entidades_aster(
            fecha_yyyymmdd
        )

        detalle_cuadre = resultado.get("detalle_cuadre", {})
        total_insertados = int(resultado.get("total_insertados", 0))
        ruta_archivo_insertado = str(resultado.get("ruta_archivo", ruta_archivo))

        session["aster_ultimo_insert_conexion"] = conexion
        session["aster_ultimo_insert_total"] = total_insertados
        session["aster_reporte_entidades"] = ruta_entidades

        _registrar_historial_carga_aster(
            fecha_proceso=fecha_yyyymmdd,
            archivo_excel=os.path.basename(ruta_archivo_insertado),
            conexion=conexion,
            total_general_aster=detalle_cuadre.get("total_general_aster"),
            filas_excel=detalle_cuadre.get("filas_excel") or 0,
            registros_insertados=detalle_cuadre.get("registros_insertados") or 0,
            estado="CORRECTO",
            mensaje="Proceso ASTER correcto. Coinciden Excel, registros insertados y Total general ASTER.",
            archivo_reporte_entidades=nombre_entidades,
            ruta_reporte_entidades=ruta_entidades,
        )

        return render_insert_ok_aster(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
            tabla_destino=f"{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}",
            ruta_archivo=ruta_archivo_insertado,
            total_leidos=int(resultado.get("total_leidos", 0)),
            total_insertados=total_insertados,
            columnas_insertadas=resultado.get("columnas_insertadas", []),
            columnas_clave=resultado.get("columnas_clave", []),
            detalle_cuadre=detalle_cuadre,
            ruta_entidades=ruta_entidades,
            nombre_entidades=nombre_entidades,
            total_entidades=total_entidades,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error insertando datos ASTER: {escape(str(exc))}</div>"



@aster_bp.route("/accion/aster-historial-cargas", methods=["POST", "GET"])
def accion_aster_historial_cargas():
    """
    Muestra historial local de cargas ASTER.
    """
    try:
        limite_raw = request.form.get("limite", "30").strip()

        try:
            limite = int(limite_raw)
        except Exception:
            limite = 30

        if limite <= 0:
            limite = 30

        registros = _obtener_historial_cargas_aster(limite=limite)

        return render_historial_cargas_aster(
                registros=registros,
                ruta_db=ASTER_HISTORIAL_DB,
            )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error consultando historial ASTER: {escape(str(exc))}</div>"



def _obtener_fecha_fase_i(fecha_raw: str = "") -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return obtener_fecha_fase_i_service(
        fecha_raw=fecha_raw,
        fecha_default=_obtener_fecha_proceso_aster(),
    )





@aster_bp.route("/accion/aster-fase-i-probar-conexiones", methods=["POST"])
def accion_aster_fase_i_probar_conexiones():
    """
    Prueba conexiones Fase I:
    - MySQL usuarios
    - MySQL gestioncomercial
    - SQL Server Aster_Api

    La lógica vive en:
    app.services.aster_phase_i_prepare_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()

        resultado = probar_conexiones_fase_i_aster(
            conexion=conexion,
            sql_local=SQL_LOCAL,
            sql_remoto=SQL_REMOTO,
            base=ASTER_FASE_I_BASE,
            schema=ASTER_FASE_I_SCHEMA,
            tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
            tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
            db_usuarios=ASTER_MYSQL_DB_USUARIOS,
            db_gestion=ASTER_MYSQL_DB_GESTION,
        )

        conexion = str(resultado.get("conexion", "local"))
        tipo = "REMOTO - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - DESARROLLO"

        html = """
        <div class='log-line success'>
            ✅ Conexiones Fase I ASTER verificadas correctamente.
        </div>
        """

        if conexion == "remoto":
            html += """
            <div class='log-line warning'>
                ⚠️ REMOTO está habilitado, pero corresponde a producción.
            </div>
            """

        html += f"""
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                    Verificación conexiones Fase I ASTER
                </th>
            </tr>
            <tr>
                <td><b>MySQL usuarios</b></td>
                <td>OK - BD {escape(ASTER_MYSQL_DB_USUARIOS)}</td>
            </tr>
            <tr>
                <td><b>MySQL gestioncomercial</b></td>
                <td>OK - BD {escape(ASTER_MYSQL_DB_GESTION)}</td>
            </tr>
            <tr>
                <td><b>SQL Server destino</b></td>
                <td>OK - {escape(tipo)} - Base {escape(ASTER_FASE_I_BASE)}</td>
            </tr>
            <tr>
                <td><b>Columnas usuarios</b></td>
                <td>{escape(str(resultado.get("total_columnas_usuarios", 0)))}</td>
            </tr>
            <tr>
                <td><b>Columnas comentarios</b></td>
                <td>{escape(str(resultado.get("total_columnas_comentarios", 0)))}</td>
            </tr>
        </table>
        """

        return html

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error probando conexiones Fase I ASTER: {escape(str(exc))}</div>"
    

@aster_bp.route("/accion/aster-fase-i-preparar", methods=["POST"])
def accion_aster_fase_i_preparar():
    """
    Prepara Fase I sin ejecutar DELETE ni INSERT.

    La lógica vive en:
    app.services.aster_phase_i_prepare_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()
        fecha_raw = request.form.get("fecha_proceso", "").strip()


        # ASTER Fase I requiere entidades_aster_YYYYMMDD.xlsx.
        # Si no existe, se genera aquí desde las entidades validadas en sesión.
        try:
            fecha_para_entidades = (
                locals().get("fecha_raw")
                or locals().get("fecha")
                or request.form.get("fecha")
                or request.args.get("fecha")
                or session.get("aster_fecha_proceso")
                or session.get("fecha_proceso_aster")
                or session.get("fecha_proceso")
                or ""
            )
            _asegurar_excel_entidades_aster_para_fase_i(fecha_para_entidades)
        except Exception as exc:
            return (
                "<div class='log-line error'>"
                f"❌ No se pudo preparar el archivo de entidades ASTER requerido por Fase I: "
                f"{escape(str(exc))}"
                "</div>"
            )

        resultado = preparar_fase_i_aster(
            data_dir=DATA_DIR,
            fecha_raw=fecha_raw,
            fecha_default=_obtener_fecha_proceso_aster(),
            conexion=conexion,
            sql_local=SQL_LOCAL,
            sql_remoto=SQL_REMOTO,
            base=ASTER_FASE_I_BASE,
            schema=ASTER_FASE_I_SCHEMA,
            tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
            tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
            db_usuarios=ASTER_MYSQL_DB_USUARIOS,
            db_gestion=ASTER_MYSQL_DB_GESTION,
        )

        fecha_yyyymmdd = str(resultado["fecha_yyyymmdd"])
        conexion = str(resultado["conexion"])
        entidades = resultado["entidades"]
        ruta_entidades = str(resultado["ruta_entidades"])
        total_usuarios = int(resultado["total_usuarios"])
        total_comentarios = int(resultado["total_comentarios"])

        session["aster_fase_i_fecha"] = fecha_yyyymmdd
        session["aster_fase_i_conexion"] = conexion
        session["aster_fase_i_preparado"] = True
        session["aster_fase_i_total_entidades"] = len(entidades)
        session["aster_fase_i_total_usuarios"] = total_usuarios
        session["aster_fase_i_total_comentarios"] = total_comentarios
        session["aster_fase_i_ruta_entidades"] = ruta_entidades

        return render_preparacion_fase_i(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
            base_destino=ASTER_FASE_I_BASE,
            ruta_entidades=ruta_entidades,
            total_entidades=len(entidades),
            total_usuarios=total_usuarios,
            total_comentarios=total_comentarios,
            comparacion_usuarios=resultado["comparacion_usuarios"],
            comparacion_comentarios=resultado["comparacion_comentarios"],
        )

    except Exception as exc:
        session["aster_fase_i_preparado"] = False
        return f"<div class='log-line error'>❌ Error preparando Fase I ASTER: {escape(str(exc))}</div>"



@aster_bp.route("/accion/aster-fase-i-ejecutar", methods=["POST"])
def accion_aster_fase_i_ejecutar():
    """
    Ejecuta Fase I completa.

    La lógica de ejecución vive en:
    app.services.aster_phase_i_execution_service
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()
        fecha_raw = request.form.get("fecha_proceso", "").strip()
        confirmar_remoto = request.form.get("confirmar_remoto", "").strip().upper()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        if conexion == "remoto" and confirmar_remoto != "SI":
            return """
            <div class='log-line error'>
                ❌ Ejecución remota bloqueada. REMOTO corresponde a producción.
            </div>
            """

        resultado = ejecutar_fase_i_aster(
            data_dir=DATA_DIR,
            fecha_raw=fecha_raw,
            fecha_default=_obtener_fecha_proceso_aster(),
            conexion=conexion,
            sql_local=SQL_LOCAL,
            sql_remoto=SQL_REMOTO,
            base=ASTER_FASE_I_BASE,
            schema=ASTER_FASE_I_SCHEMA,
            tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
            tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
            db_usuarios=ASTER_MYSQL_DB_USUARIOS,
            db_gestion=ASTER_MYSQL_DB_GESTION,
        )

        status = str(resultado.get("status") or "")
        fecha_yyyymmdd = str(
            resultado.get("fecha_yyyymmdd")
            or _obtener_fecha_fase_i(fecha_raw)
        )
        ruta_entidades = str(resultado.get("ruta_entidades") or "")
        pipeline = resultado.get("pipeline") or []

        if status == "claves_invalidas":
            _registrar_historial_carga_aster(
                fecha_proceso=fecha_yyyymmdd,
                archivo_excel=os.path.basename(ruta_entidades),
                conexion=conexion,
                total_general_aster=None,
                filas_excel=int(resultado.get("comentarios_leidos", 0)),
                registros_insertados=0,
                estado="GESTIONES_CLAVE_INCOMPLETA",
                mensaje="Fase I bloqueada por claves incompletas en comentarios.",
                archivo_reporte_entidades=os.path.basename(ruta_entidades),
                ruta_reporte_entidades=ruta_entidades,
            )

            return render_claves_invalidas_comentarios_fase_i(
                resultado.get("errores_clave", [])
            )

        if status == "duplicados":
            _registrar_historial_carga_aster(
                fecha_proceso=fecha_yyyymmdd,
                archivo_excel=os.path.basename(ruta_entidades),
                conexion=conexion,
                total_general_aster=None,
                filas_excel=int(resultado.get("comentarios_leidos", 0)),
                registros_insertados=0,
                estado="GESTIONES_DUPLICADO",
                mensaje="Fase I bloqueada por duplicados en comentarios.",
                archivo_reporte_entidades=os.path.basename(ruta_entidades),
                ruta_reporte_entidades=ruta_entidades,
            )

            return render_duplicados_comentarios_fase_i(
                int(resultado.get("total_duplicados", 0)),
                resultado.get("ejemplos_duplicados", []),
            )

        if status in {"faltan_columnas_origen", "error_columnas"}:
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Fase I bloqueada por validación.")))}
            </div>
            """

        if not resultado.get("success"):
            try:
                _registrar_historial_carga_aster(
                    fecha_proceso=fecha_yyyymmdd,
                    archivo_excel=os.path.basename(ruta_entidades),
                    conexion=conexion,
                    total_general_aster=None,
                    filas_excel=int(resultado.get("comentarios_leidos", 0) or 0),
                    registros_insertados=0,
                    estado="GESTIONES_ERROR",
                    mensaje=str(resultado.get("error", "Error ejecutando Fase I ASTER.")),
                    archivo_reporte_entidades=os.path.basename(ruta_entidades),
                    ruta_reporte_entidades=ruta_entidades,
                )
            except Exception:
                pass

            return f"""
            <div class='log-line error'>
                ❌ Error ejecutando Fase I ASTER: {escape(str(resultado.get("error", "Error desconocido.")))}
            </div>
            """

        _registrar_historial_carga_aster(
            fecha_proceso=fecha_yyyymmdd,
            archivo_excel=os.path.basename(ruta_entidades),
            conexion=conexion,
            total_general_aster=None,
            filas_excel=int(resultado.get("comentarios_leidos", 0)),
            registros_insertados=int(resultado.get("comentarios_insertados", 0)),
            estado="GESTIONES_CORRECTO",
            mensaje=(
                "Fase I correcta. Usuarios recargados y comentarios insertados "
                "sin duplicados."
            ),
            archivo_reporte_entidades=os.path.basename(ruta_entidades),
            ruta_reporte_entidades=ruta_entidades,
        )

        return render_reporte_fase_i(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
            base_destino=ASTER_FASE_I_BASE,
            ruta_entidades=ruta_entidades,
            total_entidades=int(resultado.get("total_entidades", 0)),
            usuarios_leidos=int(resultado.get("usuarios_leidos", 0)),
            usuarios_insertados=int(resultado.get("usuarios_insertados", 0)),
            comentarios_leidos=int(resultado.get("comentarios_leidos", 0)),
            comentarios_insertados=int(resultado.get("comentarios_insertados", 0)),
            estado="CORRECTO",
            mensaje="Usuarios recargados y comentarios insertados correctamente.",
            pipeline=pipeline,
            mostrar_boton_gestion=True,
        )

    except Exception as exc:
        try:
            fecha_yyyymmdd_error = _obtener_fecha_fase_i(
                request.form.get("fecha_proceso", "").strip()
            )
        except Exception:
            fecha_yyyymmdd_error = datetime.now().strftime("%Y%m%d")

        try:
            _registrar_historial_carga_aster(
                fecha_proceso=fecha_yyyymmdd_error,
                archivo_excel="",
                conexion=request.form.get("conexion", "local").strip().lower(),
                total_general_aster=None,
                filas_excel=0,
                registros_insertados=0,
                estado="GESTIONES_ERROR",
                mensaje=str(exc),
                archivo_reporte_entidades="",
                ruta_reporte_entidades="",
            )
        except Exception:
            pass

        return f"<div class='log-line error'>❌ Error ejecutando Fase I ASTER: {escape(str(exc))}</div>"



@aster_bp.route("/accion/aster-fase-i-generar-gestion", methods=["POST"])
def accion_aster_fase_i_generar_gestion():
    """
    Genera Excel de Gestión ASTER después de ejecutar correctamente Fase I.

    La lógica vive en:
    app.services.aster_gestion_export_service
    """
    try:
        payload = request.get_json(silent=True) or {}

        fecha_yyyymmdd = _obtener_fecha_fase_i(
            str(payload.get("fecha_proceso", "")).strip()
        )

        conexion = str(payload.get("conexion", "local")).strip().lower()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        resultado = generar_gestion_aster_fase_i(
            data_dir=DATA_DIR,
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
            sql_local=SQL_LOCAL,
            sql_remoto=SQL_REMOTO,
            base=ASTER_FASE_I_BASE,
        )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ Error generando Gestión ASTER: {escape(str(resultado.get("error", "Error desconocido.")))}
            </div>
            """

        return render_gestion_aster_excel(resultado)

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error generando Gestión ASTER: {escape(str(exc))}</div>"



@aster_bp.route("/accion/aster-total-actual", methods=["GET"])
def accion_aster_total_actual():
    """
    Devuelve el total ASTER actual guardado en sesión.
    """
    total: Any = session.get("total_aster")

    if total is None:
        return "<div class='log-line warning'>⚠️ Todavía no hay total ASTER registrado.</div>"

    return render_total_aster(
        total=int(total),
        origen="Sesión actual",
        previews=[],
    )
    
    
@aster_bp.route("/accion/aster-preparar-depuracion", methods=["POST"])
def accion_aster_preparar_depuracion():
    """
    Prepara la tabla para excluir entidades que no corresponden a cobranzas %.

    La lógica vive en:
    app.services.aster_classification_service
    """
    try:
        resultado = preparar_depuracion_aster(
            session.get("aster_resultados_sql") or []
        )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "No hay resultados SQL ASTER.")))}
            </div>
            """

        return render_preparar_depuracion_aster(
            resultado["resultados"]
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error preparando depuración ASTER: {escape(str(exc))}</div>"
    

@aster_bp.route("/accion/aster-aplicar-exclusiones", methods=["POST"])
def accion_aster_aplicar_exclusiones():
    """
    Aplica exclusiones seleccionadas y genera tabla de clasificación.

    La lógica vive en:
    app.services.aster_classification_service
    """
    try:
        entidades_excluir = set(request.form.getlist("entidades_excluir"))

        resultado = aplicar_exclusiones_aster(
            resultados_sql=session.get("aster_resultados_sql") or [],
            entidades_excluir=entidades_excluir,
        )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "No hay resultados SQL ASTER.")))}
            </div>
            """

        removidos = resultado["removidos"]
        filtrados = resultado["filtrados"]

        session["aster_sql_removidos"] = removidos
        session["aster_sql_filtrados"] = filtrados

        return render_exclusiones_aplicadas_aster(
            removidos=removidos,
            filtrados=filtrados,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error aplicando exclusiones ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-guardar-clasificacion", methods=["POST"])
def accion_aster_guardar_clasificacion():
    """
    Guarda clasificación final de entidades ASTER.

    La lógica vive en:
    app.services.aster_classification_service
    """
    try:
        clasificaciones_raw = request.form.get("clasificaciones", "[]")

        try:
            clasificaciones = json.loads(clasificaciones_raw)
        except Exception:
            clasificaciones = []

        resultado = guardar_clasificacion_aster(
            clasificaciones=clasificaciones,
            removidos=session.get("aster_sql_removidos") or [],
        )

        if not resultado.get("success"):
            return f"""
            <div class='log-line error'>
                ❌ {escape(str(resultado.get("error", "Formato inválido de clasificación ASTER.")))}
            </div>
            """

        removidos = resultado["removidos"]
        cobranza = resultado["cobranza"]
        integral = resultado["integral"]
        no_seleccionados = resultado["no_seleccionados"]

        session["aster_bases_cobranza"] = cobranza
        session["aster_bases_integral"] = integral
        session["aster_bases_no_seleccionadas"] = no_seleccionados

        return render_clasificacion_final_aster(
            removidos=removidos,
            cobranza=cobranza,
            integral=integral,
            no_seleccionados=no_seleccionados,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error guardando clasificación ASTER: {escape(str(exc))}</div>"


    
    
    