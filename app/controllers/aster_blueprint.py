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

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

import pandas as pd
import pyodbc

from app.config import SQL_LOCAL, SQL_REMOTO

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.services.daily_paths import (
    crear_estructura_aster,
    ruta_aster_base,
    ruta_aster_subcarpeta,
)
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor
from app.services.aster_file_service import (
    buscar_archivo_normalizado_aster_en_disco,
    copiar_archivo_aster,
    obtener_carpeta_proceso_aster,
)

from app.services.aster_normalization_service import normalizar_archivo_aster
from app.services.aster_entity_service import analizar_entidades_excel_aster
from app.services.aster_sql_entity_service import (
    consultar_entidades_sql_aster,
    normalizar_fecha_sql_aster,
)

from app.services.aster_classification_service import (
    aplicar_exclusiones_aster,
    guardar_clasificacion_aster,
    preparar_depuracion_aster,
    normalizar_resultados_sql_aster,
)

from app.services.aster_reconciliation_service import (
    conciliar_entidades_aster,
    normalizar_entidades_excel_aster,
    obtener_entidades_sql_validables_aster as obtener_entidades_sql_validables_aster_service,
)

from app.services.aster_history_service import (
    inicializar_historial_aster,
    obtener_historial_cargas_aster,
    registrar_historial_carga_aster,
)

from app.services.aster_sqlserver_service import (
    construir_cadena_pyodbc_aster as construir_cadena_pyodbc_aster_service,
    obtener_cadena_sqlserver_aster as obtener_cadena_sqlserver_aster_service,
    obtener_columnas_sqlserver_tabla,
    probar_conexion_tabla_sqlserver_aster,
    valor_config_sql as valor_config_sql_service,
)

from app.services.aster_entities_export_service import (
    generar_excel_entidades_aster as generar_excel_entidades_aster_service,
    normalizar_entidades_filtradas_finales_aster,
)

from app.services.aster_insert_prepare_service import preparar_insercion_aster
from app.services.aster_insert_service import insertar_datos_aster
from app.services.aster_phase_i_prepare_service import (
    columnas_mysql_comentarios_fase_i as columnas_mysql_comentarios_fase_i_service,
    columnas_mysql_usuarios_fase_i as columnas_mysql_usuarios_fase_i_service,
    comparar_columnas_fase_i as comparar_columnas_fase_i_service,
    conectar_mysql_fase_i as conectar_mysql_fase_i_service,
    contar_comentarios_mysql_fase_i as contar_comentarios_mysql_fase_i_service,
    contar_usuarios_mysql_fase_i as contar_usuarios_mysql_fase_i_service,
    leer_entidades_fase_i as leer_entidades_fase_i_service,
    obtener_config_mysql_fase_i as obtener_config_mysql_fase_i_service,
    obtener_fecha_fase_i as obtener_fecha_fase_i_service,
    preparar_fase_i_aster,
    probar_conexiones_fase_i_aster,
    ruta_entidades_fase_i as ruta_entidades_fase_i_service,
    validar_sql_mysql_solo_select as validar_sql_mysql_solo_select_service,
)
from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster




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


def _crear_html_total_aster(total: int | None, origen: str, previews: list[tuple[str, str]]) -> str:
    """
    Genera respuesta HTML para mostrar el total ASTER detectado o ingresado.
    """
    html = "<div class='ocr-result-container'>"

    html += "<div class='ocr-images'>"

    if previews:
        for nombre, img_b64 in previews:
            html += (
                "<div class='ocr-thumb'>"
                f"<img src='data:image/png;base64,{img_b64}' alt='{nombre}'/>"
                f"<small>{nombre}</small>"
                "</div>"
            )
    else:
        html += "<p style='color:#888;'>Sin vista previa de imagen.</p>"

    html += "</div>"

    html += "<div class='ocr-results'>"

    if total is not None:
        html += "<div class='log-line success'>✅ Total ASTER capturado correctamente.</div>"
        html += "<div class='totales-grid' style='margin-top:10px;'>"
        html += (
            "<div class='total-card'>"
            "<span class='label'>🔹 Total ASTER</span>"
            f"<span class='value'>{total}</span>"
            "</div>"
        )
        html += "</div>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:10px;'>"
            "<tr><th colspan='2' style='background:#1e3a5f; color:#fff;'>Detalle de captura</th></tr>"
            f"<tr><td><b>Origen</b></td><td>{origen}</td></tr>"
            f"<tr><td><b>Total general</b></td><td>{total}</td></tr>"
            "</table>"
        )
    else:
        html += (
            "<div class='log-line warning'>"
            "⚠️ No se pudo detectar automáticamente el total ASTER. "
            "Ingrese el total manualmente."
            "</div>"
        )

    html += "</div>"
    html += "</div>"

    html += (
        "<div id='aster-total-data' style='display:none;' "
        f"data-total='{total if total is not None else ''}'>"
        "</div>"
    )

    return html


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

def _normalizar_fecha_aster(fecha_raw: str) -> str:
    """
    Convierte una fecha recibida en distintos formatos a YYYYMMDD.

    Acepta ejemplos:
    - 20260429
    - 2026-04-29
    - 202604_29
    """
    fecha_limpia = re.sub(r"[^0-9]", "", fecha_raw or "")

    if len(fecha_limpia) < 8:
        raise ValueError(
            "La fecha del proceso debe tener al menos 8 dígitos. Ejemplo: 20260429."
        )

    return fecha_limpia[:8]


def _claves_busqueda_fecha(fecha_yyyymmdd: str) -> list[str]:
    """
    Genera claves de búsqueda para tolerar variaciones de nombre.

    Para 20260429:
    - 20260429
    - 260429
    - 0429
    """
    yyyy = fecha_yyyymmdd[0:4]
    yy = fecha_yyyymmdd[2:4]
    mm = fecha_yyyymmdd[4:6]
    dd = fecha_yyyymmdd[6:8]

    return [
        f"{yyyy}{mm}{dd}",
        f"{yy}{mm}{dd}",
        f"{mm}{dd}",
    ]


def _archivo_aster_corresponde_fecha(nombre_archivo: str, fecha_yyyymmdd: str) -> bool:
    """
    Valida que el archivo corresponda exactamente a la fecha del proceso.

    Ejemplo:
    fecha_yyyymmdd = 20260521
    válido = After20260521.xlsx
    inválido = After20240521.xlsx
    """
    nombre_esperado = f"After{fecha_yyyymmdd}.xlsx"

    return os.path.basename(nombre_archivo).lower() == nombre_esperado.lower()

def _generar_html_archivo_aster(
    fecha_yyyymmdd: str,
    ruta_origen: str,
    ruta_destino: str,
    nombre_archivo: str,
) -> str:
    """
    Genera HTML de resultado para la copia del archivo ASTER.
    """
    html = "<div class='log-line success'>✅ Archivo ASTER localizado y copiado correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Información del archivo ASTER
            </th>
        </tr>
    """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Archivo encontrado", nombre_archivo),
        ("Ruta origen", ruta_origen),
        ("Ruta destino", ruta_destino),
    ]

    for etiqueta, valor in filas:
        html += f"""
        <tr>
            <td><b>{etiqueta}</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{valor}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-archivo-data' style='display:none;' "
        f"data-fecha='{fecha_yyyymmdd}' "
        f"data-ruta='{ruta_destino}' "
        f"data-archivo='{nombre_archivo}'>"
        "</div>"
    )

    return html




def _generar_html_normalizacion_aster(
    ruta_archivo: str,
    columnas_originales: list[Any],
    columnas_normalizadas: list[str],
) -> str:
    """
    Genera HTML con tabla comparativa de encabezados originales y normalizados.
    """
    html = "<div class='log-line success'>✅ Encabezados ASTER normalizados correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='3' style='background:#1e3a5f; color:#fff;'>
                Comparación de encabezados ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Encabezado original</th>
            <th>Encabezado normalizado</th>
        </tr>
    """

    for idx, (original, normalizado) in enumerate(
        zip(columnas_originales, columnas_normalizadas),
        start=1,
    ):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{original}</td>
            <td><b>{normalizado}</b></td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Archivo actualizado
            </th>
        </tr>
        <tr>
            <td><b>Ruta</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{ruta_archivo}</td>
        </tr>
    </table>
    """

    return html

def _generar_html_entidades_excel_aster(
    ruta_archivo: str,
    total_registros: int,
    conteo_entidades: list[tuple[str, int]],
) -> str:
    """
    Genera HTML con entidades únicas del Excel ASTER.
    """
    total_entidades = len(conteo_entidades)
    total_registros_con_entidad = sum(cantidad for _, cantidad in conteo_entidades)
    total_registros_sin_entidad = total_registros - total_registros_con_entidad

    html = "<div class='log-line success'>✅ Entidades ASTER analizadas correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen de entidades del Excel ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Archivo analizado", ruta_archivo),
        ("Registros totales del Excel", total_registros),
        ("Registros con Entidad", total_registros_con_entidad),
        ("Registros sin Entidad", total_registros_sin_entidad),
        ("Entidades únicas encontradas", total_entidades),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Cantidad de registros</th>
        </tr>
    """

    for idx, (entidad, cantidad) in enumerate(conteo_entidades, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(entidad))}</b></td>
            <td style='font-weight:bold;'>{cantidad}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-entidades-excel-data' style='display:none;' "
        f"data-total-entidades='{total_entidades}' "
        f"data-total-registros='{total_registros}'>"
        "</div>"
    )

    return html


def _normalizar_fecha_sql_aster(fecha_raw: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sql_entity_service.
    """
    return normalizar_fecha_sql_aster(fecha_raw)


