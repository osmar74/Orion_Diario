"""
Blueprint para la Fase G: Carga de datos a SQL Server.
"""

import os
import re
import pyodbc
import pandas as pd
import numpy as np
from flask import Blueprint, request, session

from typing import cast
from datetime import datetime

from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import (
    construir_cadena_conexion,
    construir_sqlalchemy_engine,
    normalizar_texto,
    mapear_columnas_archivo,
)

from app.services.load_registry import (
    buscar_carga_previa,
    calcular_sha256,
    registrar_carga,
)

from app.services.schema_validator import (
    generar_html_errores_longitud,
    obtener_columnas_texto_sql,
    validar_longitudes_dataframe,
)

carga_bp = Blueprint("carga", __name__)
def generar_tabla_estadisticas_consolidado(titulo, filas):
    """
    Genera una tabla HTML simple para mostrar estadísticas del consolidado.

    filas debe ser una lista de tuplas:
    [
        ("Descripción", valor),
        ...
    ]
    """
    html = f"""
    <div style='margin-top:10px; margin-bottom:10px;'>
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                    {titulo}
                </th>
            </tr>
    """

    for descripcion, valor in filas:
        html += f"""
            <tr>
                <td><b>{descripcion}</b></td>
                <td style='font-size:1rem; font-weight:bold;'>{valor}</td>
            </tr>
        """

    html += """
        </table>
    </div>
    """

    return html

