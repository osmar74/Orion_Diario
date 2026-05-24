"""
Servicio de pruebas de conexión ORION.

Responsabilidad:
- Probar conexión SQL Server.
- Probar lectura básica de tabla.
- Devolver resultados estructurados al controlador.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pyodbc

from app.controllers.helpers import (
    construir_cadena_conexion,
    construir_sqlalchemy_engine,
)
from app.services.sql_loader import cargar_sql


def _sql_identificador_orion(nombre: str) -> str:
    """
    Escapa identificadores SQL Server con corchetes.
    """
    return f"[{str(nombre).replace(']', ']]')}]"


def _tabla_sql_orion(tabla: str) -> str:
    """
    Valida y devuelve tabla ORION segura.
    """
    tablas_permitidas = {"Causales", "Lote", "Discador"}

    if tabla not in tablas_permitidas:
        raise ValueError(f"Tabla ORION no permitida: {tabla}")

    return _sql_identificador_orion(tabla)


def _limite_select_orion(limite: int) -> int:
    """
    Normaliza límite para SELECT TOP.
    """
    try:
        valor = int(limite)
    except Exception:
        valor = 5

    if valor <= 0:
        valor = 5

    if valor > 100:
        valor = 100

    return valor


def probar_conexion_sql_server(
    cfg_sql: dict[str, Any],
    timeout: int = 5,
) -> dict[str, Any]:
    """
    Prueba conexión SQL Server.
    """
    servidor = str(cfg_sql.get("server", "")).strip()
    basedatos = str(cfg_sql.get("database", "")).strip()

    if not servidor or not basedatos:
        return {
            "success": False,
            "error": "Faltan datos obligatorios.",
        }

    try:
        conn_str = construir_cadena_conexion(cfg_sql)
        conn = pyodbc.connect(conn_str, timeout=timeout)
        conn.close()

        return {
            "success": True,
            "servidor": servidor,
            "basedatos": basedatos,
            "mensaje": f"Conexión exitosa a {servidor}/{basedatos}",
        }

    except Exception as exc:
        return {
            "success": False,
            "servidor": servidor,
            "basedatos": basedatos,
            "error": f"Error de conexión: {exc}",
        }


def probar_lectura_tabla_sql_server(
    cfg_sql: dict[str, Any],
    tabla: str = "Causales",
    limite: int = 5,
) -> dict[str, Any]:
    """
    Prueba lectura básica sobre una tabla SQL Server.
    """
    tablas_permitidas = {"Causales", "Lote", "Discador"}

    if tabla not in tablas_permitidas:
        return {
            "success": False,
            "error": f"Tabla no permitida para prueba de lectura: {tabla}",
        }

    try:
        limite_sql = _limite_select_orion(limite)
        tabla_sql = _tabla_sql_orion(tabla)

        query = cargar_sql("orion/select_top_table.sql").format(
            limite=limite_sql,
            tabla=tabla_sql,
        )

        engine = construir_sqlalchemy_engine(cfg_sql)

        try:
            with engine.connect() as conn_sqlalchemy:
                df = pd.read_sql(query, conn_sqlalchemy)
        finally:
            engine.dispose()

        if df.empty:
            return {
                "success": False,
                "status": "sin_registros",
                "warning": f"La tabla {tabla} existe pero no contiene registros.",
                "tabla": tabla,
                "registros": 0,
                "columnas": [],
                "filas": [],
            }

        df_preview = df.where(pd.notna(df), "")

        return {
            "success": True,
            "tabla": tabla,
            "registros": len(df_preview),
            "columnas": [str(col) for col in df_preview.columns.tolist()],
            "filas": df_preview.astype(str).to_dict(orient="records"),
        }

    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "tabla": tabla,
            "error": f"Error al leer {tabla}: {exc}",
        }

