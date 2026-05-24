"""
Servicio de consulta consolidada ORION.

Responsabilidad:
- Leer app/sql/consolidado.sql.
- Validar fecha y mes.
- Ejecutar consulta SQL.
- Guardar resultado temporal temp_consolidado_*.pkl.
- Devolver valores únicos de "Descripcion Codigo De Gestion" con Fecha_Compromiso.
"""

from __future__ import annotations

import os
import pickle
import re
import uuid
from typing import Any

import pandas as pd
import pyodbc

from app.controllers.helpers import (
    construir_cadena_conexion,
    construir_sqlalchemy_engine,
)


def _obtener_sql_consolidado_path() -> str:
    """
    Devuelve ruta a app/sql/consolidado.sql.
    """
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "sql",
            "consolidado.sql",
        )
    )


def ejecutar_consulta_consolidado_orion(
    data_dir: str,
    fecha: str,
    meses: str,
    cfg_sql: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta la consulta consolidada ORION y guarda el DataFrame temporal.
    """
    fecha = str(fecha or "").strip()
    meses = str(meses or "").strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        return {
            "success": False,
            "status": "error",
            "error": "Formato de fecha inválido. Use YYYY-MM-DD.",
        }

    if not re.match(r"^\d{6}$", meses):
        return {
            "success": False,
            "status": "error",
            "error": "Formato de meses inválido. Use YYYYMM.",
        }

    sql_path = _obtener_sql_consolidado_path()

    try:
        with open(sql_path, "r", encoding="utf-8") as archivo:
            sql_template = archivo.read()
    except FileNotFoundError:
        return {
            "success": False,
            "status": "error",
            "error": "No se encuentra el archivo SQL de consolidación.",
        }

    sql_final = sql_template.format(fecha=fecha, meses=meses)

    try:
        conn_str = construir_cadena_conexion(cfg_sql)
        conn = pyodbc.connect(conn_str, timeout=60)
        conn.close()

        engine = construir_sqlalchemy_engine(cfg_sql)

        try:
            with engine.connect() as conn_sqlalchemy:
                df = pd.read_sql(sql_final, conn_sqlalchemy)
        finally:
            engine.dispose()

    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "error": f"Error en consulta SQL: {exc}",
        }

    if df.empty:
        return {
            "success": False,
            "status": "sin_resultados",
            "warning": "La consulta no devolvió resultados.",
        }

    columnas_requeridas = {
        "Fecha_Compromiso",
        "Descripcion Codigo De Gestion",
    }

    faltantes = sorted(columnas_requeridas - set(df.columns))

    if faltantes:
        return {
            "success": False,
            "status": "error",
            "error": "La consulta no devolvió columnas requeridas: "
            + ", ".join(faltantes),
        }

    df_con_fecha = df[
        df["Fecha_Compromiso"].notna()
        & (df["Fecha_Compromiso"].astype(str).str.strip() != "")
    ]

    valores_unicos = sorted(
        str(valor)
        for valor in df_con_fecha["Descripcion Codigo De Gestion"]
        .dropna()
        .unique()
    )

    os.makedirs(data_dir, exist_ok=True)

    temp_id = uuid.uuid4().hex[:10]
    temp_path = os.path.join(data_dir, f"temp_consolidado_{temp_id}.pkl")

    with open(temp_path, "wb") as archivo:
        pickle.dump(df, archivo)

    return {
        "success": True,
        "status": "ok",
        "temp_id": temp_id,
        "temp_path": temp_path,
        "total_registros": len(df),
        "total_con_fecha": len(df_con_fecha),
        "valores_unicos": valores_unicos,
    }