def _consultar_entidades_sql_aster(fecha_sql: str) -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sql_entity_service.

    Recibe fecha en YYYY-MM-DD desde llamadas existentes.
    """
    resultado = consultar_entidades_sql_aster(fecha_sql)

    if not resultado.get("success"):
        raise RuntimeError(str(resultado.get("error", "Error consultando entidades ASTER.")))

    return resultado.get("resultados", [])



def _generar_html_consulta_sql_aster(
    fecha_sql: str,
    resultados: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de la consulta SQL ASTER.
    """
    total_entidades = len(resultados)
    total_registros = sum(int(fila["numero"]) for fila in resultados)

    if not resultados:
        return f"""
        <div class='log-line warning'>
            ⚠️ La consulta ASTER no devolvió resultados para la fecha {escape(fecha_sql)}.
        </div>
        """

    html = "<div class='log-line success'>✅ Consulta SQL ASTER ejecutada correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen consulta SQL ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Fecha consultada", fecha_sql),
        ("Entidades devueltas por SQL", total_entidades),
        ("Total registros SQL", total_registros),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.9rem; font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    for idx, fila in enumerate(resultados, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila["entidad"]))}</b></td>
            <td style='font-weight:bold;'>{escape(str(fila["numero"]))}</td>
            <td><code>{escape(str(fila["SSS"]))}</code></td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-sql-data' style='display:none;' "
        f"data-fecha='{escape(fecha_sql)}' "
        f"data-total-entidades='{total_entidades}' "
        f"data-total-registros='{total_registros}'>"
        "</div>"
    )

    return html


def _obtener_resultados_sql_aster_desde_sesion() -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La normalización real vive en app.services.aster_classification_service.
    """
    resultados = session.get("aster_resultados_sql") or []

    return normalizar_resultados_sql_aster(resultados)



def _generar_tabla_entidades_aster(
    titulo: str,
    filas: list[dict[str, Any]],
) -> str:
    """
    Genera tabla simple de entidades ASTER.
    """
    html = f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='4' style='background:#1e3a5f; color:#fff;'>
                {escape(titulo)} ({len(filas)})
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    if not filas:
        html += """
        <tr>
            <td colspan='4' style='text-align:center; color:#888;'>
                Sin registros.
            </td>
        </tr>
        """

    for idx, fila in enumerate(filas, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{numero}</td>
            <td><code>{escape(sss)}</code></td>
        </tr>
        """

    html += "</table>"

    return html