def _generar_html_reporte_nombre_lote_orion(reporte_lotes):
    """
    Genera tabla visual de asignación Nombre_Lote desde Discador[Lote].
    """
    if not reporte_lotes:
        return """
        <div class='log-line warning'>
            ⚠️ No se generó reporte de asignación Nombre_Lote.
        </div>
        """

    html = """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='6' style='background:#1e3a5f; color:#fff;'>
                Asignación Nombre_Lote desde Discador[Lote]
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Archivo lote</th>
            <th>Nombre base</th>
            <th>Nombre_Lote asignado</th>
            <th>Similitud</th>
            <th>Estado</th>
        </tr>
    """

    for idx, fila in enumerate(reporte_lotes, start=1):
        estado = str(fila.get("estado", ""))

        if estado == "OK":
            color = "#28a745"
            texto_estado = "✅ OK"
        elif estado == "REVISAR":
            color = "#ffc107"
            texto_estado = "⚠️ Revisar"
        else:
            color = "#dc3545"
            texto_estado = "❌ Sin coincidencia confiable"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{fila.get("archivo_lote", "")}</td>
            <td>{fila.get("nombre_base", "")}</td>
            <td><b>{fila.get("nombre_lote_asignado", "")}</b></td>
            <td>{fila.get("similitud", "")}</td>
            <td style='font-weight:bold; color:{color};'>{texto_estado}</td>
        </tr>
        """

    html += "</table>"

    return html




@carga_bp.route("/accion/probar-conexion", methods=["POST"])
def accion_probar_conexion():
    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    if not servidor or not basedatos:
        return "<div class='log-line error'>❌ Faltan datos obligatorios.</div>"

    try:
        cfg = {
            "server": servidor,
            "port": puerto,
            "database": basedatos,
            "auth": autenticacion,
            "username": usuario,
            "password": password,
        }
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return f"<div class='log-line success'>✅ Conexión exitosa a {servidor}/{basedatos}</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}</div>"


@carga_bp.route("/accion/probar-lectura", methods=["POST"])
def accion_probar_lectura():
    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    if not servidor or not basedatos:
        return "<div class='log-line error'>❌ Faltan datos obligatorios.</div>"

    try:
        cfg = {
            "server": servidor,
            "port": puerto,
            "database": basedatos,
            "auth": autenticacion,
            "username": usuario,
            "password": password,
        }

        query = "SELECT TOP 5 * FROM Causales"

        engine = construir_sqlalchemy_engine(cfg)

        try:
            with engine.connect() as conn_sqlalchemy:
                df = pd.read_sql(query, conn_sqlalchemy)
        finally:
            engine.dispose()


        if df.empty:
            return "<div class='log-line warning'>⚠️ La tabla Causales existe pero no contiene registros.</div>"
        html = "<div class='log-line success'>✅ Lectura exitosa. {} registros encontrados.</div>".format(
            len(df)
        )
        html += df.to_html(index=False, classes="dataframe")
        return html
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer Causales: {e}</div>"


@carga_bp.route("/accion/verificar-carga", methods=["POST"])
def accion_verificar_carga():
    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    # --- Rutas y tabla destino ---
    ruta_archivo = None
    nombre_archivo = None
    tabla_destino = None
    if tipo == "causales":
        carpeta = os.path.join(carpeta_diaria, "Causales")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Causales_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Causales"
    elif tipo == "lote":
        carpeta = os.path.join(carpeta_diaria, "Lotes")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Lote_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Lote"
    elif tipo == "discador":
        archivos = [
            f
            for f in os.listdir(carpeta_diaria)
            if "discador" in f.lower() and f.endswith("Consolidado.xlsx")
        ]
        if archivos:
            ruta_archivo = os.path.join(carpeta_diaria, archivos[0])
            nombre_archivo = archivos[0]
        tabla_destino = "Discador"
    else:
        return "<div class='log-line error'>❌ Tipo de carga no válido.</div>"

    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return f"<div class='log-line error'>❌ No se encontró el archivo consolidado de {tipo}.</div>"

    # Leer archivo
    try:
        df_archivo_str = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer el archivo: {e}"

    columnas_archivo_originales = df_archivo_str.columns.tolist()
    columnas_archivo_para_match = mapear_columnas_archivo(
        columnas_archivo_originales, tipo
    )
    columnas_archivo_norm = [
        normalizar_texto(col) for col in columnas_archivo_para_match
    ]

    # Conexión y metadatos de la tabla
    try:
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? 
            ORDER BY ORDINAL_POSITION
        """,
            tabla_destino,
        )
        info_columnas = cursor.fetchall()
        if not info_columnas:
            conn.close()
            return f"<div class='log-line error'>❌ No se encontró la tabla {tabla_destino} en la base de datos.</div>"

        columnas_servidor = [row.COLUMN_NAME for row in info_columnas]
        tipos_servidor = {row.COLUMN_NAME: row.DATA_TYPE for row in info_columnas}
        columnas_servidor_norm = [normalizar_texto(col) for col in columnas_servidor]

        # Último ID
        ultimo_id = None
        try:
            primera_col = columnas_servidor[0]
            cursor.execute(
                f"SELECT MAX(CAST({primera_col} AS BIGINT)) FROM [{tabla_destino}]"
            )
            row = cursor.fetchone()
            val = row[0] if row else None

            if val is not None:
                ultimo_id = val
        except Exception:
            pass

        # Conteo de registros en la tabla
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        row = cursor.fetchone()
        total_tabla = row[0] if row else 0
        conn.close()
    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}"

    # Construir HTML
    html = f"<div class='log-line success'>✅ Verificación de {tipo.capitalize()} (conexión {conexion})</div>"
    html += f"<p style='font-size:0.75rem;'><b>Archivo:</b> {nombre_archivo}<br><b>Ruta:</b> {ruta_archivo}</p>"
    html += f"<p style='font-size:0.75rem;'><b>Tabla destino:</b> {tabla_destino} ({len(columnas_servidor)} columnas)</p>"

    # Tabla de columnas del servidor con coincidencias (solo columnas del servidor)
    html += "<table class='dataframe' style='width:100%;'>"
    html += "<tr><th>Columna SQL Server</th><th>Columna en Archivo</th><th>Coincide</th><th>Tipo SQL</th></tr>"
    for i, col_srv in enumerate(columnas_servidor):
        norm_srv = columnas_servidor_norm[i]
        match_col = None
        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break
        coincide = "✅" if match_col else "❌"
        tipo_srv = tipos_servidor.get(col_srv, "?")
        html += f"<tr><td>{col_srv}</td><td>{match_col or '—'}</td><td>{coincide}</td><td>{tipo_srv}</td></tr>"
    html += "</table>"

    # Estadísticas
    html += "<div style='display:flex; gap:20px; margin-top:10px; font-size:0.75rem;'>"
    html += f"<div><b>Registros en archivo:</b> {len(df_archivo_str)}</div>"
    if ultimo_id is not None:
        html += f"<div><b>Último ID en tabla:</b> {ultimo_id}</div>"
    html += f"<div><b>Registros en tabla:</b> {total_tabla}</div>"
    html += "</div>"

    # Botón para insertar datos
    html += f"""
    <div style='margin-top:12px;'>
        <button onclick="insertarDatos('{tipo}', '{conexion}')" 
                style="background:#28a745; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; font-size:0.8rem;">
            📤 Insertar datos en {tabla_destino}
        </button>
    </div>
    <div id="resultado-insercion-{tipo}" style="margin-top:10px;"></div>
    """

    return html


