from __future__ import annotations

import os
from typing import Any

import pyodbc

from app.controllers.helpers import construir_cadena_conexion
from app.services.aster_phase_i_prepare_service import conectar_mysql_fase_i
from app.services.orion_aster_config_service import get_sql_config_legacy, normalizar_conexion


class IntegralV2ConnectionFactory:
    """
    Fábrica de conexiones para Integral v2.

    LOCAL:
    - Origen: SQL Server gestioncomercial_dev.
    - Destino: SQL Server Aster_Integral_Api.

    REMOTO:
    - Origen: MySQL usuarios / gestioncomercial usando variables ASTER_DB_*.
    - Destino: SQL Server Aster_Integral_Api.
    """

    def __init__(self, conexion: str):
        self.conexion = normalizar_conexion(conexion)

    def cfg_origen_sqlserver_local(self) -> dict[str, Any]:
        return get_sql_config_legacy("local", "gestioncomercial")

    def cfg_destino_sqlserver(self) -> dict[str, Any]:
        cfg = get_sql_config_legacy(self.conexion, "integral_api")

        if not cfg.get("database"):
            cfg = get_sql_config_legacy(self.conexion, "aster_api")

        cfg = dict(cfg)
        default_database = os.getenv(
            "INTEGRAL_SQL_LOCAL_DATABASE" if self.conexion == "local" else "INTEGRAL_SQL_REMOTO_DATABASE",
            "Aster_Integral_Api",
        )
        cfg["database"] = cfg.get("database") or default_database

        return cfg

    def abrir_origen_usuarios(self):
        if self.conexion == "remoto":
            return conectar_mysql_fase_i(os.getenv("INTEGRAL_MYSQL_DB_USUARIOS", "usuarios"))

        cfg = self.cfg_origen_sqlserver_local()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def abrir_origen_comentarios(self):
        if self.conexion == "remoto":
            return conectar_mysql_fase_i(os.getenv("INTEGRAL_MYSQL_DB_GESTION", "gestioncomercial"))

        cfg = self.cfg_origen_sqlserver_local()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def abrir_destino(self):
        cfg = self.cfg_destino_sqlserver()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def modo_origen(self) -> str:
        return "remoto_mysql" if self.conexion == "remoto" else "local_sqlserver"
