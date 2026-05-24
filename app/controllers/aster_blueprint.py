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
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

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
    obtener_fecha_fase_i as obtener_fecha_fase_i_service,
    preparar_fase_i_aster,
    probar_conexiones_fase_i_aster,
)
from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster
from app.services.aster_gestion_export_service import generar_gestion_aster_fase_i



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



def _obtener_fecha_fase_i(fecha_raw: str = "") -> str:
    """
    Compatibilidad temporal.
    La lógica real vive en app.services.aster_phase_i_prepare_service.
    """
    return obtener_fecha_fase_i_service(
        fecha_raw=fecha_raw,
        fecha_default=_obtener_fecha_proceso_aster(),
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

        resumen_tratamiento = resultado.get("resumen_tratamiento", {})

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
            <tr><td><b>Fecha proceso</b></td><td>{escape(str(resultado.get("fecha_yyyymmdd", "")))}</td></tr>
            <tr><td><b>Conexión</b></td><td>{escape(str(resultado.get("conexion", "")))}</td></tr>
            <tr><td><b>Registros generados</b></td><td>{escape(str(resultado.get("registros_generados", 0)))}</td></tr>
            <tr>
                <td><b>NULL / NaN limpiados</b></td>
                <td>{escape(str(resumen_tratamiento.get("celdas_null_texto_limpiadas", 0)))}</td>
            </tr>
            <tr>
                <td><b>Fecha_Compromiso limpiada en no Acuerdo</b></td>
                <td>{escape(str(resumen_tratamiento.get("fechas_compromiso_limpiadas_no_acuerdo", 0)))}</td>
            </tr>
            <tr>
                <td><b>Acuerdos con Fecha_Compromiso</b></td>
                <td>{escape(str(resumen_tratamiento.get("acuerdos_con_fecha_compromiso", 0)))}</td>
            </tr>
            <tr>
                <td><b>Acuerdos sin Fecha_Compromiso</b></td>
                <td>{escape(str(resumen_tratamiento.get("acuerdos_sin_fecha_compromiso", 0)))}</td>
            </tr>
            <tr><td><b>Archivo</b></td><td>{escape(str(resultado.get("nombre_archivo", "")))}</td></tr>
            <tr>
                <td><b>Ruta completa</b></td>
                <td style='font-size:0.75rem; word-break:break-all;'>
                    {escape(str(resultado.get("ruta_archivo", "")))}
                </td>
            </tr>
        </table>
        """

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


    
    
    