def _parsear_fecha_orion_segura(valor):
    """
    Convierte fechas ORION de forma segura para SQL Server.

    Soporta:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM:SS
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM:SS
    - YYYY-DD-MM solo cuando el segundo valor es > 12

    Devuelve datetime de Python o None.
    """
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    texto = str(valor).strip()

    if not texto or texto.lower() in {"nan", "nat", "none", "null"}:
        return None

    texto = texto.replace("T", " ")

    # 1. Formato ISO correcto: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS
    match_iso = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?$",
        texto,
    )

    if match_iso:
        anio = int(match_iso.group(1))
        segundo = int(match_iso.group(2))
        tercero = int(match_iso.group(3))
        hora = int(match_iso.group(4) or 0)
        minuto = int(match_iso.group(5) or 0)
        segundo_hora = int(match_iso.group(6) or 0)

        # Caso normal: YYYY-MM-DD
        if 1 <= segundo <= 12 and 1 <= tercero <= 31:
            return datetime(anio, segundo, tercero, hora, minuto, segundo_hora)

        # Caso detectado: YYYY-DD-MM
        if segundo > 12 and 1 <= tercero <= 12:
            return datetime(anio, tercero, segundo, hora, minuto, segundo_hora)

    # 2. Formato latino: DD/MM/YYYY o DD-MM-YYYY
    match_latam = re.match(
        r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?$",
        texto,
    )

    if match_latam:
        dia = int(match_latam.group(1))
        mes = int(match_latam.group(2))
        anio = int(match_latam.group(3))
        hora = int(match_latam.group(4) or 0)
        minuto = int(match_latam.group(5) or 0)
        segundo_hora = int(match_latam.group(6) or 0)

        return datetime(anio, mes, dia, hora, minuto, segundo_hora)

    # 3. Fallback controlado
    fecha = pd.to_datetime(texto, errors="coerce", dayfirst=False)

    if pd.isna(fecha):
        fecha = pd.to_datetime(texto, errors="coerce", dayfirst=True)

    if pd.isna(fecha):
        return None

    return fecha.to_pydatetime()