def _generar_html_preparar_depuracion_aster(
    resultados: list[dict[str, Any]],
) -> str:
    """
    Genera primera tabla para seleccionar registros que no corresponden a cobranzas %.
    """
    total_entidades = len(resultados)
    total_registros = sum(int(fila.get("numero") or 0) for fila in resultados)

    html = """
    <div class='log-line info'>
        Seleccione las entidades que NO corresponden a cobranzas %. Luego presione Aplicar exclusiones.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                Depuración inicial ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Entidades SQL disponibles", total_entidades),
        ("Total registros SQL", total_registros),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td colspan='2'><b>{escape(str(etiqueta))}</b></td>
            <td colspan='3' style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += """
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>Excluir</th>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    for idx, fila in enumerate(resultados, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        entidad_value = escape(entidad, quote=True)

        html += f"""
        <tr>
            <td style='text-align:center;'>
                <input
                    type='checkbox'
                    class='aster-excluir-checkbox'
                    value="{entidad_value}"
                >
            </td>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{numero}</td>
            <td><code>{escape(sss)}</code></td>
        </tr>
        """

    html += "</table>"

    html += """
    <div style='margin-top:10px;'>
        <button type='button' onclick='aplicarExclusionesAster(this)'>
            Aplicar exclusiones ASTER
        </button>
    </div>
    """

    return html


def _generar_html_exclusiones_aplicadas_aster(
    removidos: list[dict[str, Any]],
    filtrados: list[dict[str, Any]],
) -> str:
    """
    Muestra removidos y tabla filtrada para clasificar Cobranza % / Integral.
    """
    html = "<div class='log-line success'>✅ Exclusiones ASTER aplicadas correctamente.</div>"

    html += _generar_tabla_entidades_aster(
        "Registros removidos por no corresponder a cobranzas %",
        removidos,
    )

    html += """
    <div class='log-line info' style='margin-top:10px;'>
        Clasifique las entidades restantes como Cobranza % o Integral. Las que deje sin seleccionar quedarán como no seleccionadas.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                Clasificación de entidades ASTER filtradas
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
            <th>Clasificación</th>
        </tr>
    """

    if not filtrados:
        html += """
        <tr>
            <td colspan='5' style='text-align:center; color:#888;'>
                Sin entidades disponibles para clasificar.
            </td>
        </tr>
        """

    for idx, fila in enumerate(filtrados, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{numero}</td>
            <td><code>{escape(sss)}</code></td>
            <td>
                <select
                    class='aster-clasificacion-select'
                    data-entidad="{escape(entidad, quote=True)}"
                    data-numero="{numero}"
                    data-sss="{escape(sss, quote=True)}"
                    style='padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;'
                >
                    <option value=''>No seleccionado</option>
                    <option value='cobranza'>Cobranza %</option>
                    <option value='integral'>Integral</option>
                </select>
            </td>
        </tr>
        """

    html += "</table>"

    html += """
    <div style='margin-top:10px;'>
        <button type='button' onclick='guardarClasificacionAster(this)'>
            Guardar clasificación ASTER
        </button>
    </div>
    """

    return html


def _generar_html_clasificacion_final_aster(
    removidos: list[dict[str, Any]],
    cobranza: list[dict[str, Any]],
    integral: list[dict[str, Any]],
    no_seleccionados: list[dict[str, Any]],
) -> str:
    """
    Muestra resultado final de la depuración y clasificación ASTER.
    """
    total_validado = len(cobranza) + len(integral) + len(no_seleccionados)

    html = "<div class='log-line success'>✅ Clasificación ASTER guardada correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen clasificación ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Registros removidos", len(removidos)),
        ("Bases Cobranza %", len(cobranza)),
        ("Bases Integral", len(integral)),
        ("No seleccionadas", len(no_seleccionados)),
        ("Entidades revisadas después de exclusiones", total_validado),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += _generar_tabla_entidades_aster("Registros removidos", removidos)
    html += _generar_tabla_entidades_aster("Seleccionadas como Cobranza %", cobranza)
    html += _generar_tabla_entidades_aster("Seleccionadas como Integral", integral)
    html += _generar_tabla_entidades_aster("No seleccionadas", no_seleccionados)

    html += (
        "<div id='aster-clasificacion-data' style='display:none;' "
        f"data-removidos='{len(removidos)}' "
        f"data-cobranza='{len(cobranza)}' "
        f"data-integral='{len(integral)}' "
        f"data-no-seleccionados='{len(no_seleccionados)}'>"
        "</div>"
    )

    return html

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


def _generar_html_tabla_comparativa_aster(
    comparacion: list[dict[str, Any]],
    titulo: str = "Comparación Excel vs SQL ASTER",
) -> str:
    """
    Genera tabla comparativa Excel vs SQL desde resultado estructurado.
    """
    html = f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                {escape(titulo)}
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>En Excel</th>
            <th>En SQL</th>
            <th>Estado</th>
        </tr>
    """

    if not comparacion:
        html += """
        <tr>
            <td colspan='5' style='text-align:center; color:#888;'>
                Sin entidades para comparar.
            </td>
        </tr>
        """

    for idx, fila in enumerate(comparacion, start=1):
        entidad = str(fila.get("entidad") or "")
        en_excel = bool(fila.get("en_excel"))
        en_sql = bool(fila.get("en_sql"))
        estado_raw = str(fila.get("estado") or "")

        if estado_raw == "MATCH":
            estado = "✅ Match"
            color = "#28a745"
        elif estado_raw == "FALTA_EN_SQL":
            estado = "⚠️ Está en Excel, falta en SQL"
            color = "#ffc107"
        else:
            estado = "⚠️ Está en SQL, falta en Excel"
            color = "#dc3545"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td>{'Sí' if en_excel else 'No'}</td>
            <td>{'Sí' if en_sql else 'No'}</td>
            <td style='font-weight:bold; color:{color};'>{estado}</td>
        </tr>
        """

    html += "</table>"

    return html


def _generar_html_conciliacion_aster(
    resultado: dict[str, Any],
) -> str:
    """
    Genera HTML de conciliación ASTER desde resultado estructurado.
    """
    faltan_en_sql = resultado.get("faltan_en_sql", [])
    sobran_en_sql = resultado.get("sobran_en_sql", [])
    entidades_no_tomar = set(resultado.get("entidades_no_tomar", []))
    comparacion = resultado.get("comparacion", [])
    match_ok = bool(resultado.get("match_ok"))

    html = """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen conciliación ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Entidades únicas en Excel", resultado.get("total_excel", 0)),
        ("Entidades SQL consideradas", resultado.get("total_sql", 0)),
        ("Entidades no tomadas en cuenta", resultado.get("total_no_tomar", 0)),
        ("Entidades en Excel que faltan en SQL", len(faltan_en_sql)),
        ("Entidades en SQL que faltan en Excel", len(sobran_en_sql)),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += _generar_html_tabla_comparativa_aster(
        comparacion=comparacion,
        titulo="Comparación Excel vs SQL ASTER",
    )

    if match_ok:
        html = "<div class='log-line success'>✅ Información Verificada.</div>" + html

        html += """
        <div id='aster-conciliacion-data' style='display:none;' data-validado='1'></div>
        """

        return html

    html = """
    <div class='log-line warning'>
        ⚠️ La conciliación ASTER tiene diferencias. Revise las entidades antes de continuar.
    </div>
    """ + html

    if faltan_en_sql:
        html += """
        <div class='log-line warning' style='margin-top:10px;'>
            ⚠️ Hay entidades en el Excel que no aparecen en la consulta SQL ASTER.
            Esto puede indicar que falta completar información en ASTER o revisar la fecha consultada.
        </div>
        """

        html += _generar_tabla_entidades_aster(
            "Entidades en Excel que faltan en SQL",
            [
                {
                    "entidad": entidad,
                    "numero": 0,
                    "SSS": f"'{entidad}'",
                }
                for entidad in faltan_en_sql
            ],
        )

    if sobran_en_sql:
        html += """
        <div class='log-line warning' style='margin-top:10px;'>
            ⚠️ Hay entidades en SQL que no aparecen en el Excel. Seleccione cuáles no se tomarán en cuenta y vuelva a validar.
        </div>
        """

        html += """
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='4' style='background:#1e3a5f; color:#fff;'>
                    Entidades SQL sobrantes
                </th>
            </tr>
            <tr style='background:#1e3a5f; color:#fff;'>
                <th>No tomar en cuenta</th>
                <th>#</th>
                <th>Entidad</th>
                <th>SSS</th>
            </tr>
        """

        for idx, fila in enumerate(resultado.get("sobrantes_detalle", []), start=1):
            entidad = str(fila.get("entidad") or "")
            sss = str(fila.get("SSS") or f"'{entidad}'")
            checked = "checked" if entidad in entidades_no_tomar else ""

            html += f"""
            <tr>
                <td style='text-align:center;'>
                    <input
                        type='checkbox'
                        class='aster-no-tomar-checkbox'
                        value="{escape(entidad, quote=True)}"
                        {checked}
                    >
                </td>
                <td>{idx}</td>
                <td><b>{escape(entidad)}</b></td>
                <td><code>{escape(sss)}</code></td>
            </tr>
            """

        html += "</table>"

        html += """
        <div style='margin-top:10px;'>
            <button type='button' onclick='ajustarConciliacionAster(this)'>
                Aplicar entidades no tomadas en cuenta
            </button>
        </div>
        """

    html += """
    <div id='aster-conciliacion-data' style='display:none;' data-validado='0'></div>
    """

    return html


def _valor_config_sql(config: Any, *nombres: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sqlserver_service.
    """
    return valor_config_sql_service(config, *nombres)


def _construir_cadena_pyodbc_aster(config: Any) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sqlserver_service.
    """
    return construir_cadena_pyodbc_aster_service(
        config,
        database_default=ASTER_BASE_INSERCION,
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
    


def _generar_html_preparacion_insercion_aster(
    conexion: str,
    ruta_archivo: str,
    total_registros: int,
    comparacion: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de comparación previa a inserción ASTER.
    """
    conexion_normalizada = (conexion or "local").strip().lower()
    es_remoto = conexion_normalizada == "remoto"

    html = ""

    if es_remoto:
        html += """
        <div class='log-line warning'>
            ⚠️ Atención: seleccionó conexión REMOTA. Esta conexión es producción.
            No se debe usar para pruebas.
        </div>
        """
    else:
        html += """
        <div class='log-line success'>
            ✅ Conexión LOCAL seleccionada para pruebas.
        </div>
        """

    total_ok = sum(1 for fila in comparacion if fila["estado"] == "OK")
    total_no_sql = sum(1 for fila in comparacion if fila["estado"] == "NO_EXISTE_EN_SQL")
    total_no_excel = sum(1 for fila in comparacion if fila["estado"] == "NO_EXISTE_EN_EXCEL")

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen preparación inserción ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Conexión seleccionada", conexion_normalizada.upper()),
        ("Tabla destino", f"{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}"),
        ("Archivo Excel", ruta_archivo),
        ("Registros en Excel", total_registros),
        ("Columnas coincidentes", total_ok),
        ("Columnas Excel sin campo SQL", total_no_sql),
        ("Campos SQL sin columna Excel", total_no_excel),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.8rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Columna Excel</th>
            <th>Tipo Excel</th>
            <th>Campo SQL</th>
            <th>Tipo SQL</th>
            <th>Nullable</th>
            <th>Longitud</th>
            <th>Estado</th>
        </tr>
    """

    for idx, fila in enumerate(comparacion, start=1):
        estado = str(fila["estado"])

        if estado == "OK":
            color = "#28a745"
            texto_estado = "✅ OK"
        elif estado == "NO_EXISTE_EN_SQL":
            color = "#dc3545"
            texto_estado = "❌ No existe en SQL"
        else:
            color = "#ffc107"
            texto_estado = "⚠️ No existe en Excel"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila["columna_excel"]))}</b></td>
            <td>{escape(str(fila["tipo_excel"]))}</td>
            <td><b>{escape(str(fila["columna_sql"]))}</b></td>
            <td>{escape(str(fila["tipo_sql"]))}</td>
            <td>{escape(str(fila["nullable"]))}</td>
            <td>{escape(str(fila["longitud"]))}</td>
            <td style='font-weight:bold; color:{color};'>{texto_estado}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <div id='aster-preparacion-insercion-data' style='display:none;' data-preparado='1'></div>
    """

    return html


def _sql_identificador_aster(nombre: str) -> str:
    """
    Escapa identificadores SQL Server con corchetes.
    """
    return f"[{str(nombre).replace(']', ']]')}]"




def _es_valor_vacio_aster(valor: Any) -> bool:
    """
    Determina si un valor debe enviarse como NULL.
    """
    if valor is None:
        return True

    try:
        if pd.isna(valor):
            return True
    except Exception:
        pass

    texto = str(valor).strip()

    return texto == "" or texto.lower() in {"nan", "nat", "none", "null"}

def _limpiar_parametro_sql_aster(valor: Any) -> Any:
    """
    Limpia valores antes de enviarlos a SQL Server.

    Convierte NaN, NaT, None, 'nan', 'nat', '' a None.
    Esto evita errores ODBC como Numeric value out of range.
    """
    if _es_valor_vacio_aster(valor):
        return None

    texto = str(valor).strip()

    if texto.lower() in {"nan", "nat", "none", "null"}:
        return None

    return valor


def _normalizar_dataframe_sql_aster(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza un DataFrame antes de INSERT/diagnóstico SQL.

    Fuerza dtype object y reemplaza NaN/NaT por None.
    """
    df_normalizado = df.astype(object)
    df_normalizado = df_normalizado.where(pd.notna(df_normalizado), None)

    return df_normalizado

def _convertir_valor_sql_aster(valor: Any, tipo_sql: str) -> Any:
    """
    Convierte un valor del Excel al tipo compatible con SQL Server.
    """
    if _es_valor_vacio_aster(valor):
        return None

    tipo = str(tipo_sql).lower()
    texto = str(valor).strip()

    if tipo in {"int", "bigint", "smallint", "tinyint"}:
        numero = pd.to_numeric(texto.replace(",", "."), errors="coerce")

        if pd.isna(numero):
            return None

        return int(numero)

    if tipo in {"decimal", "numeric", "money", "smallmoney"}:
        try:
            return Decimal(texto.replace(",", "."))
        except InvalidOperation:
            return None

    if tipo in {"float", "real"}:
        return float(texto.replace(",", "."))

    if tipo in {"bit"}:
        texto_lower = texto.lower()

        if texto_lower in {"1", "true", "si", "sí", "yes", "y"}:
            return 1

        if texto_lower in {"0", "false", "no", "n"}:
            return 0

        return int(float(texto.replace(",", ".")))

    if tipo in {"date"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return None

        return fecha.date()

    if tipo in {"datetime", "datetime2", "smalldatetime"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return None

        return fecha.to_pydatetime()

    if tipo in {"time"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return texto

        return fecha.time()

    return texto


def _generar_html_duplicados_aster(
    total_duplicados: int,
    columnas_clave: list[str],
    ejemplos: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de bloqueo por duplicados.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Inserción ASTER bloqueada. Se detectaron {total_duplicados} registros posiblemente duplicados.
    </div>
    <div class='log-line warning'>
        No se insertó ningún registro. Revise los datos o limpie la carga previa si corresponde.
    </div>
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Validación anti-duplicados ASTER
            </th>
        </tr>
        <tr>
            <td><b>Columnas usadas como clave</b></td>
            <td>{escape(", ".join(columnas_clave))}</td>
        </tr>
        <tr>
            <td><b>Duplicados detectados</b></td>
            <td>{total_duplicados}</td>
        </tr>
    </table>
    """

    if ejemplos:
        html += """
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr style='background:#1e3a5f; color:#fff;'>
                <th>#</th>
        """

        for columna in columnas_clave:
            html += f"<th>{escape(columna)}</th>"

        html += "</tr>"

        for idx, ejemplo in enumerate(ejemplos, start=1):
            html += f"<tr><td>{idx}</td>"

            for columna in columnas_clave:
                html += f"<td>{escape(str(ejemplo.get(columna, '')))}</td>"

            html += "</tr>"

        html += "</table>"

    return html


def _generar_html_errores_validacion_insert_aster(
    errores: list[dict[str, Any]],
) -> str:
    """
    Genera HTML con errores de validación previa.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Preparación de inserción ASTER bloqueada. Se detectaron {len(errores)} errores de datos.
    </div>
    <div class='log-line warning'>
        No se debe insertar hasta corregir estos valores o ajustar los tipos/longitudes de la tabla SQL.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Fila Excel</th>
            <th>Columna</th>
            <th>Tipo SQL</th>
            <th>Valor</th>
            <th>Problema</th>
        </tr>
    """

    for idx, error in enumerate(errores, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(error.get("fila", "")))}</td>
            <td><b>{escape(str(error.get("columna", "")))}</b></td>
            <td>{escape(str(error.get("tipo_sql", "")))}</td>
            <td style='word-break:break-all;'>{escape(str(error.get("valor", "")))}</td>
            <td style='color:#dc3545; font-weight:bold;'>{escape(str(error.get("problema", "")))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <div id='aster-preparacion-insercion-data' style='display:none;' data-preparado='0'></div>
    """

    return html


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


def _obtener_carpeta_proceso_aster(fecha_yyyymmdd: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_file_service.
    """
    return obtener_carpeta_proceso_aster(DATA_DIR, fecha_yyyymmdd)

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


def _inicializar_historial_aster() -> None:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_history_service.
    """
    inicializar_historial_aster(ASTER_HISTORIAL_DB)


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


def _generar_html_historial_cargas_aster(
    registros: list[dict[str, Any]],
) -> str:
    """
    Genera HTML del historial de cargas ASTER.
    """
    html = """
    <div class='log-line info'>
        📜 Historial local de cargas ASTER.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='12' style='background:#1e3a5f; color:#fff;'>
                Últimas cargas ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Fecha registro</th>
            <th>Fecha proceso</th>
            <th>Conexión</th>
            <th>Total ASTER</th>
            <th>Filas Excel</th>
            <th>Insertados</th>
            <th>Estado</th>
            <th>Archivo Excel</th>
            <th>Reporte entidades</th>
            <th>Ruta reporte</th>
            <th>Mensaje</th>
        </tr>
    """

    if not registros:
        html += """
        <tr>
            <td colspan='12' style='text-align:center; color:#888;'>
                Todavía no hay cargas ASTER registradas.
            </td>
        </tr>
        """

    for idx, registro in enumerate(registros, start=1):
        estado = str(registro.get("estado") or "")

        if estado == "CORRECTO":
            color = "#28a745"
        elif estado in {"FALLÓ_CUADRE", "ERROR_DATOS"}:
            color = "#dc3545"
        else:
            color = "#ffc107"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(registro.get("fecha_hora_registro") or ""))}</td>
            <td>{escape(str(registro.get("fecha_proceso") or ""))}</td>
            <td>{escape(str(registro.get("conexion") or ""))}</td>
            <td>{escape(str(registro.get("total_general_aster") or ""))}</td>
            <td>{escape(str(registro.get("filas_excel") or ""))}</td>
            <td>{escape(str(registro.get("registros_insertados") or ""))}</td>
            <td style='font-weight:bold; color:{color};'>{escape(estado)}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("archivo_excel") or ""))}</td>
            <td>{escape(str(registro.get("archivo_reporte_entidades") or ""))}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("ruta_reporte_entidades") or ""))}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("mensaje") or ""))}</td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <div class='log-line info' style='margin-top:10px;'>
        Base local historial: <code>{escape(ASTER_HISTORIAL_DB)}</code>
    </div>
    """

    return html



def _generar_html_reporte_final_aster(
    fecha_yyyymmdd: str,
    detalle_cuadre: dict[str, Any],
    ruta_entidades: str,
    nombre_entidades: str,
    total_entidades: int,
) -> str:
    """
    Genera reporte visual final de Fase H ASTER.
    """
    cumple = bool(detalle_cuadre.get("cumple"))

    if cumple:
        html = """
        <div class='log-line success'>
            ✅ Proceso ASTER correcto. La cantidad insertada coincide con el Excel y con el Total general ASTER.
        </div>
        """
    else:
        html = """
        <div class='log-line error'>
            ❌ Proceso ASTER falló. La cantidad insertada no coincide con el Excel o con el Total general ASTER.
        </div>
        """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Filas del archivo Excel", detalle_cuadre.get("filas_excel")),
        ("Registros insertados", detalle_cuadre.get("registros_insertados")),
        ("Total general ASTER", detalle_cuadre.get("total_general_aster")),
        ("Resultado de comparación", "CORRECTO" if cumple else "FALLÓ"),
        ("Archivo de entidades creado", nombre_entidades),
        ("Ruta archivo entidades", ruta_entidades),
        ("Entidades filtradas exportadas", total_entidades),
    ]

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Reporte final Fase H ASTER
            </th>
        </tr>
    """

    for etiqueta, valor in filas:
        color = ""

        if etiqueta == "Resultado de comparación":
            color = "color:#28a745;" if cumple else "color:#dc3545;"

        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all; font-weight:bold; {color}'>
                {escape(str(valor))}
            </td>
        </tr>
        """

    html += "</table>"

    return html



def _generar_html_insert_ok_aster(
    conexion: str,
    ruta_archivo: str,
    total_leidos: int,
    total_insertados: int,
    columnas_insertadas: list[str],
    columnas_clave: list[str],
    detalle_cuadre: dict[str, Any],
    ruta_entidades: str,
    nombre_entidades: str,
    total_entidades: int,
) -> str:
    """
    Genera HTML de inserción exitosa ASTER con validación final.
    """
    conexion_txt = "REMOTO - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - PRUEBAS"

    html = """
    <div class='log-line success'>
        ✅ Inserción ASTER completada correctamente.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen inserción ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Conexión usada", conexion_txt),
        ("Tabla destino", f"{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}"),
        ("Archivo", ruta_archivo),
        ("Registros leídos del Excel", total_leidos),
        ("Registros duplicados detectados", 0),
        ("Registros insertados", total_insertados),
        ("Columnas insertadas", ", ".join(columnas_insertadas)),
        ("Clave anti-duplicados", ", ".join(columnas_clave)),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.8rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += _generar_html_reporte_final_aster(
        fecha_yyyymmdd=_obtener_fecha_proceso_aster(),
        detalle_cuadre=detalle_cuadre,
        ruta_entidades=ruta_entidades,
        nombre_entidades=nombre_entidades,
        total_entidades=total_entidades,
    )

    return html



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

    html = _crear_html_total_aster(
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

        return _crear_html_total_aster(
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

        return _generar_html_archivo_aster(
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

        return _generar_html_normalizacion_aster(
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

        return _generar_html_entidades_excel_aster(
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

        return _generar_html_consulta_sql_aster(
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

        return _generar_html_conciliacion_aster(resultado)

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

        return _generar_html_conciliacion_aster(resultado)

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
                return _generar_html_errores_validacion_insert_aster(
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

        return _generar_html_preparacion_insercion_aster(
            conexion=conexion,
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
            return _generar_html_errores_validacion_insert_aster(
                resultado.get("errores", [])
            )

        if status == "duplicados":
            return _generar_html_duplicados_aster(
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

            return _generar_html_reporte_final_aster(
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

        return _generar_html_insert_ok_aster(
            conexion=conexion,
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

        return _generar_html_historial_cargas_aster(registros)

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error consultando historial ASTER: {escape(str(exc))}</div>"


def _columnas_mysql_usuarios_fase_i() -> list[str]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return columnas_mysql_usuarios_fase_i_service()

def _columnas_mysql_comentarios_fase_i() -> list[str]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return columnas_mysql_comentarios_fase_i_service()

def _obtener_config_mysql_fase_i(database: str) -> dict[str, Any]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return obtener_config_mysql_fase_i_service(database)

def _conectar_mysql_fase_i(database: str):
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return conectar_mysql_fase_i_service(database)

def _validar_sql_mysql_solo_select(sql: str) -> None:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    validar_sql_mysql_solo_select_service(sql)

def _obtener_fecha_fase_i(fecha_raw: str = "") -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return obtener_fecha_fase_i_service(
        fecha_raw=fecha_raw,
        fecha_default=_obtener_fecha_proceso_aster(),
    )


def _ruta_entidades_fase_i(fecha_yyyymmdd: str) -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return ruta_entidades_fase_i_service(
        data_dir=DATA_DIR,
        fecha_yyyymmdd=fecha_yyyymmdd,
    )

def _leer_entidades_fase_i(fecha_yyyymmdd: str) -> tuple[list[str], str]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return leer_entidades_fase_i_service(
        data_dir=DATA_DIR,
        fecha_yyyymmdd=fecha_yyyymmdd,
    )


def _obtener_columnas_sqlserver_fase_i(
    conexion: str,
    tabla: str,
) -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_sqlserver_service.
    """
    return obtener_columnas_sqlserver_tabla(
        conexion=conexion,
        sql_local=SQL_LOCAL,
        sql_remoto=SQL_REMOTO,
        base=ASTER_FASE_I_BASE,
        schema=ASTER_FASE_I_SCHEMA,
        tabla=tabla,
    )


def _comparar_columnas_fase_i(
    columnas_origen: list[str],
    columnas_destino: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return comparar_columnas_fase_i_service(
        columnas_origen=columnas_origen,
        columnas_destino=columnas_destino,
    )

def _contar_usuarios_mysql_fase_i() -> int:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return contar_usuarios_mysql_fase_i_service(
        db_usuarios=ASTER_MYSQL_DB_USUARIOS,
    )

def _contar_comentarios_mysql_fase_i(
    fecha_yyyymmdd: str,
    entidades: list[str],
) -> int:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return contar_comentarios_mysql_fase_i_service(
        db_gestion=ASTER_MYSQL_DB_GESTION,
        fecha_yyyymmdd=fecha_yyyymmdd,
        entidades=entidades,
    )


def _generar_tabla_comparacion_fase_i(
    titulo: str,
    comparacion: list[dict[str, Any]],
) -> str:
    """
    HTML de comparación de columnas Fase I.
    """
    html = f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='7' style='background:#1e3a5f; color:#fff;'>
                {escape(titulo)}
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Columna origen</th>
            <th>Columna destino</th>
            <th>Tipo SQL</th>
            <th>Longitud</th>
            <th>Nullable</th>
            <th>Estado</th>
        </tr>
    """

    for idx, fila in enumerate(comparacion, start=1):
        estado = str(fila.get("estado") or "")

        if estado == "OK":
            color = "#28a745"
            texto_estado = "✅ OK"
        else:
            color = "#dc3545"
            texto_estado = "❌ No existe en destino"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila.get("columna_origen") or ""))}</b></td>
            <td><b>{escape(str(fila.get("columna_destino") or ""))}</b></td>
            <td>{escape(str(fila.get("tipo_sql") or ""))}</td>
            <td>{escape(str(fila.get("longitud") or ""))}</td>
            <td>{escape(str(fila.get("nullable") or ""))}</td>
            <td style='font-weight:bold; color:{color};'>{texto_estado}</td>
        </tr>
        """

    html += "</table>"

    return html


def _generar_html_preparacion_fase_i(
    fecha_yyyymmdd: str,
    conexion: str,
    ruta_entidades: str,
    total_entidades: int,
    total_usuarios: int,
    total_comentarios: int,
    comparacion_usuarios: list[dict[str, Any]],
    comparacion_comentarios: list[dict[str, Any]],
) -> str:
    """
    Reporte visual de preparación Fase I.
    """
    conexion_txt = "REMOTO - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - DESARROLLO"

    html = """
    <div class='log-line success'>
        ✅ Preparación Fase I ASTER completada correctamente. No se ejecutó DELETE ni INSERT.
    </div>
    """

    if conexion == "remoto":
        html += """
        <div class='log-line warning'>
            ⚠️ Conexión REMOTA seleccionada. Está habilitada, pero corresponde a producción.
        </div>
        """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen preparación Fase I ASTER
            </th>
        </tr>
    """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Conexión SQL Server", conexion_txt),
        ("Base destino", ASTER_FASE_I_BASE),
        ("Archivo entidades", ruta_entidades),
        ("Entidades usadas en filtro", total_entidades),
        ("Usuarios origen MySQL", total_usuarios),
        ("Comentarios origen MySQL filtrados", total_comentarios),
        ("Tarea SQL pendiente", "DELETE FROM Aster_Api.dbo.usuarios"),
        ("Anti-duplicados comentarios", "id + data + usuario"),
    ]

    for etiqueta, valor in filas:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += _generar_tabla_comparacion_fase_i(
        "Comparación usuarios.crm → Aster_Api.dbo.usuarios",
        comparacion_usuarios,
    )

    html += _generar_tabla_comparacion_fase_i(
        "Comparación gestioncomercial.comentarios → Aster_Api.dbo.comentarios",
        comparacion_comentarios,
    )

    html += """
    <div id='aster-fase-i-data' style='display:none;' data-preparado='1'></div>
    """

    return html

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

        return _generar_html_preparacion_fase_i(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
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



def _nombre_tabla_sql_fase_i(tabla: str) -> str:
    """
    Devuelve nombre calificado para tablas de Fase I.
    """
    return (
        f"{_sql_identificador_aster(ASTER_FASE_I_SCHEMA)}."
        f"{_sql_identificador_aster(tabla)}"
    )


def _leer_usuarios_mysql_fase_i() -> pd.DataFrame:
    """
    Lee usuarios desde MySQL usuarios.crm.
    Solo SELECT.

    Se usa cursor.fetchall() para evitar problemas de interpretación con pandas.read_sql.
    """
    columnas = _columnas_mysql_usuarios_fase_i()

    columnas_sql = ", ".join(
        f"`{col}` AS `{col}`"
        for col in columnas
    )

    sql = f"""
        SELECT {columnas_sql}
        FROM crm
    """

    _validar_sql_mysql_solo_select(sql)

    conn = _conectar_mysql_fase_i(ASTER_MYSQL_DB_USUARIOS)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            filas = cursor.fetchall()

        return pd.DataFrame(filas, columns=columnas)

    finally:
        conn.close()

def _leer_comentarios_mysql_fase_i(
    fecha_yyyymmdd: str,
    entidades: list[str],
) -> pd.DataFrame:
    """
    Lee comentarios desde MySQL gestioncomercial.comentarios filtrando por fecha y entidad.
    Solo SELECT.

    Se usa cursor.fetchall() con alias explícitos para evitar que Pandas cambie o interprete mal columnas.
    """
    columnas = _columnas_mysql_comentarios_fase_i()

    if not entidades:
        return pd.DataFrame(columns=columnas)

    columnas_sql = ", ".join(
        f"`{col}` AS `{col}`"
        for col in columnas
    )

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    placeholders = ", ".join(["%s"] * len(entidades))

    sql = f"""
        SELECT {columnas_sql}
        FROM comentarios
        WHERE DATE(`fecha`) = %s
          AND `entidad` IN ({placeholders})
          AND COALESCE(TRIM(usuario), '') <> 'SystemUser'
    """

    _validar_sql_mysql_solo_select(sql)

    conn = _conectar_mysql_fase_i(ASTER_MYSQL_DB_GESTION)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, [fecha_sql, *entidades])
            filas = cursor.fetchall()

        df = pd.DataFrame(filas, columns=columnas)

        return df

    finally:
        conn.close()


def _transformar_comentarios_fase_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica transformación de columna derivada del flujo SSIS.

    Regla:
    fechaagenda = '1900-01-01 00:00:00' -> NULL
    """
    df_transformado = df.copy()

    if "fechaagenda" in df_transformado.columns:
        fechas_agenda = pd.to_datetime(
            df_transformado["fechaagenda"],
            errors="coerce",
        )

        fecha_base = pd.Timestamp("1900-01-01 00:00:00")

        df_transformado.loc[
            fechas_agenda == fecha_base,
            "fechaagenda",
        ] = None

    return df_transformado


def _preparar_columnas_insert_fase_i(
    df: pd.DataFrame,
    columnas_sql: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Determina columnas comunes entre origen y destino para insertar.
    Excluye identity.
    """
    origen_por_lower = {
        str(col).lower(): str(col)
        for col in df.columns
    }

    columnas_insert: list[dict[str, Any]] = []

    for col_sql in columnas_sql:
        if int(col_sql.get("is_identity") or 0) == 1:
            continue

        nombre_sql = str(col_sql["columna"])
        nombre_origen = origen_por_lower.get(nombre_sql.lower())

        if not nombre_origen:
            continue

        columnas_insert.append(
            {
                "origen": nombre_origen,
                "sql": nombre_sql,
                "tipo_sql": str(col_sql["tipo_sql"]),
                "nullable": str(col_sql["nullable"]),
                "longitud": col_sql.get("longitud"),
                "precision": col_sql.get("precision"),
                "escala": col_sql.get("escala"),
            }
        )

    return columnas_insert


def _construir_dataframe_insert_fase_i(
    df: pd.DataFrame,
    columnas_insert: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Construye DataFrame listo para insertar en SQL Server.
    """
    data_convertida: dict[str, list[Any]] = {}

    for col in columnas_insert:
        nombre_origen = str(col["origen"])
        nombre_sql = str(col["sql"])
        tipo_sql = str(col["tipo_sql"])

        data_convertida[nombre_sql] = [
            _convertir_valor_sql_aster(valor, tipo_sql)
            for valor in df[nombre_origen].tolist()
        ]

    df_insert = pd.DataFrame(data_convertida)
    df_insert = _normalizar_dataframe_sql_aster(df_insert)

    return df_insert


def _validar_columnas_minimas_fase_i(
    columnas_insert: list[dict[str, Any]],
    columnas_requeridas: list[str],
    nombre_tabla: str,
) -> str | None:
    """
    Valida columnas mínimas para insertar.
    """
    nombres = {
        str(col["sql"]).lower()
        for col in columnas_insert
    }

    faltantes = [
        columna
        for columna in columnas_requeridas
        if columna.lower() not in nombres
    ]

    if faltantes:
        return (
            f"Faltan columnas requeridas para {nombre_tabla}: "
            + ", ".join(faltantes)
        )

    return None


def _insertar_dataframe_sql_fase_i(
    cursor: Any,
    tabla: str,
    df_insert: pd.DataFrame,
    tamano_lote: int = 1000,
) -> int:
    """
    Inserta un DataFrame en SQL Server por lotes.
    """
    if df_insert.empty:
        return 0

    columnas = list(df_insert.columns)
    tabla_sql = _nombre_tabla_sql_fase_i(tabla)

    columnas_sql = ", ".join(
        _sql_identificador_aster(columna)
        for columna in columnas
    )
    placeholders = ", ".join("?" for _ in columnas)

    sql_insert = f"""
        INSERT INTO {tabla_sql} ({columnas_sql})
        VALUES ({placeholders})
    """

    total_insertados = 0
    cursor.fast_executemany = True

    for inicio in range(0, len(df_insert), tamano_lote):
        bloque = df_insert.iloc[inicio : inicio + tamano_lote]

        valores = [
            tuple(
                _limpiar_parametro_sql_aster(row[columna])
                for columna in columnas
            )
            for _, row in bloque.iterrows()
        ]

        cursor.executemany(sql_insert, valores)
        total_insertados += len(valores)

    return total_insertados


def _validar_columnas_duplicado_comentarios_fase_i(
    df_insert: pd.DataFrame,
) -> list[str]:
    """
    Valida que existan las columnas de clave anti-duplicados.

    Regla definida:
    id + data + usuario
    """
    columnas_clave = ["id", "data", "usuario"]

    columnas_lower = {
        str(col).lower(): str(col)
        for col in df_insert.columns
    }

    faltantes = [
        columna
        for columna in columnas_clave
        if columna.lower() not in columnas_lower
    ]

    if faltantes:
        raise ValueError(
            "No se puede validar duplicados en comentarios. Faltan columnas: "
            + ", ".join(faltantes)
        )

    return [
        columnas_lower[columna.lower()]
        for columna in columnas_clave
    ]

def _validar_claves_comentarios_fase_i(
    df_insert: pd.DataFrame,
    limite_ejemplos: int = 20,
) -> list[dict[str, Any]]:
    """
    Valida que la clave anti-duplicados tenga valores reales.

    Clave obligatoria:
    id + data + usuario
    """
    columnas_clave = _validar_columnas_duplicado_comentarios_fase_i(df_insert)

    errores: list[dict[str, Any]] = []

    for idx, row in df_insert.iterrows():
        faltantes = []

        for columna in columnas_clave:
            valor = row[columna]

            if _es_valor_vacio_aster(valor):
                faltantes.append(columna)

        if faltantes:
            errores.append(
                {
                    "fila": int(idx) + 2,
                    "id": row.get("id", ""),
                    "data": row.get("data", ""),
                    "usuario": row.get("usuario", ""),
                    "problema": "Clave anti-duplicados incompleta: "
                    + ", ".join(faltantes),
                }
            )

        if len(errores) >= limite_ejemplos:
            return errores

    return errores


def _generar_html_claves_invalidas_comentarios_fase_i(
    errores: list[dict[str, Any]],
) -> str:
    """
    Muestra errores de claves incompletas antes de validar duplicados.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Fase I bloqueada. Se detectaron {len(errores)} registros con clave anti-duplicados incompleta.
    </div>
    <div class='log-line warning'>
        No se ejecutó DELETE ni INSERT. Revise los datos origen de MySQL o la conversión antes de continuar.
    </div>
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Clave anti-duplicados requerida
            </th>
        </tr>
        <tr>
            <td><b>Columnas</b></td>
            <td>id + data + usuario</td>
        </tr>
    </table>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Fila</th>
            <th>id</th>
            <th>data</th>
            <th>usuario</th>
            <th>Problema</th>
        </tr>
    """

    for idx, error in enumerate(errores, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(error.get("fila", "")))}</td>
            <td>{escape(str(error.get("id", "")))}</td>
            <td>{escape(str(error.get("data", "")))}</td>
            <td>{escape(str(error.get("usuario", "")))}</td>
            <td style='color:#dc3545; font-weight:bold;'>
                {escape(str(error.get("problema", "")))}
            </td>
        </tr>
        """

    html += "</table>"

    html += """
    <div class='log-line warning' style='margin-top:10px;'>
        Diagnóstico: id, data y usuario son obligatorios para validar duplicados en comentarios.
    </div>
    """

    return html

def _contar_duplicados_comentarios_fase_i(
    cursor: Any,
    df_insert: pd.DataFrame,
    fecha_yyyymmdd: str,
    limite_ejemplos: int = 10,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Valida duplicados en Aster_Api.dbo.comentarios usando:

    id + data + usuario

    La fecha del proceso se mantiene como parámetro para trazabilidad,
    pero la clave real de duplicidad es exclusivamente id + data + usuario.
    """
    columnas_clave = _validar_columnas_duplicado_comentarios_fase_i(df_insert)

    if df_insert.empty:
        return 0, []

    df_claves_base = df_insert[columnas_clave].copy()
    df_claves_base = _normalizar_dataframe_sql_aster(df_claves_base)

    # 1. Duplicados dentro del lote origen MySQL.
    duplicados_origen = df_claves_base.duplicated(
        subset=columnas_clave,
        keep=False,
    )

    if duplicados_origen.any():
        ejemplos_origen = []

        for _, fila in df_claves_base.loc[duplicados_origen, columnas_clave].head(
            limite_ejemplos
        ).iterrows():
            ejemplos_origen.append(
                {
                    columna: fila[columna]
                    for columna in columnas_clave
                }
            )

        return int(duplicados_origen.sum()), ejemplos_origen

    # 2. Crear tabla temporal con claves del lote.
    cursor.execute(
        "IF OBJECT_ID('tempdb..#fase_i_comentarios_claves') IS NOT NULL "
        "DROP TABLE #fase_i_comentarios_claves"
    )

    cursor.execute(
        f"""
        SELECT TOP 0
            {_sql_identificador_aster(columnas_clave[0])},
            {_sql_identificador_aster(columnas_clave[1])},
            {_sql_identificador_aster(columnas_clave[2])}
        INTO #fase_i_comentarios_claves
        FROM {_nombre_tabla_sql_fase_i(ASTER_FASE_I_TABLA_COMENTARIOS)}
        """
    )

    df_claves = df_claves_base.drop_duplicates().copy()

    columnas_sql = ", ".join(
        _sql_identificador_aster(columna)
        for columna in columnas_clave
    )
    placeholders = ", ".join("?" for _ in columnas_clave)

    sql_insert_temp = f"""
        INSERT INTO #fase_i_comentarios_claves ({columnas_sql})
        VALUES ({placeholders})
    """

    valores_temp = [
        tuple(
            _limpiar_parametro_sql_aster(row[columna])
            for columna in columnas_clave
        )
        for _, row in df_claves.iterrows()
    ]

    cursor.fast_executemany = True
    cursor.executemany(sql_insert_temp, valores_temp)

    condiciones_join = []

    for columna in columnas_clave:
        col = _sql_identificador_aster(columna)

        if columna.lower() in {"data", "usuario"}:
            condiciones_join.append(
                f"""(
                    (t.{col} COLLATE DATABASE_DEFAULT = k.{col} COLLATE DATABASE_DEFAULT)
                    OR (t.{col} IS NULL AND k.{col} IS NULL)
                )"""
            )
        else:
            condiciones_join.append(
                f"((t.{col} = k.{col}) OR (t.{col} IS NULL AND k.{col} IS NULL))"
            )

    join_sql = " AND ".join(condiciones_join)

    columnas_select = ", ".join(
        f"t.{_sql_identificador_aster(columna)}"
        for columna in columnas_clave
    )

    sql_ejemplos = f"""
        SELECT TOP ({limite_ejemplos})
            {columnas_select}
        FROM {_nombre_tabla_sql_fase_i(ASTER_FASE_I_TABLA_COMENTARIOS)} t
        INNER JOIN #fase_i_comentarios_claves k
            ON {join_sql}
    """

    cursor.execute(sql_ejemplos)
    rows = cursor.fetchall()

    ejemplos: list[dict[str, Any]] = []

    for row in rows:
        ejemplo = {}

        for idx, columna in enumerate(columnas_clave):
            ejemplo[columna] = row[idx]

        ejemplos.append(ejemplo)

    if ejemplos:
        return len(ejemplos), ejemplos

    return 0, []


def _generar_html_duplicados_comentarios_fase_i(
    total_duplicados: int,
    ejemplos: list[dict[str, Any]],
) -> str:
    """
    HTML de bloqueo por duplicados en comentarios Fase I.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Fase I bloqueada. Se detectaron {total_duplicados} duplicados en comentarios.
    </div>
    <div class='log-line warning'>
        No se ejecutó COMMIT. Se aplicó ROLLBACK de la transacción.
    </div>
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Clave anti-duplicados comentarios
            </th>
        </tr>
        <tr>
            <td><b>Columnas</b></td>
            <td>id + data + usuario</td>
        </tr>
    </table>
    """

    if ejemplos:
        html += """
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr style='background:#1e3a5f; color:#fff;'>
                <th>#</th>
                <th>id</th>
                <th>data</th>
                <th>usuario</th>
            </tr>
        """

        for idx, ejemplo in enumerate(ejemplos, start=1):
            html += f"""
            <tr>
                <td>{idx}</td>
                <td>{escape(str(ejemplo.get("id", "")))}</td>
                <td>{escape(str(ejemplo.get("data", "")))}</td>
                <td>{escape(str(ejemplo.get("usuario", "")))}</td>
            </tr>
            """

        html += "</table>"

    return html


def _agregar_paso_pipeline_fase_i(
    pipeline: list[dict[str, Any]],
    paso: int,
    proceso: str,
    origen: str,
    destino: str,
    accion: str,
    cantidad: int | str,
    estado: str = "OK",
) -> None:
    """
    Agrega un paso al pipeline visual de Fase I ASTER.
    """
    pipeline.append(
        {
            "paso": paso,
            "proceso": proceso,
            "origen": origen,
            "destino": destino,
            "accion": accion,
            "cantidad": cantidad,
            "estado": estado,
        }
    )


def _generar_html_pipeline_fase_i(pipeline: list[dict[str, Any]]) -> str:
    """
    Genera tabla visual del pipeline Fase I ASTER.
    """
    if not pipeline:
        return ""

    html = """
    <table class='dataframe' style='width:100%; margin-top:12px;'>
        <tr>
            <th colspan='7' style='background:#1e3a5f; color:#fff;'>
                Pipeline de ejecución Fase I ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>Paso</th>
            <th>Proceso</th>
            <th>Origen</th>
            <th>Destino</th>
            <th>Acción</th>
            <th>Cantidad</th>
            <th>Estado</th>
        </tr>
    """

    for item in pipeline:
        estado = str(item.get("estado", ""))
        color = "#28a745" if estado.upper() == "OK" else "#dc3545"

        html += f"""
        <tr>
            <td>{escape(str(item.get("paso", "")))}</td>
            <td><b>{escape(str(item.get("proceso", "")))}</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(item.get("origen", "")))}</td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(item.get("destino", "")))}</td>
            <td>{escape(str(item.get("accion", "")))}</td>
            <td><b>{escape(str(item.get("cantidad", "")))}</b></td>
            <td style='font-weight:bold; color:{color};'>{escape(estado)}</td>
        </tr>
        """

    html += "</table>"

    return html


def _boton_generar_gestion_aster_fase_i(
    fecha_yyyymmdd: str,
    conexion: str,
) -> str:
    """
    Botón visual para generar el Excel de Gestión ASTER después de Fase I.
    """
    return f"""
    <div class='log-line info' style='margin-top:12px;'>
        📌 Fase I terminada. Puede generar el archivo de Gestión ASTER.
    </div>

    <button
        type='button'
        onclick='generarGestionAsterFaseI(this)'
        data-fecha='{escape(str(fecha_yyyymmdd))}'
        data-conexion='{escape(str(conexion))}'
        style='margin-top:8px;'
    >
        Generar Gestión ASTER Excel
    </button>

    <div id='resultado-gestion-aster-fase-i' style='margin-top:10px;'></div>
    """
    



def _generar_html_reporte_fase_i(
    fecha_yyyymmdd: str,
    conexion: str,
    ruta_entidades: str,
    total_entidades: int,
    usuarios_leidos: int,
    usuarios_insertados: int,
    comentarios_leidos: int,
    comentarios_insertados: int,
    estado: str,
    mensaje: str,
    pipeline: list[dict[str, Any]] | None = None,
    mostrar_boton_gestion: bool = False,
) -> str:
    """
    Reporte visual final Fase I.
    """
    conexion_txt = "REMOTO - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - DESARROLLO"

    if estado == "CORRECTO":
        html = """
        <div class='log-line success'>
            ✅ Fase I ASTER completada correctamente.
        </div>
        """
    else:
        html = """
        <div class='log-line error'>
            ❌ Fase I ASTER finalizó con error.
        </div>
        """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Reporte final Fase I ASTER
            </th>
        </tr>
    """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Conexión SQL Server", conexion_txt),
        ("Base destino", ASTER_FASE_I_BASE),
        ("Archivo entidades", ruta_entidades),
        ("Entidades usadas en filtro", total_entidades),
        ("Usuarios leídos MySQL", usuarios_leidos),
        ("Usuarios insertados SQL Server", usuarios_insertados),
        ("Comentarios leídos MySQL", comentarios_leidos),
        ("Comentarios insertados SQL Server", comentarios_insertados),
        ("Anti-duplicados comentarios", "id + data + usuario"),
        ("Estado", estado),
        ("Mensaje", mensaje),
    ]

    for etiqueta, valor in filas:
        color = ""

        if etiqueta == "Estado":
            color = "color:#28a745;" if estado == "CORRECTO" else "color:#dc3545;"

        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all; font-weight:bold; {color}'>
                {escape(str(valor))}
            </td>
        </tr>
        """

    html += "</table>"

    if pipeline:
        html += _generar_html_pipeline_fase_i(pipeline)

    if mostrar_boton_gestion and estado == "CORRECTO":
        html += _boton_generar_gestion_aster_fase_i(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
        )

    return html

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

            return _generar_html_claves_invalidas_comentarios_fase_i(
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

            return _generar_html_duplicados_comentarios_fase_i(
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

        return _generar_html_reporte_fase_i(
            fecha_yyyymmdd=fecha_yyyymmdd,
            conexion=conexion,
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


def _ejecutar_consulta_gestion_aster_fase_i(
    cursor: Any,
    fecha_yyyymmdd: str,
) -> pd.DataFrame:
    """
    Ejecuta la consulta final de Gestión ASTER para la fecha del proceso.
    """
    fecha_inicio = datetime.strptime(fecha_yyyymmdd, "%Y%m%d")
    fecha_fin = fecha_inicio + timedelta(days=1)

    sql = """
    WITH
    CTE_Aster_Base AS (
        SELECT
            Codigo,
            Fecha_Hora,
            Duracion,
            Estado,
            Atendio,
            Numero,
            Cartera,
            CASE
                WHEN Estado = 'ATENDIDO'
                 AND Atendio IN ('HUMANO', 'DESCONOCIDO')
                THEN 1 ELSE 0
            END AS EsHumano
        FROM [dbo].[aster_dia_nc]
        WHERE Fecha_Hora >= ? AND Fecha_Hora < ?
    ),

    CTE_Comentarios_Base AS (
        SELECT
            [data],
            resultado1,
            resultado2,
            datapers,
            usuario,
            comentario
        FROM [dbo].[comentarios]
        WHERE fecha >= ? AND fecha < ?
    ),

    CTE_Maquinas AS (
        SELECT DISTINCT
            Codigo AS Cliente_Nro,
            Fecha_Hora,
            Duracion,
            CASE
                WHEN Estado = 'OCUPADO' AND Atendio = 'NULL' THEN 'Telefono Ocupado'
                WHEN Estado = 'ATENDIDO' AND Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                WHEN Estado = 'NO ATENDIDO' AND Atendio = 'NULL' THEN 'No contestan'
                WHEN Estado = 'ATENDIDO' AND Atendio = 'CORTO' THEN 'No contestan'
                WHEN Estado = 'CONGESTION' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                WHEN Estado = 'SIN CANALES' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                ELSE 'Usuario pide volver a llamar'
            END AS [Descripcion Codigo De Gestion],
            '' AS Fecha_Compromiso,
            '' AS Grabador,
            Numero AS Telefonos,
            CASE
                WHEN Codigo IS NULL OR LTRIM(RTRIM(Codigo)) = '' THEN NULL
                WHEN Codigo LIKE 'M%' THEN 'Mobile'
                ELSE 'Home'
            END AS [Tipo Cartera],
            '' AS Asesor,
            Cartera AS [Antiguedad De La Cartera],
            '' AS [Nota de la Gestion],
            'codmaquina' AS [Clase de Gestion],
            '' AS [Causal de Mora/Respuesta]
        FROM CTE_Aster_Base
        WHERE EsHumano = 0
    ),

    CTE_Humanos_Processed AS (
        SELECT
            _dia.Codigo AS Cliente_Nro,
            _dia.Fecha_Hora,
            _dia.Duracion,
            _dia.Numero AS Telefonos,
            _dia.Cartera AS [Antiguedad De La Cartera],
            CASE
                WHEN _contactada.resultado1 IS NULL
                  OR LTRIM(RTRIM(_contactada.resultado1)) = ''
                THEN 'codmaquina'
                ELSE 'TEL'
            END AS [Clase de Gestion],

            LTRIM(RTRIM(CASE
                WHEN _contactada.resultado1 IS NULL
                  OR LTRIM(RTRIM(_contactada.resultado1)) = ''
                THEN
                    CASE
                        WHEN _dia.Estado = 'OCUPADO' AND _dia.Atendio = 'NULL' THEN 'Telefono Ocupado'
                        WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                        WHEN _dia.Estado = 'NO ATENDIDO' AND _dia.Atendio = 'NULL' THEN 'No contestan'
                        WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CORTO' THEN 'No contestan'
                        WHEN _dia.Estado = 'CONGESTION' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                        WHEN _dia.Estado = 'SIN CANALES' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                        ELSE 'Usuario pide volver a llamar'
                    END
                ELSE [dbo].[Obtener_Estado](_contactada.resultado1, _contactada.resultado2)
            END)) AS [Desc_Raw],

            CASE
                WHEN CHARINDEX('compromisos<=>', _contactada.datapers) > 0 THEN
                    REPLACE(
                        SUBSTRING(
                            _contactada.datapers,
                            CHARINDEX('compromisos<=>', _contactada.datapers) + 14,
                            CASE
                                WHEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers)) > 0
                                THEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers))
                                   - (CHARINDEX('compromisos<=>', _contactada.datapers) + 14)
                                ELSE 10
                            END
                        ),
                        '-',
                        '/'
                    )
                ELSE ''
            END AS Fecha_Compromiso,

            [dbo].[Obtener_Usuario](_contactada.usuario) AS Grabador,

            CASE
                WHEN _dia.Codigo IS NULL OR LTRIM(RTRIM(_dia.Codigo)) = '' THEN NULL
                WHEN _dia.Codigo LIKE 'M%' THEN 'Mobile'
                ELSE 'Home'
            END AS [Tipo Cartera],

            _contactada.usuario AS Asesor,

            LTRIM(RTRIM(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(_contactada.comentario, CHAR(9), ''),
                            CHAR(10),
                            ''
                        ),
                        CHAR(13),
                        ''
                    ),
                    CHAR(160),
                    ' '
                )
            )) AS [Nota_Clean],

            LTRIM(RTRIM([dbo].[Obtener_Causal_Mora](_contactada.resultado2)))
                AS [Causal de Mora/Respuesta]
        FROM CTE_Aster_Base _dia
        LEFT JOIN CTE_Comentarios_Base _contactada
            ON _dia.Codigo = _contactada.[data]
        WHERE _dia.EsHumano = 1
    ),

    CTE_Humanos_Final AS (
        SELECT DISTINCT
            Cliente_Nro,
            Fecha_Hora,
            Duracion,
            CASE
                WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
                 AND [Clase de Gestion] = 'codmaquina'
                THEN 'No contestan'
                ELSE [Desc_Raw]
            END AS [Descripcion Codigo De Gestion],
            Fecha_Compromiso,
            Grabador,
            Telefonos,
            [Tipo Cartera],
            Asesor,
            [Antiguedad De La Cartera],
            CASE
                WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
                 AND [Clase de Gestion] = 'codmaquina'
                THEN ''
                ELSE [Nota_Clean]
            END AS [Nota de la Gestion],
            [Clase de Gestion],
            [Causal de Mora/Respuesta]
        FROM CTE_Humanos_Processed
    ),

    CTE_Universo AS (
        SELECT * FROM CTE_Maquinas
        UNION ALL
        SELECT * FROM CTE_Humanos_Final
    )

    SELECT
        Cliente_Nro AS [Cliente Nro.],
        FORMAT(Fecha_Hora, 'dd/MM/yyyy') AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), Fecha_Hora, 108), '00:00:00') AS [Hora De Gestion],
        FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(Duracion AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
        [Descripcion Codigo De Gestion],
        Fecha_Compromiso,
        Grabador,
        'Vencorp' AS [Responsable De Cobro],
        Telefonos,
        [Tipo Cartera],
        Asesor,
        [Antiguedad De La Cartera],
        [Nota de la Gestion],
        [Clase de Gestion],
        [Causal de Mora/Respuesta]
    FROM CTE_Universo
    ORDER BY [Clase de Gestion], [Hora De Gestion]
    """

    cursor.execute(sql, fecha_inicio, fecha_fin, fecha_inicio, fecha_fin)

    columnas = [columna[0] for columna in cursor.description]
    filas = cursor.fetchall()

    return pd.DataFrame.from_records(filas, columns=columnas)


def _tratar_gestion_aster_antes_excel(
    df_gestion: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Tratamiento final antes de exportar Gestión ASTER a Excel.

    Reglas:
    1. Eliminar valores NULL / None / NaN / NaT / 'NULL' / 'nan' reemplazándolos por vacío.
    2. Si 'Descripcion Codigo De Gestion' inicia con 'Acuerdo',
       debe conservar Fecha_Compromiso.
    3. Si NO inicia con 'Acuerdo',
       Fecha_Compromiso debe quedar vacío.
    """
    df_tratado = df_gestion.copy()

    total_filas = len(df_tratado)

    # 1. Reemplazar nulos reales por vacío.
    df_tratado = df_tratado.replace(
        {
            None: "",
            pd.NA: "",
            pd.NaT: "",
        }
    )

    df_tratado = df_tratado.fillna("")

    # 2. Reemplazar textos que representan nulos por vacío.
    valores_null_texto = {
        "NULL",
        "null",
        "None",
        "none",
        "NaN",
        "nan",
        "NaT",
        "nat",
    }

    celdas_null_texto = 0

    for columna in df_tratado.columns:
        serie_texto = df_tratado[columna].astype(str).str.strip()
        mascara_null_texto = serie_texto.isin(valores_null_texto)
        celdas_null_texto += int(mascara_null_texto.sum())
        df_tratado.loc[mascara_null_texto, columna] = ""

    col_descripcion = "Descripcion Codigo De Gestion"
    col_fecha_compromiso = "Fecha_Compromiso"

    fechas_compromiso_limpiadas = 0
    acuerdos_sin_fecha_compromiso = 0
    acuerdos_con_fecha_compromiso = 0

    if col_descripcion in df_tratado.columns and col_fecha_compromiso in df_tratado.columns:
        descripcion = df_tratado[col_descripcion].astype(str).str.strip()
        fecha_compromiso = df_tratado[col_fecha_compromiso].astype(str).str.strip()

        mascara_acuerdo = descripcion.str.startswith("Acuerdo", na=False)
        mascara_no_acuerdo = ~mascara_acuerdo

        fechas_compromiso_limpiadas = int(
            (mascara_no_acuerdo & (fecha_compromiso != "")).sum()
        )

        # 3. Si NO inicia con Acuerdo, Fecha_Compromiso queda vacío.
        df_tratado.loc[mascara_no_acuerdo, col_fecha_compromiso] = ""

        # 4. Diagnóstico de acuerdos.
        fecha_compromiso_post = df_tratado[col_fecha_compromiso].astype(str).str.strip()

        acuerdos_con_fecha_compromiso = int(
            (mascara_acuerdo & (fecha_compromiso_post != "")).sum()
        )

        acuerdos_sin_fecha_compromiso = int(
            (mascara_acuerdo & (fecha_compromiso_post == "")).sum()
        )

    resumen = {
        "total_filas": total_filas,
        "celdas_null_texto_limpiadas": celdas_null_texto,
        "fechas_compromiso_limpiadas_no_acuerdo": fechas_compromiso_limpiadas,
        "acuerdos_con_fecha_compromiso": acuerdos_con_fecha_compromiso,
        "acuerdos_sin_fecha_compromiso": acuerdos_sin_fecha_compromiso,
    }

    return df_tratado, resumen


def _ruta_gestion_aster_fase_i(fecha_yyyymmdd: str) -> tuple[str, str]:
    """
    Devuelve nombre y ruta del Excel Gestión ASTER.

    Nueva ubicación:
    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Gestion
    """
    carpeta_gestion = ruta_aster_subcarpeta(
        DATA_DIR,
        fecha_yyyymmdd,
        "Gestion",
    )
    os.makedirs(carpeta_gestion, exist_ok=True)

    nombre_archivo = f"{fecha_yyyymmdd}_Gestion_aster.xlsx"
    ruta_archivo = os.path.join(carpeta_gestion, nombre_archivo)

    return nombre_archivo, ruta_archivo



@aster_bp.route("/accion/aster-fase-i-generar-gestion", methods=["POST"])
def accion_aster_fase_i_generar_gestion():
    """
    Genera Excel de Gestión ASTER después de ejecutar correctamente Fase I.
    """
    conn_sql = None

    try:
        payload = request.get_json(silent=True) or {}

        fecha_yyyymmdd = _obtener_fecha_fase_i(
            str(payload.get("fecha_proceso", "")).strip()
        )

        conexion = str(payload.get("conexion", "local")).strip().lower()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        cadena = _obtener_cadena_sqlserver_aster(conexion)

        conn_sql = pyodbc.connect(cadena, timeout=10)
        conn_sql.timeout = 120

        cursor = conn_sql.cursor()
        cursor.execute(f"USE [{ASTER_FASE_I_BASE}]")

        df_gestion = _ejecutar_consulta_gestion_aster_fase_i(
            cursor,
            fecha_yyyymmdd,
        )

        df_gestion, resumen_tratamiento = _tratar_gestion_aster_antes_excel(
            df_gestion
        )

        nombre_archivo, ruta_archivo = _ruta_gestion_aster_fase_i(fecha_yyyymmdd)

        df_gestion.to_excel(ruta_archivo, index=False)

        return f"""
        <div class='log-line success'>
            ✅ Gestión ASTER generada correctamente.
        </div>

        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                    Archivo Gestión ASTER
                </th>
            </tr>
            <tr><td><b>Fecha proceso</b></td><td>{escape(fecha_yyyymmdd)}</td></tr>
            <tr><td><b>Conexión</b></td><td>{escape(conexion)}</td></tr>
            <tr><td><b>Registros generados</b></td><td>{len(df_gestion)}</td></tr>
            <tr>
                <td><b>NULL / NaN limpiados</b></td>
                <td>{resumen_tratamiento.get("celdas_null_texto_limpiadas", 0)}</td>
            </tr>
            <tr>
                <td><b>Fecha_Compromiso limpiada en no Acuerdo</b></td>
                <td>{resumen_tratamiento.get("fechas_compromiso_limpiadas_no_acuerdo", 0)}</td>
            </tr>
            <tr>
                <td><b>Acuerdos con Fecha_Compromiso</b></td>
                <td>{resumen_tratamiento.get("acuerdos_con_fecha_compromiso", 0)}</td>
            </tr>
            <tr>
                <td><b>Acuerdos sin Fecha_Compromiso</b></td>
                <td>{resumen_tratamiento.get("acuerdos_sin_fecha_compromiso", 0)}</td>
            </tr>
            <tr><td><b>Archivo</b></td><td>{escape(nombre_archivo)}</td></tr>
            <tr>
                <td><b>Ruta completa</b></td>
                <td style='font-size:0.75rem; word-break:break-all;'>
                    {escape(ruta_archivo)}
                </td>
            </tr>
        </table>
        """

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error generando Gestión ASTER: {escape(str(exc))}</div>"

    finally:
        if conn_sql is not None:
            conn_sql.close()
            



@aster_bp.route("/accion/aster-total-actual", methods=["GET"])
def accion_aster_total_actual():
    """
    Devuelve el total ASTER actual guardado en sesión.
    """
    total: Any = session.get("total_aster")

    if total is None:
        return "<div class='log-line warning'>⚠️ Todavía no hay total ASTER registrado.</div>"

    return _crear_html_total_aster(
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

        return _generar_html_preparar_depuracion_aster(
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

        return _generar_html_exclusiones_aplicadas_aster(
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

        return _generar_html_clasificacion_final_aster(
            removidos=removidos,
            cobranza=cobranza,
            integral=integral,
            no_seleccionados=no_seleccionados,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error guardando clasificación ASTER: {escape(str(exc))}</div>"


    
    
    