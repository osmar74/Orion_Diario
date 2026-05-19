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
import shutil
import unicodedata
from datetime import datetime
from html import escape
from typing import Any

import pandas as pd
import pyodbc

from app.config import SQL_LOCAL, SQL_REMOTO

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor


aster_bp = Blueprint("aster", __name__)

RUTAS_ASTER_DEFAULT = [
    r"Z:\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"\\10.24.90.118\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_aster\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO"
]

ASTER_TABLA_INSERCION = "aster_dia_nc"
ASTER_SCHEMA_INSERCION = "dbo"
ASTER_BASE_INSERCION = "Aster_Api"


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
    Determina si un archivo .xlsx pertenece a la fecha ASTER.

    Se exige:
    - extensión .xlsx
    - nombre que empiece con After
    - que contenga alguna clave de fecha relevante
    """
    nombre_lower = nombre_archivo.lower()

    if not nombre_lower.endswith(".xlsx"):
        return False

    if not nombre_lower.startswith("after"):
        return False

    solo_digitos = re.sub(r"[^0-9]", "", nombre_archivo)
    claves = _claves_busqueda_fecha(fecha_yyyymmdd)

    return any(clave in solo_digitos for clave in claves)


def _buscar_archivo_aster_en_ruta(ruta_base: str, fecha_yyyymmdd: str) -> str | None:
    """
    Busca el primer archivo ASTER de la fecha indicada dentro de una ruta.
    """
    if not ruta_base or not os.path.isdir(ruta_base):
        return None

    candidatos: list[str] = []

    for nombre in os.listdir(ruta_base):
        ruta_archivo = os.path.join(ruta_base, nombre)

        if not os.path.isfile(ruta_archivo):
            continue

        if _archivo_aster_corresponde_fecha(nombre, fecha_yyyymmdd):
            candidatos.append(ruta_archivo)

    candidatos.sort()

    if candidatos:
        return candidatos[0]

    return None


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


def _normalizar_encabezado_aster(encabezado: Any) -> str:
    """
    Normaliza un encabezado ASTER.

    Reglas:
    - Quitar acentos.
    - Reemplazar espacios, /, *, - por _
    - Eliminar caracteres especiales no necesarios.
    - Colapsar múltiples guiones bajos.
    """
    texto = str(encabezado).strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(car for car in texto if not unicodedata.combining(car))

    texto = re.sub(r"[\s/\*\-]+", "_", texto)
    texto = re.sub(r"[^A-Za-z0-9_]", "", texto)
    texto = re.sub(r"_+", "_", texto)
    texto = texto.strip("_")

    if not texto:
        texto = "Columna"

    return texto


def _normalizar_lista_encabezados_aster(columnas: list[Any]) -> list[str]:
    """
    Normaliza una lista de encabezados y evita nombres duplicados.
    """
    columnas_normalizadas: list[str] = []
    contador: dict[str, int] = {}

    for columna in columnas:
        nombre_base = _normalizar_encabezado_aster(columna)

        if nombre_base not in contador:
            contador[nombre_base] = 1
            columnas_normalizadas.append(nombre_base)
            continue

        contador[nombre_base] += 1
        columnas_normalizadas.append(f"{nombre_base}_{contador[nombre_base]}")

    return columnas_normalizadas


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
    Convierte una fecha recibida en distintos formatos a YYYY-MM-DD.

    Acepta:
    - 20260513
    - 2026-05-13
    - 202605_13
    """
    fecha_yyyymmdd = _normalizar_fecha_aster(fecha_raw)

    fecha_dt = datetime.strptime(fecha_yyyymmdd, "%Y%m%d")

    return fecha_dt.strftime("%Y-%m-%d")


def _obtener_config_mysql_aster() -> dict[str, str]:
    """
    Obtiene configuración MySQL ASTER desde variables de entorno.
    """
    config = {
        "host": os.getenv("ASTER_DB_HOST", "").strip(),
        "user": os.getenv("ASTER_DB_USER", "").strip(),
        "password": os.getenv("ASTER_DB_PASSWORD", "").strip(),
        "database": os.getenv("ASTER_DB_NAME", "gestioncomercial").strip(),
    }

    faltantes = [
        nombre
        for nombre, valor in config.items()
        if nombre != "password" and not valor
    ]

    if not config["password"]:
        faltantes.append("password")

    if faltantes:
        raise ValueError(
            "Faltan variables de entorno ASTER: "
            + ", ".join(f"ASTER_DB_{campo.upper()}" for campo in faltantes)
        )

    return config


