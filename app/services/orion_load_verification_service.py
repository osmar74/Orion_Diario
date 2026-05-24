"""
Servicio de verificación de carga ORION.

Responsabilidad:
- Ubicar archivo consolidado ORION.
- Leer columnas del Excel consolidado.
- Leer columnas reales de SQL Server.
- Comparar coincidencias entre Excel y tabla destino.
- Devolver resultado estructurado al controlador.
"""

from __future__ import annotations

from typing import Any

import os
import pandas as pd
import pyodbc

from app.controllers.helpers import (
    construir_cadena_conexion,
    mapear_columnas_archivo,
    normalizar_texto,
)
from app.services.daily_paths import ruta_orion
from app.services.orion_file_lookup_service import buscar_archivo_consolidado_orion


TABLA_ORION_POR_TIPO = {
    "causales": "Causales",
    "lote": "Lote",
    "discador": "Discador",
}


def verificar_carga_orion(
    data_dir: str,
    fecha: str,
    tipo: str,
    conexion: str,
    cfg_sql: dict[str, Any],
) -> dict[str, Any]:
    """
    Verifica compatibilidad entre consolidado ORION y tabla SQL Server.
    """
    tipo_normalizado = str(tipo or "").strip().lower()
    conexion_normalizada = str(conexion or "local").strip().lower()

    tabla_destino = TABLA_ORION_POR_TIPO.get(tipo_normalizado)

    if not tabla_destino:
        return {
            "success": False,
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
            "error": f"No se encontró el archivo consolidado de {tipo_normalizado}.",
            "tabla_destino": tabla_destino,
            "ruta_archivo": ruta_archivo or "",
            "nombre_archivo": nombre_archivo or "",
        }

    try:
        df_archivo_str = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Error al leer el archivo: {exc}",
            "tabla_destino": tabla_destino,
            "ruta_archivo": ruta_archivo,
            "nombre_archivo": nombre_archivo,
        }

    columnas_archivo_originales = df_archivo_str.columns.tolist()

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

        cursor.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """,
            tabla_destino,
        )

        info_columnas = cursor.fetchall()

        if not info_columnas:
            return {
                "success": False,
                "error": f"No se encontró la tabla {tabla_destino} en la base de datos.",
                "tabla_destino": tabla_destino,
                "ruta_archivo": ruta_archivo,
                "nombre_archivo": nombre_archivo,
            }

        columnas_servidor = [row.COLUMN_NAME for row in info_columnas]
        tipos_servidor = {
            row.COLUMN_NAME: row.DATA_TYPE
            for row in info_columnas
        }
        columnas_servidor_norm = [
            normalizar_texto(col)
            for col in columnas_servidor
        ]

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
            ultimo_id = None

        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        row = cursor.fetchone()
        total_tabla = row[0] if row else 0

    except Exception as exc:
        return {
            "success": False,
            "error": f"Error de conexión: {exc}",
            "tabla_destino": tabla_destino,
            "ruta_archivo": ruta_archivo,
            "nombre_archivo": nombre_archivo,
        }

    finally:
        if conn is not None:
            conn.close()

    columnas_comparadas = []

    for i, col_srv in enumerate(columnas_servidor):
        norm_srv = columnas_servidor_norm[i]
        match_col = None

        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break

        columnas_comparadas.append(
            {
                "columna_sql": col_srv,
                "columna_archivo": match_col or "",
                "coincide": bool(match_col),
                "tipo_sql": tipos_servidor.get(col_srv, "?"),
            }
        )

    return {
        "success": True,
        "tipo": tipo_normalizado,
        "conexion": conexion_normalizada,
        "tabla_destino": tabla_destino,
        "ruta_archivo": ruta_archivo,
        "nombre_archivo": nombre_archivo,
        "registros_archivo": len(df_archivo_str),
        "ultimo_id": ultimo_id,
        "total_tabla": total_tabla,
        "total_columnas_sql": len(columnas_servidor),
        "columnas": columnas_comparadas,
    }