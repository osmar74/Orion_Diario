"""
Blueprint para Gestión Diaria ASTER.

Fase A:
- Captura del total diario por OCR.
- Captura manual del total general.
"""

import base64
import os
import re
import shutil
import unicodedata
from datetime import datetime
from html import escape
from typing import Any

import pandas as pd

from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from app.config import DATA_DIR, TESSERACT_PATH
from app.controllers.helpers import obtener_log_service
from app.services.ocr_processor import OCRProcessor


aster_bp = Blueprint("aster", __name__)

RUTAS_ASTER_DEFAULT = [
    r"Z:\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"\\10.24.90.118\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
    r"F:\Vencorp\ff\unidad_red_Data\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO"
]


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