def _consultar_entidades_sql_aster(fecha_sql: str) -> list[dict[str, Any]]:
    """
    Ejecuta la consulta SQL contra el servidor ASTER.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(
            "No está instalado PyMySQL. Ejecute: pip install PyMySQL"
        ) from exc

    config = _obtener_config_mysql_aster()

    sql = """
        SELECT
            entidad,
            count(distinct data) as numero
        FROM comentarios
        WHERE DATE(fecha) = %s
        GROUP BY entidad
        ORDER BY numero DESC
    """

    conexion = pymysql.connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (fecha_sql,))
            filas = cursor.fetchall()
    finally:
        conexion.close()

    resultados: list[dict[str, Any]] = []

    for fila in filas:
        entidad = str(fila.get("entidad") or "").strip()
        numero = int(fila.get("numero") or 0)

        resultados.append(
            {
                "entidad": entidad,
                "numero": numero,
                "SSS": f"'{entidad}'",
            }
        )

    return resultados


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
    Obtiene resultados SQL ASTER guardados en sesión.
    """
    resultados = session.get("aster_resultados_sql") or []

    return [
        {
            "entidad": str(fila.get("entidad") or "").strip(),
            "numero": int(fila.get("numero") or 0),
            "SSS": str(fila.get("SSS") or ""),
        }
        for fila in resultados
        if str(fila.get("entidad") or "").strip()
    ]


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
    Obtiene entidades únicas del Excel ASTER desde sesión.
    """
    entidades = session.get("aster_entidades_excel") or []

    return sorted(
        {
            str(entidad).strip()
            for entidad in entidades
            if str(entidad).strip()
        }
    )


def _obtener_entidades_sql_validables_aster() -> list[dict[str, Any]]:
    """
    Obtiene entidades SQL disponibles para conciliación.

    Se toman:
    - Bases Cobranza %
    - Bases Integral
    - No seleccionadas

    No se toman las removidas.
    """
    cobranza = session.get("aster_bases_cobranza") or []
    integral = session.get("aster_bases_integral") or []
    no_seleccionadas = session.get("aster_bases_no_seleccionadas") or []

    combinadas = cobranza + integral + no_seleccionadas

    entidades: dict[str, dict[str, Any]] = {}

    for fila in combinadas:
        entidad = str(fila.get("entidad") or "").strip()

        if not entidad:
            continue

        entidades[entidad] = {
            "entidad": entidad,
            "numero": int(fila.get("numero") or 0),
            "SSS": str(fila.get("SSS") or f"'{entidad}'"),
        }

    return [
        entidades[entidad]
        for entidad in sorted(entidades.keys())
    ]


def _generar_html_tabla_comparativa_aster(
    entidades_excel: list[str],
    entidades_sql: list[dict[str, Any]],
    titulo: str = "Comparación Excel vs SQL ASTER",
) -> str:
    """
    Genera tabla comparativa Excel vs SQL.
    """
    set_excel = set(entidades_excel)
    set_sql = {
        str(fila.get("entidad") or "").strip()
        for fila in entidades_sql
        if str(fila.get("entidad") or "").strip()
    }

    todas = sorted(set_excel | set_sql)

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

    if not todas:
        html += """
        <tr>
            <td colspan='5' style='text-align:center; color:#888;'>
                Sin entidades para comparar.
            </td>
        </tr>
        """

    for idx, entidad in enumerate(todas, start=1):
        en_excel = entidad in set_excel
        en_sql = entidad in set_sql

        if en_excel and en_sql:
            estado = "✅ Match"
            color = "#28a745"
        elif en_excel and not en_sql:
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
    entidades_excel: list[str],
    entidades_sql: list[dict[str, Any]],
    entidades_no_tomar: set[str] | None = None,
) -> str:
    """
    Genera HTML de conciliación ASTER.
    """
    entidades_no_tomar = entidades_no_tomar or set()

    entidades_sql_ajustadas = [
        fila
        for fila in entidades_sql
        if str(fila.get("entidad") or "").strip() not in entidades_no_tomar
    ]

    set_excel = set(entidades_excel)
    set_sql = {
        str(fila.get("entidad") or "").strip()
        for fila in entidades_sql_ajustadas
        if str(fila.get("entidad") or "").strip()
    }

    faltan_en_sql = sorted(set_excel - set_sql)
    sobran_en_sql = sorted(set_sql - set_excel)
    match_ok = not faltan_en_sql and not sobran_en_sql and len(set_excel) == len(set_sql)

    html = """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen conciliación ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Entidades únicas en Excel", len(set_excel)),
        ("Entidades SQL consideradas", len(set_sql)),
        ("Entidades no tomadas en cuenta", len(entidades_no_tomar)),
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
        entidades_excel=entidades_excel,
        entidades_sql=entidades_sql_ajustadas,
    )

    if match_ok:
        session["aster_informacion_verificada"] = True
        session["aster_entidades_sql_validadas"] = entidades_sql_ajustadas
        session["aster_entidades_no_tomar"] = sorted(entidades_no_tomar)

        html = "<div class='log-line success'>✅ Información Verificada.</div>" + html

        html += """
        <div id='aster-conciliacion-data' style='display:none;' data-validado='1'></div>
        """

        return html

    session["aster_informacion_verificada"] = False

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

        for idx, entidad in enumerate(sobran_en_sql, start=1):
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
                <td><code>{escape("'" + entidad + "'")}</code></td>
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

