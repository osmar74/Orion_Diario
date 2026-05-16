"""
Blueprint para la Fase G: Carga de datos a SQL Server.
"""

import os
import traceback
import pyodbc
import pandas as pd
import numpy as np
from flask import Blueprint, request, session

from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import (
    construir_cadena_conexion,
    normalizar_texto,
    mapear_columnas_archivo,
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
        conn_str = construir_cadena_conexion(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        query = "SELECT TOP 5 * FROM Causales"
        df = pd.read_sql(query, conn)
        conn.close()
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
            val = cursor.fetchone()[0]
            if val is not None:
                ultimo_id = val
        except Exception:
            pass

        # Conteo de registros en la tabla
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        total_tabla = cursor.fetchone()[0]
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
        registros_antes = cursor.fetchone()[0]

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
                df_insert[col_srv] = pd.to_datetime(
                    df_insert[col_srv], errors="coerce", dayfirst=True
                )
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
                        years = df_insert.loc[mask, col_srv].dt.year
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
                elif isinstance(val, (pd.Int64Dtype, np.int64)):
                    tupla.append(int(val))
                else:
                    tupla.append(val)
            datos.append(tuple(tupla))

        # Ejecutar inserción
        cursor.executemany(sql, datos)
        conn.commit()

        # Contar después de insertar
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        registros_despues = cursor.fetchone()[0]
        insertados = registros_despues - registros_antes
        exito = insertados == registros_archivo

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