@carga_bp.route("/accion/insertar-datos", methods=["POST"])
def accion_insertar_datos():
    """Realiza la inserción de los datos una vez verificada la compatibilidad de columnas."""
    import traceback

    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    # ---------- Rutas y tabla destino ----------
    ruta_archivo = None
    nombre_archivo = None
    tabla_destino = None
    if tipo == "causales":
        carpeta = os.path.join(carpeta_diaria, "Causales")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Causales_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Causales"
    elif tipo == "lote":
        carpeta = os.path.join(carpeta_diaria, "Lotes")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Lote_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Lote"
    elif tipo == "discador":
        archivos = [
            f
            for f in os.listdir(carpeta_diaria)
            if "discador" in f.lower() and f.endswith("Consolidado.xlsx")
        ]
        if archivos:
            ruta_archivo = os.path.join(carpeta_diaria, archivos[0])
            nombre_archivo = archivos[0]
        tabla_destino = "Discador"
    else:
        return "<div class='log-line error'>❌ Tipo de carga no válido.</div>"

    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return f"<div class='log-line error'>❌ No se encontró el archivo consolidado de {tipo}.</div>"

    # Leer archivo
    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer el archivo: {e}"

    registros_archivo = len(df)
    
    archivo_hash = calcular_sha256(ruta_archivo)
    carga_previa = buscar_carga_previa(
        tipo=tipo,
        conexion=conexion,
        tabla_destino=tabla_destino,
        archivo_hash=archivo_hash,
    )

    if carga_previa:
        return f"""
        <div class='log-line warning'>
            ⚠️ Este archivo ya fue insertado anteriormente.
        </div>
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='2' style='background:#8a6d3b; color:#fff;'>
                    Carga duplicada bloqueada
                </th>
            </tr>
            <tr><td><b>Tipo</b></td><td>{tipo}</td></tr>
            <tr><td><b>Conexión</b></td><td>{conexion}</td></tr>
            <tr><td><b>Tabla destino</b></td><td>{tabla_destino}</td></tr>
            <tr><td><b>Archivo</b></td><td>{carga_previa['nombre_archivo']}</td></tr>
            <tr><td><b>Registros archivo</b></td><td>{carga_previa['registros_archivo']}</td></tr>
            <tr><td><b>Registros insertados</b></td><td>{carga_previa['registros_insertados']}</td></tr>
            <tr><td><b>Fecha de carga</b></td><td>{carga_previa['fecha_carga']}</td></tr>
        </table>
        """
    

    # Normalización de columnas
    columnas_archivo_originales = df.columns.tolist()
    columnas_archivo_para_match = mapear_columnas_archivo(
        columnas_archivo_originales, tipo
    )
    columnas_archivo_norm = [
        normalizar_texto(col) for col in columnas_archivo_para_match
    ]

    # Conexión y metadatos
    try:
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? 
            ORDER BY ORDINAL_POSITION
        """,
            tabla_destino,
        )
        info_columnas = cursor.fetchall()
        if not info_columnas:
            conn.close()
            return f"<div class='log-line error'>❌ La tabla {tabla_destino} no existe en la base de datos.</div>"

        columnas_servidor = [row.COLUMN_NAME for row in info_columnas]
        tipos_servidor = {row.COLUMN_NAME: row.DATA_TYPE for row in info_columnas}

        # Contar registros antes
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        row = cursor.fetchone()
        registros_antes = row[0] if row else 0

    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}"

    # Construir mapeo de columnas
    mapeo_final = {}
    for col_srv in columnas_servidor:
        norm_srv = normalizar_texto(col_srv)
        match_col = None
        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break
        if match_col:
            mapeo_final[col_srv] = match_col

    # ---------- Conversión de tipos e inserción ----------
    try:
        columnas_insert = list(mapeo_final.keys())
        df_insert = pd.DataFrame()

        for col_srv in columnas_insert:
            col_arch = mapeo_final[col_srv]
            df_insert[col_srv] = df[col_arch]

        # Validar longitudes de columnas de texto antes del INSERT.
        # Esto evita errores SQL como:
        # String or binary data would be truncated
        columnas_texto_sql = obtener_columnas_texto_sql(conn, tabla_destino)
        # if tipo == "discador" and "FechayHora" in df_insert.columns:
        #     print("DEBUG FechayHora Discador:")
        #     print(df_insert["FechayHora"].head(10).tolist())
        errores_longitud = validar_longitudes_dataframe(df_insert, columnas_texto_sql)

        if errores_longitud:
            conn.close()
            return generar_html_errores_longitud(errores_longitud)

        # Conversión de tipos
        for col_srv, tipo_srv in tipos_servidor.items():
            if col_srv not in df_insert.columns:
                continue
            if tipo_srv in ("nvarchar", "varchar", "char", "text", "ntext"):
                df_insert[col_srv] = df_insert[col_srv].astype(str)
            elif tipo_srv in ("int", "smallint", "tinyint", "bigint"):
                df_insert[col_srv] = pd.to_numeric(
                    df_insert[col_srv], errors="coerce"
                ).astype("Int64")
            elif tipo_srv in ("float", "real", "decimal", "numeric", "money"):
                df_insert[col_srv] = pd.to_numeric(df_insert[col_srv], errors="coerce")
            elif tipo_srv in ("datetime", "datetime2", "smalldatetime", "date"):
                df_insert[col_srv] = df_insert[col_srv].map(_parsear_fecha_orion_segura)
            elif tipo_srv == "bit":
                df_insert[col_srv] = (
                    df_insert[col_srv]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map(
                        {
                            "1": True,
                            "true": True,
                            "yes": True,
                            "0": False,
                            "false": False,
                            "no": False,
                        }
                    )
                )

        # Limpiar fechas fuera de rango
        for col_srv, tipo_srv in tipos_servidor.items():
            if tipo_srv in ("datetime", "datetime2", "smalldatetime", "date"):
                if col_srv in df_insert.columns:
                    mask = df_insert[col_srv].notna()
                    if mask.any():
                        serie_fechas = cast(pd.Series, df_insert.loc[mask, col_srv])
                        fechas_validas = pd.to_datetime(serie_fechas, errors="coerce")
                        years = fechas_validas.dt.year
                        invalid = (years < 1753) | (years > 9999)
                        df_insert.loc[mask & invalid, col_srv] = None

        # Construir INSERT SQL
        columnas_sql = ", ".join([f"[{col}]" for col in columnas_insert])
        placeholders = ", ".join(["?" for _ in columnas_insert])
        sql = f"INSERT INTO [{tabla_destino}] ({columnas_sql}) VALUES ({placeholders})"

        # Preparar datos
        datos = []
        for _, row in df_insert.iterrows():
            tupla = []
            for col in columnas_insert:
                val = row[col]
                if pd.isna(val):
                    tupla.append(None)
                elif isinstance(val, pd.Timestamp):
                    tupla.append(val.to_pydatetime())
                elif isinstance(val, np.integer):
                    tupla.append(int(val))
                elif isinstance(val, np.floating):
                    tupla.append(float(val))
                else:
                    tupla.append(val)
            datos.append(tuple(tupla))

        # Ejecutar inserción
        cursor.executemany(sql, datos)
        conn.commit()

        # Contar después de insertar
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        row = cursor.fetchone()
        registros_despues = row[0] if row else registros_antes
        insertados = registros_despues - registros_antes
        exito = insertados == registros_archivo

        if exito:
            registrar_carga(
                tipo=tipo,
                conexion=conexion,
                tabla_destino=tabla_destino,
                nombre_archivo=nombre_archivo,
                ruta_archivo=ruta_archivo,
                archivo_hash=archivo_hash,
                registros_archivo=registros_archivo,
                registros_insertados=insertados,
            )

        conn.close()

        # Construir HTML de respuesta con formato de tablas
        color_coincide = "#28a745" if exito else "#dc3545"
        texto_coincide = "Coincide" if exito else "No coincide"

        html = f"<div style='margin-top:10px;'>"
        html += f"<div class='log-line {'success' if exito else 'error'}'>"
        html += f"{'✅' if exito else '⚠️'} Inserción de {tipo.capitalize()} completada.</div>"

        # Primera tabla: datos del archivo
        html += "<table class='dataframe' style='width:100%; margin-top:10px;'>"
        html += "<tr><th colspan='2' style='background:#1e3a5f; color:#fff;'>Información de la carga</th></tr>"
        html += f"<tr><td><b>Tabla destino</b></td><td>{tabla_destino}</td></tr>"
        html += f"<tr><td><b>Archivo</b></td><td>{nombre_archivo}</td></tr>"
        html += f"<tr><td><b>Ruta</b></td><td style='font-size:0.7rem;'>{ruta_archivo}</td></tr>"
        html += "</table>"

        # Segunda tabla: estadísticas de inserción
        html += "<table class='dataframe' style='width:100%; margin-top:10px;'>"
        html += "<tr style='background:#1e3a5f; color:#fff;'>"
        html += "<th>Registros en archivo</th><th>Registros antes</th><th>Registros después</th><th>Insertados</th></tr>"
        html += "<tr>"
        html += (
            f"<td style='font-size:1.1rem; font-weight:bold;'>{registros_archivo}</td>"
        )
        html += f"<td>{registros_antes}</td>"
        html += f"<td>{registros_despues}</td>"
        html += f"<td style='color:{color_coincide}; font-weight:bold;'>{insertados} ({texto_coincide})</td>"
        html += "</tr></table>"
        html += "</div>"

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        traceback.print_exc()
        html = f"<div class='log-line error'>❌ Error en la inserción: {str(e)}</div>"

    return html


@carga_bp.route("/accion/probar-conexion-consolidado")
def accion_probar_conexion_consolidado():
    """Prueba la conexión para el panel de consolidado."""
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


@carga_bp.route("/accion/consolidar-consulta", methods=["POST"])
def accion_consolidar_consulta():
    """Ejecuta la consulta SQL de consolidación y devuelve los valores únicos de Descripción."""
    import re
    import os
    import pickle
    import uuid
    import pandas as pd
    import pyodbc

    # Limpiar posibles residuos grandes en sesión de ejecuciones anteriores
    session.pop("consolidado_df", None)
    session.pop("consolidado_valores", None)

    fecha = request.form.get("fecha", "2026-05-05")
    meses = request.form.get("meses", "202605")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    # Leer el archivo SQL
    sql_path = os.path.join(os.path.dirname(__file__), "..", "sql", "consolidado.sql")
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_template = f.read()
    except FileNotFoundError:
        return "<div class='log-line error'>❌ No se encuentra el archivo SQL de consolidación.</div>"

    # Validar formatos
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        return "<div class='log-line error'>❌ Formato de fecha inválido. Use YYYY-MM-DD.</div>"
    if not re.match(r"^\d{6}$", meses):
        return "<div class='log-line error'>❌ Formato de meses inválido. Use YYYYMM.</div>"

    # Reemplazar variables en el SQL
    sql_final = sql_template.format(fecha=fecha, meses=meses)

    try:
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=60)
        engine = construir_sqlalchemy_engine(cfg)

        try:
            with engine.connect() as conn_sqlalchemy:
                df = pd.read_sql(sql_final, conn_sqlalchemy)
        finally:
            engine.dispose()
        
        conn.close()
    except Exception as e:
        return f"<div class='log-line error'>❌ Error en consulta SQL: {str(e)}</div>"

    if df.empty:
        return (
            "<div class='log-line warning'>⚠️ La consulta no devolvió resultados.</div>"
        )

    # Filtrar filas con fecha de compromiso no vacía
    df_con_fecha = df[df["Fecha_Compromiso"].notna() & (df["Fecha_Compromiso"] != "")]
    valores_unicos = sorted(
        df_con_fecha["Descripcion Codigo De Gestion"].dropna().unique()
    )

    # Guardar DataFrame en archivo temporal (no en sesión)
    temp_id = uuid.uuid4().hex[:10]
    temp_path = os.path.join(DATA_DIR, f"temp_consolidado_{temp_id}.pkl")
    with open(temp_path, "wb") as f:
        pickle.dump(df, f)

    # Construir HTML con checkboxes
    html = f"<p style='font-size:0.75rem; color:#ccc;'>Valores únicos en 'Descripción Codigo de Gestion' con fecha de compromiso ({len(valores_unicos)}):</p>"
    html += "<div style='max-height:200px; overflow-y:auto; margin-bottom:10px;'>"
    html += "<table class='dataframe' style='width:100%;'>"
    html += "<tr><th>Seleccionar</th><th>Descripción</th></tr>"
    for val in valores_unicos:
        html += f"<tr><td><input type='checkbox' name='descripcion' value='{val}'></td><td>{val}</td></tr>"
    html += "</table>"
    html += "</div>"
    html += f"<input type='hidden' id='cons-temp-id' value='{temp_id}'>"
    html += "<button onclick='aplicarFiltroYExportar()' style='background:#28a745; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; font-size:0.8rem;'>Aplicar Filtro y Exportar a Excel</button>"
    return html

def _obtener_carpeta_diaria_orion_desde_fecha(fecha: str) -> str:
    """
    Devuelve la carpeta diaria ORION.

    Entrada:
    20260429

    Salida:
    data\\orion_202604_29
    """
    fecha_limpia = "".join(ch for ch in str(fecha or "") if ch.isdigit())

    if len(fecha_limpia) != 8:
        raise ValueError(
            f"Fecha inválida para carpeta ORION: {fecha}. Se esperaba YYYYMMDD."
        )

    anio_mes = fecha_limpia[:6]
    dia = fecha_limpia[6:8]

    carpeta = os.path.join(
        DATA_DIR,
        f"orion_{anio_mes}_{dia}",
    )

    os.makedirs(carpeta, exist_ok=True)

    return carpeta


@carga_bp.route("/accion/consolidar-aplicar", methods=["POST"])
def accion_consolidar_aplicar():
    """Aplica los filtros seleccionados y exporta el Excel final."""
    import json
    import pickle
    import os
    import pandas as pd

    fecha = request.form.get("fecha", "2026-05-05")
    seleccionados = json.loads(request.form.get("seleccionados", "[]"))
    temp_id = request.form.get("temp_id")

    if not temp_id:
        return "<div class='log-line error'>❌ Falta identificador de consulta previa.</div>"

    temp_path = os.path.join(DATA_DIR, f"temp_consolidado_{temp_id}.pkl")
    if not os.path.isfile(temp_path):
        return "<div class='log-line error'>❌ Los datos de consulta previa han expirado. Ejecute la consulta nuevamente.</div>"

    try:
        with open(temp_path, "rb") as f:
            df = pickle.load(f)
        # Borrar el archivo temporal después de cargarlo
        os.remove(temp_path)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al cargar datos: {e}</div>"

    # Aplicar limpieza: para las filas con fecha de compromiso y cuyo Descripción esté en seleccionados,
    # reemplazar la fecha por vacío

    # Estadísticas antes de aplicar limpieza
    total_inicial = len(df)

    mask_fecha_antes = (
        df["Fecha_Compromiso"].notna()
        & (df["Fecha_Compromiso"].astype(str).str.strip() != "")
    )

    registros_con_fecha_antes = int(mask_fecha_antes.sum())
    registros_sin_fecha_antes = int(total_inicial - registros_con_fecha_antes)

    # Aplicar limpieza: para las filas con fecha de compromiso y cuyo Descripción esté en seleccionados,
    # reemplazar la fecha por vacío
    mask_seleccionados = df["Descripcion Codigo De Gestion"].isin(seleccionados)
    mask_limpiar = mask_fecha_antes & mask_seleccionados

    registros_seleccionados_por_filtro = int(mask_seleccionados.sum())
    registros_limpiados = int(mask_limpiar.sum())

    df.loc[mask_limpiar, "Fecha_Compromiso"] = None

    # Estadísticas después de aplicar limpieza
    mask_fecha_despues = (
        df["Fecha_Compromiso"].notna()
        & (df["Fecha_Compromiso"].astype(str).str.strip() != "")
    )

    registros_con_fecha_despues = int(mask_fecha_despues.sum())
    registros_sin_fecha_despues = int(total_inicial - registros_con_fecha_despues)
    registros_exportados = len(df)

    html_estadisticas = generar_tabla_estadisticas_consolidado(
        "Estadísticas después de aplicar filtro y exportar",
        [
            ("Registros cargados desde consulta temporal", total_inicial),
            ("Descripciones seleccionadas", len(seleccionados)),
            ("Registros con Fecha_Compromiso antes", registros_con_fecha_antes),
            ("Registros sin Fecha_Compromiso antes", registros_sin_fecha_antes),
            ("Registros que coinciden con las descripciones seleccionadas", registros_seleccionados_por_filtro),
            ("Registros limpiados", registros_limpiados),
            ("Registros con Fecha_Compromiso después", registros_con_fecha_despues),
            ("Registros sin Fecha_Compromiso después", registros_sin_fecha_despues),
            ("Registros exportados", registros_exportados),
        ],
    )

    # Exportar a Excel
    fecha_limpia = "".join(ch for ch in str(fecha or "") if ch.isdigit())

    carpeta_diaria_orion = _obtener_carpeta_diaria_orion_desde_fecha(fecha_limpia)

    nombre_archivo = f"{fecha_limpia}_Gestion_orion.xlsx"

    ruta_salida = os.path.join(
        carpeta_diaria_orion,
        nombre_archivo,
    )
    
    df.to_excel(ruta_salida, index=False)

    html = html_estadisticas
    # Generar enlace de descarga
    html = "<div class='log-line success'>✅ Excel generado correctamente.</div>"
    html += f"<p style='font-size:0.8rem;'><b>Archivo:</b> {nombre_archivo}</p>"
    html += f"<p><a href='/descargar/{nombre_archivo}' style='color:#1e90ff; text-decoration:none; font-weight:bold;'>📥 Descargar {nombre_archivo}</a></p>"
    html += f"<p style='font-size:0.7rem; color:#888;'>Ruta: {ruta_salida}</p>"
    html = html_estadisticas + html
    return html
