"""
Servicio de consulta SQL/MySQL de entidades ASTER.

Responsabilidad:
- Normalizar fecha ASTER a YYYY-MM-DD.
- Obtener configuración MySQL desde variables de entorno.
- Consultar entidades desde gestioncomercial.comentarios.
- Devolver resultado estructurado al controlador.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.services.aster_file_service import normalizar_fecha_aster


def normalizar_fecha_sql_aster(fecha_raw: str) -> str:
    """
    Convierte una fecha recibida en distintos formatos a YYYY-MM-DD.

    Acepta:
    - 20260513
    - 2026-05-13
    - 202605_13
    """
    fecha_yyyymmdd = normalizar_fecha_aster(fecha_raw)
    fecha_dt = datetime.strptime(fecha_yyyymmdd, "%Y%m%d")

    return fecha_dt.strftime("%Y-%m-%d")


def obtener_config_mysql_aster() -> dict[str, Any]:
    """
    Obtiene configuración MySQL ASTER desde variables de entorno.

    Variables esperadas:
    - ASTER_DB_HOST
    - ASTER_DB_USER
    - ASTER_DB_PASSWORD
    - ASTER_DB_NAME
    - ASTER_DB_PORT
    """
    port_raw = os.getenv("ASTER_DB_PORT", "3306").strip()

    try:
        port = int(port_raw)
    except Exception:
        port = 3306

    config: dict[str, Any] = {
        "host": os.getenv("ASTER_DB_HOST", "").strip(),
        "user": os.getenv("ASTER_DB_USER", "").strip(),
        "password": os.getenv("ASTER_DB_PASSWORD", "").strip(),
        "database": os.getenv("ASTER_DB_NAME", "gestioncomercial").strip(),
        "port": port,
        "charset": "utf8mb4",
    }

    faltantes = []

    if not config["host"]:
        faltantes.append("ASTER_DB_HOST")

    if not config["user"]:
        faltantes.append("ASTER_DB_USER")

    if not config["password"]:
        faltantes.append("ASTER_DB_PASSWORD")

    if not config["database"]:
        faltantes.append("ASTER_DB_NAME")

    if faltantes:
        raise ValueError(
            "Faltan variables de entorno ASTER MySQL: "
            + ", ".join(faltantes)
        )

    return config


def consultar_entidades_sql_aster(
    fecha_raw: str,
) -> dict[str, Any]:
    """
    Ejecuta consulta MySQL ASTER para obtener entidades del día.

    Retorna:
    - fecha_sql
    - resultados
    - total_entidades
    - total_registros
    """
    try:
        import pymysql
    except ImportError as exc:
        return {
            "success": False,
            "error": "No está instalado PyMySQL. Ejecute: pip install PyMySQL",
            "exception": str(exc),
        }

    try:
        fecha_sql = normalizar_fecha_sql_aster(fecha_raw)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Fecha ASTER inválida: {exc}",
        }

    try:
        config = obtener_config_mysql_aster()

        sql = """
            SELECT
                entidad,
                COUNT(DISTINCT data) AS numero
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
            port=config["port"],
            charset=config["charset"],
            cursorclass=pymysql.cursors.DictCursor,
        )

        try:
            with conexion.cursor() as cursor:
                cursor.execute(sql, (fecha_sql,))
                filas = cursor.fetchall()
        finally:
            conexion.close()

    except Exception as exc:
        return {
            "success": False,
            "fecha_sql": fecha_sql,
            "error": f"Error consultando entidades ASTER en MySQL: {exc}",
        }

    resultados: list[dict[str, Any]] = []

    for fila in filas:
        entidad = str(fila.get("entidad") or "").strip()
        numero = int(fila.get("numero") or 0)

        if not entidad:
            continue

        resultados.append(
            {
                "entidad": entidad,
                "numero": numero,
                "SSS": f"'{entidad}'",
            }
        )

    total_registros = sum(int(fila["numero"]) for fila in resultados)

    return {
        "success": True,
        "fecha_sql": fecha_sql,
        "resultados": resultados,
        "total_entidades": len(resultados),
        "total_registros": total_registros,
    }
    
