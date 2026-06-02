from __future__ import annotations

import os
from typing import Any


class IntegralConnectionFactory:
    """
    Centraliza conexiones del módulo Integral.

    Origen:
    - local  -> SQL Server local, por defecto gestioncomercial_dev.
    - remoto -> MySQL remoto, usando las mismas funciones/configuración de ASTER.

    Destino:
    - local/remoto -> SQL Server, por defecto base Aster_Integral_Api.
    """

    @staticmethod
    def normalizar_conexion(conexion: str | None) -> str:
        valor = str(conexion or "local").strip().lower()
        return valor if valor in {"local", "remoto"} else "local"

    @classmethod
    def source_engine(cls, conexion: str | None) -> str:
        return "mysql" if cls.normalizar_conexion(conexion) == "remoto" else "sqlserver"

    @staticmethod
    def _env_first(*names: str, default: str = "") -> str:
        for name in names:
            value = os.getenv(name)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
        return default

    @classmethod
    def connect_source_usuarios(cls, conexion: str | None):
        modo = cls.normalizar_conexion(conexion)

        if modo == "remoto":
            from app.services.aster_source_service import conectar_mysql_remoto_aster
            return conectar_mysql_remoto_aster("usuarios")

        from app.services.aster_source_service import conectar_sqlserver_origen_aster
        database = cls._env_first(
            "INTEGRAL_SQL_LOCAL_SOURCE_DATABASE",
            "SQLSERVER_DATABASE",
            default="gestioncomercial_dev",
        )
        return conectar_sqlserver_origen_aster(database)

    @classmethod
    def connect_source_comentarios(cls, conexion: str | None):
        modo = cls.normalizar_conexion(conexion)

        if modo == "remoto":
            from app.services.aster_source_service import conectar_mysql_remoto_aster
            return conectar_mysql_remoto_aster("gestioncomercial")

        from app.services.aster_source_service import conectar_sqlserver_origen_aster
        database = cls._env_first(
            "INTEGRAL_SQL_LOCAL_SOURCE_DATABASE",
            "SQLSERVER_DATABASE",
            default="gestioncomercial_dev",
        )
        return conectar_sqlserver_origen_aster(database)

    @classmethod
    def _sqlserver_destino_cfg(cls, conexion: str | None) -> dict[str, Any]:
        modo = cls.normalizar_conexion(conexion)

        if modo == "remoto":
            return {
                "driver": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_DRIVER",
                    "ORION_SQL_REMOTO_DRIVER",
                    default="ODBC Driver 18 for SQL Server",
                ),
                "server": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_SERVER",
                    "ORION_SQL_REMOTO_SERVER",
                    default="VC-EIDER",
                ),
                "database": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_DATABASE",
                    default="Aster_Integral_Api",
                ),
                "username": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_USERNAME",
                    "ORION_SQL_REMOTO_USERNAME",
                    default="Admin1",
                ),
                "password": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_PASSWORD",
                    "ORION_SQL_REMOTO_PASSWORD",
                    default="",
                ),
                "encrypt": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_ENCRYPT",
                    "ORION_SQL_REMOTO_ENCRYPT",
                    default="yes",
                ),
                "trust": cls._env_first(
                    "INTEGRAL_SQL_REMOTO_TRUST_SERVER_CERTIFICATE",
                    "ORION_SQL_REMOTO_TRUST_SERVER_CERTIFICATE",
                    default="yes",
                ),
            }

        return {
            "driver": cls._env_first(
                "INTEGRAL_SQL_LOCAL_DRIVER",
                "ORION_SQL_LOCAL_DRIVER",
                "SQLSERVER_DRIVER",
                default="ODBC Driver 18 for SQL Server",
            ),
            "server": cls._env_first(
                "INTEGRAL_SQL_LOCAL_SERVER",
                "ORION_SQL_LOCAL_SERVER",
                "SQLSERVER_SERVER",
                default=r"localhost\SQL2025DEV",
            ),
            "database": cls._env_first(
                "INTEGRAL_SQL_LOCAL_DATABASE",
                default="Aster_Integral_Api",
            ),
            "username": cls._env_first(
                "INTEGRAL_SQL_LOCAL_USERNAME",
                "ORION_SQL_LOCAL_USERNAME",
                "SQLSERVER_USER",
                default="Admin1",
            ),
            "password": cls._env_first(
                "INTEGRAL_SQL_LOCAL_PASSWORD",
                "ORION_SQL_LOCAL_PASSWORD",
                "SQLSERVER_PASSWORD",
                default="",
            ),
            "encrypt": cls._env_first(
                "INTEGRAL_SQL_LOCAL_ENCRYPT",
                "ORION_SQL_LOCAL_ENCRYPT",
                default="yes",
            ),
            "trust": cls._env_first(
                "INTEGRAL_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
                "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
                "SQLSERVER_TRUST_CERTIFICATE",
                default="yes",
            ),
        }

    @classmethod
    def connect_destino(cls, conexion: str | None):
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("No está instalado pyodbc. Ejecute: pip install pyodbc") from exc

        cfg = cls._sqlserver_destino_cfg(conexion)

        partes = [
            f"DRIVER={{{cfg['driver']}}}",
            f"SERVER={cfg['server']}",
            f"DATABASE={cfg['database']}",
            f"Encrypt={cfg['encrypt']}",
            f"TrustServerCertificate={cfg['trust']}",
        ]

        if cfg.get("username"):
            partes.append(f"UID={cfg['username']}")
            partes.append(f"PWD={cfg.get('password', '')}")
        else:
            partes.append("Trusted_Connection=yes")

        cadena = ";".join(partes) + ";"
        return pyodbc.connect(cadena, timeout=10)

    @classmethod
    def describir(cls, conexion: str | None) -> dict[str, str]:
        modo = cls.normalizar_conexion(conexion)
        destino = cls._sqlserver_destino_cfg(modo)
        return {
            "conexion": modo,
            "origen_engine": cls.source_engine(modo),
            "destino_engine": "sqlserver",
            "destino_servidor": destino.get("server", ""),
            "destino_database": destino.get("database", ""),
        }
