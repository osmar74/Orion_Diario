"""
Servicio de inserción de cargas ORION.

Responsabilidad:
- Ubicar consolidado ORION.
- Validar historial anti-duplicados.
- Leer Excel consolidado.
- Comparar columnas Excel vs SQL Server.
- Validar longitudes.
- Convertir tipos según SQL Server.
- Insertar registros.
- Registrar carga exitosa.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, cast

import numpy as np
import pandas as pd
import pyodbc

from app.controllers.helpers import (
    construir_cadena_conexion,
    mapear_columnas_archivo,
    normalizar_texto,
)
from app.services.daily_paths import ruta_orion
from app.services.load_registry import (
    buscar_carga_previa,
    calcular_sha256,
    registrar_carga,
)
from app.services.orion_file_lookup_service import buscar_archivo_consolidado_orion
from app.services.schema_validator import (
    obtener_columnas_texto_sql,
    validar_longitudes_dataframe,
)
from app.services.sql_loader import cargar_sql


TABLA_ORION_POR_TIPO = {
    "causales": "Causales",
    "lote": "Lote",
    "discador": "Discador",
}


def _sql_identificador_orion(nombre: str) -> str:
    """
    Escapa identificadores SQL Server con corchetes.
    """
    return f"[{str(nombre).replace(']', ']]')}]"


def _tabla_sql_orion(tabla_destino: str) -> str:
    """
    Devuelve tabla SQL segura.

    La tabla destino viene de TABLA_ORION_POR_TIPO, no del usuario directamente.
    """
    tablas_validas = set(TABLA_ORION_POR_TIPO.values())

    if tabla_destino not in tablas_validas:
        raise ValueError(f"Tabla ORION no permitida: {tabla_destino}")

    return _sql_identificador_orion(tabla_destino)


def parsear_fecha_orion_segura(valor: Any) -> datetime | None:
    """
    Convierte fechas ORION de forma segura para SQL Server.

    Soporta:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM:SS
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM:SS
    - YYYY-DD-MM solo cuando el segundo valor es > 12
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

    fecha = pd.to_datetime(texto, errors="coerce", dayfirst=False)

    if pd.isna(fecha):
        fecha = pd.to_datetime(texto, errors="coerce", dayfirst=True)

    if pd.isna(fecha):
        return None

    return fecha.to_pydatetime()


def _construir_mapeo_columnas(
    columnas_servidor: list[str],
    columnas_archivo_originales: list[str],
    columnas_archivo_norm: list[str],
) -> dict[str, str]:
    """
    Construye mapeo:
    columna_sql -> columna_excel
    """
    mapeo_final: dict[str, str] = {}

    for col_srv in columnas_servidor:
        norm_srv = normalizar_texto(col_srv)
        match_col = None

        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break

        if match_col:
            mapeo_final[col_srv] = match_col

    return mapeo_final


def _convertir_dataframe_a_tipos_sql(
    df_insert: pd.DataFrame,
    tipos_servidor: dict[str, str],
) -> pd.DataFrame:
    """
    Convierte columnas al tipo compatible con SQL Server.
    """
    for col_srv, tipo_srv in tipos_servidor.items():
        if col_srv not in df_insert.columns:
            continue

        tipo = str(tipo_srv).lower()

        if tipo in ("nvarchar", "varchar", "char", "text", "ntext"):
            df_insert[col_srv] = df_insert[col_srv].astype(str)

        elif tipo in ("int", "smallint", "tinyint", "bigint"):
            df_insert[col_srv] = pd.to_numeric(
                df_insert[col_srv],
                errors="coerce",
            ).astype("Int64")

        elif tipo in ("float", "real", "decimal", "numeric", "money"):
            df_insert[col_srv] = pd.to_numeric(
                df_insert[col_srv],
                errors="coerce",
            )

        elif tipo in ("datetime", "datetime2", "smalldatetime", "date"):
            df_insert[col_srv] = df_insert[col_srv].map(parsear_fecha_orion_segura)

        elif tipo == "bit":
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

    return df_insert


def _limpiar_fechas_fuera_rango(
    df_insert: pd.DataFrame,
    tipos_servidor: dict[str, str],
) -> pd.DataFrame:
    """
    SQL Server datetime no acepta años fuera de rango.
    """
    for col_srv, tipo_srv in tipos_servidor.items():
        tipo = str(tipo_srv).lower()

        if tipo not in ("datetime", "datetime2", "smalldatetime", "date"):
            continue

        if col_srv not in df_insert.columns:
            continue

        mask = df_insert[col_srv].notna()

        if not mask.any():
            continue

        serie_fechas = cast(pd.Series, df_insert.loc[mask, col_srv])
        fechas_validas = pd.to_datetime(serie_fechas, errors="coerce")
        years = fechas_validas.dt.year
        invalid = (years < 1753) | (years > 9999)

        df_insert.loc[mask & invalid, col_srv] = None

    return df_insert


def _preparar_datos_insert(
    df_insert: pd.DataFrame,
    columnas_insert: list[str],
) -> list[tuple[Any, ...]]:
    """
    Convierte DataFrame a lista de tuplas compatible con pyodbc.
    """
    datos: list[tuple[Any, ...]] = []

    for _, row in df_insert.iterrows():
        tupla: list[Any] = []

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

    return datos


