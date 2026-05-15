"""
Blueprint para la Fase G: Carga de datos a SQL Server.
"""

import os
import re
import unicodedata
import traceback
import pyodbc
import pandas as pd
import numpy as np
from flask import Blueprint, request, session

from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import (
    obtener_log_service,
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
        html = f"<div class='log-line success'>✅ Lectura exitosa. {len(df)} registros encontrados.</div>"
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

        ultimo_id = None
        try:
            primera_col = columnas_servidor[0]
            cursor.execute(
                f"SELECT MAX(CAST({primera_col} AS BIGINT)) FROM [{tabla_destino}]"
            )
            val = cursor.fetchone()[0]
            if val is not None:
                ultimo_id = val
        except:
            pass

        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        total_tabla = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}"

    html = f"<div class='log-line success'>✅ Verificación de {tipo.capitalize()} (conexión {conexion})</div>"
    html += f"<p style='font-size:0.75rem;'><b>Archivo:</b> {nombre_archivo}<br><b>Ruta:</b> {ruta_archivo}</p>"
    html += f"<p style='font-size:0.75rem;'><b>Tabla destino:</b> {tabla_destino} ({len(columnas_servidor)} columnas)</p>"

    html += "<table class='dataframe' style='width:100%;'>"
    html += "<tr><th>Columna SQL Server</th><th>Columna en Archivo</th><th>Coincide</th><th>Tipo SQL</th></tr>"
    mapeo_final = {}
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
        if match_col:
            mapeo_final[col_srv] = match_col

    set_norm_srv = set(columnas_servidor_norm)
    for j, col_arch in enumerate(columnas_archivo_originales):
        if columnas_archivo_norm[j] not in set_norm_srv:
            html += f"<tr><td>—</td><td>{col_arch}</td><td>❌</td><td>—</td></tr>"
    html += "</table>"

    html += "<div style='display:flex; gap:20px; margin-top:10px; font-size:0.75rem;'>"
    html += f"<div><b>Registros en archivo:</b> {len(df_archivo_str)}</div>"
    if ultimo_id is not None:
        html += f"<div><b>Último ID en tabla:</b> {ultimo_id}</div>"
    html += f"<div><b>Registros en tabla:</b> {total_tabla}</div>"
    html += "</div>"

    return html


@carga_bp.route("/accion/cargar-datos", methods=["POST"])
def accion_cargar_datos():
    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

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

    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer el archivo: {e}"

    registros_archivo = len(df)

    columnas_archivo_originales = df.columns.tolist()
    columnas_archivo_para_match = mapear_columnas_archivo(
        columnas_archivo_originales, tipo
    )
    columnas_archivo_norm = [
        normalizar_texto(col) for col in columnas_archivo_para_match
    ]

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

        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        registros_antes = cursor.fetchone()[0]

    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}"

    html_verif = "<table class='dataframe' style='width:100%;'><tr><th>Columna SQL Server</th><th>Columna en Archivo</th><th>Coincide</th><th>Tipo SQL</th></tr>"
    mapeo_final = {}
    for col_srv in columnas_servidor:
        norm_srv = normalizar_texto(col_srv)
        match_col = None
        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break
        coincide = "✅" if match_col else "❌"
        tipo_srv = tipos_servidor.get(col_srv, "?")
        html_verif += f"<tr><td>{col_srv}</td><td>{match_col or '—'}</td><td>{coincide}</td><td>{tipo_srv}</td></tr>"
        if match_col:
            mapeo_final[col_srv] = match_col

    set_norm_srv = set(normalizar_texto(c) for c in columnas_servidor)
    for j, col_arch in enumerate(columnas_archivo_originales):
        if columnas_archivo_norm[j] not in set_norm_srv:
            html_verif += f"<tr><td>—</td><td>{col_arch}</td><td>❌</td><td>—</td></tr>"
    html_verif += "</table>"

    try:
        columnas_insert = list(mapeo_final.keys())
        df_insert = pd.DataFrame()
        for col_srv in columnas_insert:
            col_arch = mapeo_final[col_srv]
            df_insert[col_srv] = df[col_arch]

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

        for col_srv, tipo_srv in tipos_servidor.items():
            if tipo_srv in ("datetime", "datetime2", "smalldatetime", "date"):
                if col_srv in df_insert.columns:
                    mask = df_insert[col_srv].notna()
                    if mask.any():
                        years = df_insert.loc[mask, col_srv].dt.year
                        invalid = (years < 1753) | (years > 9999)
                        df_insert.loc[mask & invalid, col_srv] = None

        columnas_sql = ", ".join([f"[{col}]" for col in columnas_insert])
        placeholders = ", ".join(["?" for _ in columnas_insert])
        sql = f"INSERT INTO [{tabla_destino}] ({columnas_sql}) VALUES ({placeholders})"

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

        cursor.executemany(sql, datos)
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        registros_despues = cursor.fetchone()[0]
        insertados = registros_despues - registros_antes
        exito = insertados == registros_archivo

        conn.close()

        html = f"<div class='log-line {'success' if exito else 'warning'}'>"
        html += (
            f"{'✅' if exito else '⚠️'} Carga de {tipo.capitalize()} completada.</div>"
        )
        html += f"<p style='font-size:0.8rem;'><b>Servidor:</b> {cfg['server']} / {cfg['database']}</p>"
        html += (
            f"<p style='font-size:0.8rem;'><b>Tabla destino:</b> {tabla_destino}</p>"
        )
        html += f"<p style='font-size:0.8rem;'><b>Archivo:</b> {nombre_archivo}<br><b>Ruta:</b> {ruta_archivo}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros en archivo:</b> {registros_archivo}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros antes:</b> {registros_antes}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros después:</b> {registros_despues}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Insertados:</b> {insertados} {'(coincide)' if exito else '(diferencia con archivo: ' + str(registros_archivo - insertados) + ')'}</p>"
        html += html_verif

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        traceback.print_exc()
        html = f"<div class='log-line error'>❌ Error en la carga: {str(e)}</div>"

    return html