def _obtener_cadena_sqlserver_aster(conexion: str) -> str:
    """
    Devuelve la cadena SQL Server según conexión solicitada.

    local  = pruebas
    remoto = producción
    """
    conexion_normalizada = (conexion or "local").strip().lower()

    if conexion_normalizada == "remoto":
        return SQL_REMOTO

    return SQL_LOCAL


def _valor_config_sql(config: Any, *nombres: str) -> str:
    """
    Lee un valor desde una configuración tipo dict de forma flexible.
    """
    if not isinstance(config, dict):
        return ""

    claves = {str(k).lower(): v for k, v in config.items()}

    for nombre in nombres:
        valor = claves.get(nombre.lower())

        if valor is not None:
            return str(valor).strip()

    return ""


def _construir_cadena_pyodbc_aster(config: Any) -> str:
    """
    Convierte SQL_LOCAL / SQL_REMOTO a cadena pyodbc.

    Soporta:
    - string directo
    - diccionario con server/database/user/password/driver
    """
    if isinstance(config, str):
        cadena = config.strip()

        if not cadena:
            raise ValueError("La cadena de conexión SQL Server está vacía.")

        return cadena

    if not isinstance(config, dict):
        raise TypeError(
            "La configuración SQL Server debe ser string o dict. "
            f"Tipo recibido: {type(config).__name__}"
        )

    driver = _valor_config_sql(config, "driver", "DRIVER") or "ODBC Driver 17 for SQL Server"
    server = _valor_config_sql(config, "server", "SERVER", "host", "HOST")
    database = (
        _valor_config_sql(config, "database", "DATABASE", "db", "DB")
        or ASTER_BASE_INSERCION
    )
    user = _valor_config_sql(config, "user", "USER", "uid", "UID", "username")
    password = _valor_config_sql(config, "password", "PASSWORD", "pwd", "PWD")
    trusted = _valor_config_sql(
        config,
        "trusted_connection",
        "Trusted_Connection",
        "trusted",
    )

    if not server:
        raise ValueError("Falta SERVER en la configuración SQL Server.")

    partes = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        "TrustServerCertificate=yes",
    ]

    if trusted.lower() in {"yes", "true", "1", "si", "sí"}:
        partes.append("Trusted_Connection=yes")
    else:
        if not user:
            raise ValueError("Falta USER/UID en la configuración SQL Server.")
        partes.append(f"UID={user}")
        partes.append(f"PWD={password}")

    return ";".join(partes)