def insertar_datos_orion(
    data_dir: str,
    fecha: str,
    tipo: str,
    conexion: str,
    cfg_sql: dict[str, Any],
) -> dict[str, Any]:
    """
    Inserta datos ORION desde el consolidado correspondiente.
    """
    tipo_normalizado = str(tipo or "").strip().lower()
    conexion_normalizada = str(conexion or "local").strip().lower()

    tabla_destino = TABLA_ORION_POR_TIPO.get(tipo_normalizado)

    if not tabla_destino:
        return {
            "success": False,
            "status": "error",
            "error": "Tipo de carga no válido.",
        }

    carpeta_orion = ruta_orion(data_dir, fecha)

    ruta_archivo, nombre_archivo = buscar_archivo_consolidado_orion(
        carpeta_orion,
        tipo_normalizado,
    )

    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return {
            "success": False,
            "status": "error",
            "error": f"No se encontró el archivo consolidado de {tipo_normalizado}.",
        }

    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "error": f"Error al leer el archivo: {exc}",
        }

    registros_archivo = len(df)

    archivo_hash = calcular_sha256(ruta_archivo)

    carga_previa = buscar_carga_previa(
        tipo=tipo_normalizado,
        conexion=conexion_normalizada,
        tabla_destino=tabla_destino,
        archivo_hash=archivo_hash,
    )

    if carga_previa:
        return {
            "success": False,
            "status": "duplicado",
            "tipo": tipo_normalizado,
            "conexion": conexion_normalizada,
            "tabla_destino": tabla_destino,
            "carga_previa": carga_previa,
        }

    columnas_archivo_originales = df.columns.tolist()

    columnas_archivo_para_match = mapear_columnas_archivo(
        columnas_archivo_originales,
        tipo_normalizado,
    )

    columnas_archivo_norm = [
        normalizar_texto(col)
        for col in columnas_archivo_para_match
    ]

    conn = None

    try:
        conn_str = construir_cadena_conexion(cfg_sql)
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        sql_columnas = cargar_sql("orion/columnas_tabla.sql")
        cursor.execute(sql_columnas, tabla_destino)

        info_columnas = cursor.fetchall()

        if not info_columnas:
            conn.close()
            return {
                "success": False,
                "status": "error",
                "error": f"La tabla {tabla_destino} no existe en la base de datos.",
            }

        columnas_servidor = [str(row.COLUMN_NAME) for row in info_columnas]
        tipos_servidor = {
            str(row.COLUMN_NAME): str(row.DATA_TYPE)
            for row in info_columnas
        }

        tabla_sql = _tabla_sql_orion(tabla_destino)
        sql_count = cargar_sql("orion/count_table.sql").format(tabla=tabla_sql)
        cursor.execute(sql_count)
        row = cursor.fetchone()
        registros_antes = int(row[0]) if row else 0

        mapeo_final = _construir_mapeo_columnas(
            columnas_servidor=columnas_servidor,
            columnas_archivo_originales=columnas_archivo_originales,
            columnas_archivo_norm=columnas_archivo_norm,
        )

        columnas_insert = list(mapeo_final.keys())

        if not columnas_insert:
            return {
                "success": False,
                "status": "error",
                "error": "No existen columnas coincidentes para insertar.",
            }

        df_insert = pd.DataFrame()

        for col_srv in columnas_insert:
            col_arch = mapeo_final[col_srv]
            df_insert[col_srv] = df[col_arch]

        columnas_texto_sql = obtener_columnas_texto_sql(conn, tabla_destino)
        errores_longitud = validar_longitudes_dataframe(
            df_insert,
            columnas_texto_sql,
        )

        if errores_longitud:
            return {
                "success": False,
                "status": "errores_longitud",
                "errores_longitud": errores_longitud,
            }

        df_insert = _convertir_dataframe_a_tipos_sql(
            df_insert,
            tipos_servidor,
        )

        df_insert = _limpiar_fechas_fuera_rango(
            df_insert,
            tipos_servidor,
        )

        tabla_sql = _tabla_sql_orion(tabla_destino)

        columnas_sql = ", ".join(
            _sql_identificador_orion(col)
            for col in columnas_insert
        )

        placeholders = ", ".join("?" for _ in columnas_insert)

        sql_insert = cargar_sql("orion/insert_table.sql").format(
            tabla=tabla_sql,
            columnas=columnas_sql,
            placeholders=placeholders,
        )

        datos = _preparar_datos_insert(
            df_insert,
            columnas_insert,
        )

        cursor.executemany(sql_insert, datos)
        conn.commit()

        tabla_sql = _tabla_sql_orion(tabla_destino)
        sql_count = cargar_sql("orion/count_table.sql").format(tabla=tabla_sql)
        cursor.execute(sql_count)
        row = cursor.fetchone()
        registros_despues = int(row[0]) if row else registros_antes

        insertados = registros_despues - registros_antes
        exito = insertados == registros_archivo

        if exito:
            registrar_carga(
                tipo=tipo_normalizado,
                conexion=conexion_normalizada,
                tabla_destino=tabla_destino,
                nombre_archivo=str(nombre_archivo),
                ruta_archivo=str(ruta_archivo),
                archivo_hash=archivo_hash,
                registros_archivo=registros_archivo,
                registros_insertados=insertados,
            )

        return {
            "success": True,
            "status": "insertado",
            "tipo": tipo_normalizado,
            "conexion": conexion_normalizada,
            "tabla_destino": tabla_destino,
            "nombre_archivo": nombre_archivo,
            "ruta_archivo": ruta_archivo,
            "registros_archivo": registros_archivo,
            "registros_antes": registros_antes,
            "registros_despues": registros_despues,
            "insertados": insertados,
            "exito": exito,
        }

    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass

        return {
            "success": False,
            "status": "error",
            "error": f"Error en la inserción: {exc}",
        }

    finally:
        if conn is not None:
            conn.close()

