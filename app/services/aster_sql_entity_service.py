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
from app.services.aster_source_service import consultar_entidades_sql_aster_origen

from app.services.aster_file_service import normalizar_fecha_aster
from app.services.sql_loader import cargar_sql


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


def consultar_entidades_sql_aster(fecha_sql: str, conexion: str = "local") -> dict[str, Any]:
    """
    Consulta entidades ASTER desde el origen según conexión:
    - LOCAL: SQL Server gestioncomercial_dev.dbo.comentarios
    - REMOTO: MySQL gestioncomercial.comentarios
    """
    return consultar_entidades_sql_aster_origen(
        fecha_sql=fecha_sql,
        conexion=conexion,
    )