def _obtener_columnas_sqlserver_aster(conexion: str) -> list[dict[str, Any]]:
    """
    Obtiene columnas de la tabla destino ASTER desde SQL Server.
    """
    cadena = _obtener_cadena_sqlserver_aster(conexion)

    sql = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """

    conn = pyodbc.connect(cadena)

    try:
        cursor = conn.cursor()

        cursor.execute(f"USE [{ASTER_BASE_INSERCION}]")

        cursor.execute(
            sql,
            ASTER_SCHEMA_INSERCION,
            ASTER_TABLA_INSERCION,
        )

        columnas: list[dict[str, Any]] = []

        for row in cursor.fetchall():
            columnas.append(
                {
                    "columna": str(row.COLUMN_NAME),
                    "tipo_sql": str(row.DATA_TYPE),
                    "nullable": str(row.IS_NULLABLE),
                    "longitud": row.CHARACTER_MAXIMUM_LENGTH,
                    "precision": row.NUMERIC_PRECISION,
                    "escala": row.NUMERIC_SCALE,
                    "orden": int(row.ORDINAL_POSITION),
                }
            )

        if not columnas:
            raise ValueError(
                "No se encontraron columnas para la tabla "
                f"{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}."
            )

        return columnas

    finally:
        conn.close()

def _obtener_cadena_sqlserver_aster(conexion: str) -> str:
    """
    Devuelve cadena pyodbc según conexión solicitada.

    local  = pruebas
    remoto = producción
    """
    conexion_normalizada = (conexion or "local").strip().lower()

    config = SQL_REMOTO if conexion_normalizada == "remoto" else SQL_LOCAL

    return _construir_cadena_pyodbc_aster(config)


def _tipo_excel_aster(serie: pd.Series) -> str:
    """
    Detecta un tipo general de columna Excel.
    """
    serie_no_nula = serie.dropna()

    if serie_no_nula.empty:
        return "vacia"

    if pd.api.types.is_integer_dtype(serie_no_nula):
        return "entero"

    if pd.api.types.is_float_dtype(serie_no_nula):
        return "decimal"

    if pd.api.types.is_datetime64_any_dtype(serie_no_nula):
        return "fecha_hora"

    valores = serie_no_nula.astype(str).str.strip()

    if valores.empty:
        return "texto"

    valores_no_vacios = valores[valores != ""]

    if valores_no_vacios.empty:
        return "texto"

    fechas = pd.to_datetime(valores_no_vacios, errors="coerce", dayfirst=False)

    if fechas.notna().mean() >= 0.8:
        return "fecha_hora"

    numeros = pd.to_numeric(valores_no_vacios, errors="coerce")

    if numeros.notna().mean() >= 0.9:
        if (numeros.dropna() % 1 == 0).all():
            return "entero"

        return "decimal"

    return "texto"


def _comparar_excel_vs_sql_aster(
    df: pd.DataFrame,
    columnas_sql: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compara columnas del Excel ASTER contra columnas SQL.
    """
    sql_por_nombre = {
        str(col["columna"]).lower(): col
        for col in columnas_sql
    }

    comparacion: list[dict[str, Any]] = []

    for columna_excel in df.columns:
        clave = str(columna_excel).lower()
        col_sql = sql_por_nombre.get(clave)

        existe = col_sql is not None

        comparacion.append(
            {
                "columna_excel": str(columna_excel),
                "tipo_excel": _tipo_excel_aster(df[columna_excel]),
                "existe_sql": existe,
                "columna_sql": str(col_sql["columna"]) if col_sql else "",
                "tipo_sql": str(col_sql["tipo_sql"]) if col_sql else "",
                "nullable": str(col_sql["nullable"]) if col_sql else "",
                "longitud": col_sql["longitud"] if col_sql else "",
                "estado": "OK" if existe else "NO_EXISTE_EN_SQL",
            }
        )

    columnas_excel_lower = {
        str(col).lower()
        for col in df.columns
    }

    for col_sql in columnas_sql:
        clave_sql = str(col_sql["columna"]).lower()

        if clave_sql in columnas_excel_lower:
            continue

        comparacion.append(
            {
                "columna_excel": "",
                "tipo_excel": "",
                "existe_sql": False,
                "columna_sql": str(col_sql["columna"]),
                "tipo_sql": str(col_sql["tipo_sql"]),
                "nullable": str(col_sql["nullable"]),
                "longitud": col_sql["longitud"],
                "estado": "NO_EXISTE_EN_EXCEL",
            }
        )

    return comparacion


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
    Busca el archivo After del día y lo copia a la carpeta local ASTER.

    Destino:
    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD
    """
    try:
        fecha_raw = request.form.get("fecha_proceso", "").strip()
        ruta_base_usuario = request.form.get("ruta_base", "").strip()

        if not fecha_raw:
            return "<div class='log-line error'>❌ Debe ingresar la fecha del proceso ASTER.</div>"

        fecha_yyyymmdd = _normalizar_fecha_aster(fecha_raw)

        rutas_busqueda = []

        if ruta_base_usuario:
            rutas_busqueda.append(ruta_base_usuario)

        rutas_busqueda.extend(RUTAS_ASTER_DEFAULT)

        ruta_origen: str | None = None

        for ruta_base in rutas_busqueda:
            ruta_encontrada = _buscar_archivo_aster_en_ruta(
                ruta_base,
                fecha_yyyymmdd,
            )

            if ruta_encontrada:
                ruta_origen = ruta_encontrada
                break

        if not ruta_origen:
            rutas_html = "<br>".join(
                f"<code>{ruta}</code>" for ruta in rutas_busqueda
            )

            return f"""
            <div class='log-line error'>
                ❌ No se encontró archivo ASTER para la fecha {fecha_yyyymmdd}.
            </div>
            <div class='log-line warning'>
                Rutas revisadas:<br>{rutas_html}
            </div>
            """

        carpeta_destino = os.path.join(
            DATA_DIR,
            fecha_yyyymmdd,
            "Aster",
            f"aster_{fecha_yyyymmdd}",
        )
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(ruta_origen)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        shutil.copy2(ruta_origen, ruta_destino)

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
        return f"<div class='log-line error'>❌ {exc}</div>"

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error buscando archivo ASTER: {exc}</div>"


@aster_bp.route("/accion/aster-normalizar-encabezados", methods=["POST"])
def accion_aster_normalizar_encabezados():
    """
    Normaliza los encabezados del archivo ASTER copiado en Fase B.
    """
    try:
        ruta_archivo = request.form.get("ruta_archivo", "").strip()

        if not ruta_archivo:
            ruta_archivo = str(session.get("aster_archivo_copiado") or "")

        if not ruta_archivo:
            return """
            <div class='log-line error'>
                ❌ No hay archivo ASTER copiado en sesión. Primero ejecute la Fase B.
            </div>
            """

        if not os.path.isfile(ruta_archivo):
            return f"""
            <div class='log-line error'>
                ❌ El archivo ASTER no existe en la ruta indicada.
            </div>
            <div class='log-line warning'>
                Ruta: <code>{ruta_archivo}</code>
            </div>
            """

        df = pd.read_excel(ruta_archivo, dtype=str)

        columnas_originales = list(df.columns)
        columnas_normalizadas = _normalizar_lista_encabezados_aster(columnas_originales)

        df.columns = columnas_normalizadas
        df.to_excel(ruta_archivo, index=False)

        session["aster_archivo_normalizado"] = ruta_archivo
        session["aster_columnas_originales"] = [str(col) for col in columnas_originales]
        session["aster_columnas_normalizadas"] = columnas_normalizadas

        return _generar_html_normalizacion_aster(
            ruta_archivo=ruta_archivo,
            columnas_originales=columnas_originales,
            columnas_normalizadas=columnas_normalizadas,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error normalizando encabezados ASTER: {exc}</div>"


@aster_bp.route("/accion/aster-entidades-excel", methods=["POST"])
def accion_aster_entidades_excel():
    """
    Obtiene valores únicos de la columna Entidad del Excel ASTER normalizado.
    """
    try:
        ruta_archivo = request.form.get("ruta_archivo", "").strip()

        if not ruta_archivo:
            ruta_archivo = str(
                session.get("aster_archivo_normalizado")
                or session.get("aster_archivo_copiado")
                or ""
            )

        if not ruta_archivo:
            return """
            <div class='log-line error'>
                ❌ No hay archivo ASTER disponible. Ejecute primero Fase B y Fase C.
            </div>
            """

        if not os.path.isfile(ruta_archivo):
            return f"""
            <div class='log-line error'>
                ❌ El archivo ASTER no existe en la ruta indicada.
            </div>
            <div class='log-line warning'>
                Ruta: <code>{escape(ruta_archivo)}</code>
            </div>
            """

        df = pd.read_excel(ruta_archivo, dtype=str)
        columnas = list(df.columns)

        if "Entidad" not in columnas:
            columnas_html = "<br>".join(
                f"<code>{escape(str(col))}</code>" for col in columnas
            )

            return f"""
            <div class='log-line error'>
                ❌ No se encontró la columna <b>Entidad</b> en el Excel ASTER.
            </div>
            <div class='log-line warning'>
                Columnas disponibles:<br>{columnas_html}
            </div>
            """

        serie_entidad = df["Entidad"].fillna("").astype(str).str.strip()
        serie_valida = serie_entidad[serie_entidad != ""]

        conteo_series = serie_valida.value_counts()

        conteo_entidades = [
            (str(entidad), int(cantidad))
            for entidad, cantidad in conteo_series.items()
        ]

        session["aster_entidades_excel"] = [
            entidad for entidad, _ in conteo_entidades
        ]
        session["aster_total_entidades_excel"] = len(conteo_entidades)
        session["aster_total_registros_excel"] = len(df)

        return _generar_html_entidades_excel_aster(
            ruta_archivo=ruta_archivo,
            total_registros=len(df),
            conteo_entidades=conteo_entidades,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error analizando entidades ASTER: {exc}</div>"


@aster_bp.route("/accion/aster-consulta-sql", methods=["POST"])
def accion_aster_consulta_sql():
    """
    Ejecuta consulta SQL ASTER para obtener entidades del día.
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

        fecha_sql = _normalizar_fecha_sql_aster(fecha_raw)
        resultados = _consultar_entidades_sql_aster(fecha_sql)

        session["aster_fecha_sql"] = fecha_sql
        session["aster_resultados_sql"] = resultados
        session["aster_total_entidades_sql"] = len(resultados)
        session["aster_total_registros_sql"] = sum(
            int(fila["numero"]) for fila in resultados
        )

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

        session["aster_entidades_no_tomar"] = []

        return _generar_html_conciliacion_aster(
            entidades_excel=entidades_excel,
            entidades_sql=entidades_sql,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error conciliando entidades ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-ajustar-conciliacion", methods=["POST"])
def accion_aster_ajustar_conciliacion():
    """
    Aplica entidades SQL que no se tomarán en cuenta y vuelve a validar.
    """
    try:
        entidades_excel = _obtener_entidades_excel_aster_desde_sesion()
        entidades_sql = _obtener_entidades_sql_validables_aster()

        entidades_no_tomar = {
            str(entidad).strip()
            for entidad in request.form.getlist("entidades_no_tomar")
            if str(entidad).strip()
        }

        session["aster_entidades_no_tomar"] = sorted(entidades_no_tomar)

        return _generar_html_conciliacion_aster(
            entidades_excel=entidades_excel,
            entidades_sql=entidades_sql,
            entidades_no_tomar=entidades_no_tomar,
        )

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error ajustando conciliación ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-probar-conexion-insercion", methods=["POST"])
def accion_aster_probar_conexion_insercion():
    """
    Prueba conexión SQL Server ASTER para inserción.
    No inserta datos.
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        cadena = _obtener_cadena_sqlserver_aster(conexion)

        conn = pyodbc.connect(cadena)

        try:
            cursor = conn.cursor()
            cursor.execute(f"USE [{ASTER_BASE_INSERCION}]")
            cursor.execute("SELECT DB_NAME() AS base_actual")
            row = cursor.fetchone()
            base_actual = str(row.base_actual)

            cursor.execute(
                """
                SELECT COUNT(*) AS total_columnas
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ?
                  AND TABLE_NAME = ?
                """,
                ASTER_SCHEMA_INSERCION,
                ASTER_TABLA_INSERCION,
            )
            row_cols = cursor.fetchone()
            total_columnas = int(row_cols.total_columnas or 0)

        finally:
            conn.close()

        if total_columnas <= 0:
            return f"""
            <div class='log-line error'>
                ❌ Conexión ASTER correcta, pero no se encontró la tabla
                {ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}.
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
                <td>{escape(base_actual)}</td>
            </tr>
            <tr>
                <td><b>Tabla destino</b></td>
                <td>{escape(f'{ASTER_BASE_INSERCION}.{ASTER_SCHEMA_INSERCION}.{ASTER_TABLA_INSERCION}')}</td>
            </tr>
            <tr>
                <td><b>Columnas detectadas</b></td>
                <td>{total_columnas}</td>
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
    """
    try:
        conexion = request.form.get("conexion", "local").strip().lower()
        ruta_archivo = request.form.get("ruta_archivo", "").strip()

        if conexion not in {"local", "remoto"}:
            conexion = "local"

        if not ruta_archivo:
            ruta_archivo = str(
                session.get("aster_archivo_normalizado")
                or session.get("aster_archivo_copiado")
                or ""
            )

        if not ruta_archivo:
            return """
            <div class='log-line error'>
                ❌ No hay archivo ASTER disponible. Ejecute primero Fase B y Fase C.
            </div>
            """

        if not os.path.isfile(ruta_archivo):
            return f"""
            <div class='log-line error'>
                ❌ El archivo ASTER no existe.
            </div>
            <div class='log-line warning'>
                Ruta: <code>{escape(ruta_archivo)}</code>
            </div>
            """

        df = pd.read_excel(ruta_archivo, dtype=str)

        columnas_sql = _obtener_columnas_sqlserver_aster(conexion)
        comparacion = _comparar_excel_vs_sql_aster(df, columnas_sql)

        session["aster_conexion_insercion"] = conexion
        session["aster_preparacion_insercion_ok"] = True
        session["aster_columnas_comparacion_sql"] = comparacion

        return _generar_html_preparacion_insercion_aster(
            conexion=conexion,
            ruta_archivo=ruta_archivo,
            total_registros=len(df),
            comparacion=comparacion,
        )

    except Exception as exc:
        session["aster_preparacion_insercion_ok"] = False
        return f"<div class='log-line error'>❌ Error preparando inserción ASTER: {escape(str(exc))}</div>"


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
    """
    try:
        resultados = _obtener_resultados_sql_aster_desde_sesion()

        if not resultados:
            return """
            <div class='log-line error'>
                ❌ No hay resultados SQL ASTER en sesión. Ejecute primero la Fase E.
            </div>
            """

        return _generar_html_preparar_depuracion_aster(resultados)

    except Exception as exc:
        return f"<div class='log-line error'>❌ Error preparando depuración ASTER: {escape(str(exc))}</div>"


@aster_bp.route("/accion/aster-aplicar-exclusiones", methods=["POST"])
def accion_aster_aplicar_exclusiones():
    """
    Aplica exclusiones seleccionadas y genera tabla de clasificación.
    """
    try:
        resultados = _obtener_resultados_sql_aster_desde_sesion()

        if not resultados:
            return """
            <div class='log-line error'>
                ❌ No hay resultados SQL ASTER en sesión. Ejecute primero la Fase E.
            </div>
            """

        entidades_excluir = set(request.form.getlist("entidades_excluir"))

        removidos = [
            fila
            for fila in resultados
            if str(fila.get("entidad") or "") in entidades_excluir
        ]

        filtrados = [
            fila
            for fila in resultados
            if str(fila.get("entidad") or "") not in entidades_excluir
        ]

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
    """
    try:
        clasificaciones_raw = request.form.get("clasificaciones", "[]")

        clasificaciones = json.loads(clasificaciones_raw)

        if not isinstance(clasificaciones, list):
            return "<div class='log-line error'>❌ Formato inválido de clasificación ASTER.</div>"

        removidos = session.get("aster_sql_removidos") or []

        cobranza: list[dict[str, Any]] = []
        integral: list[dict[str, Any]] = []
        no_seleccionados: list[dict[str, Any]] = []

        for item in clasificaciones:
            entidad = str(item.get("entidad") or "").strip()
            numero = int(item.get("numero") or 0)
            sss = str(item.get("SSS") or f"'{entidad}'")
            clasificacion = str(item.get("clasificacion") or "").strip()

            fila = {
                "entidad": entidad,
                "numero": numero,
                "SSS": sss,
            }

            if clasificacion == "cobranza":
                cobranza.append(fila)
            elif clasificacion == "integral":
                integral.append(fila)
            else:
                no_seleccionados.append(fila)

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
    
    
    