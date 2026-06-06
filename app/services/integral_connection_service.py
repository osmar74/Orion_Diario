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

# === Integral v2: contexto de pantalla ===

from datetime import datetime as _integral_v2_datetime
from time import perf_counter as _integral_v2_perf_counter


def _integral_v2_parse_fecha(value: str):
    raw = str(value or "").strip()

    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return _integral_v2_datetime.strptime(raw, fmt)
        except ValueError:
            pass

    raise ValueError(f"Fecha de proceso no válida: {value}")


def _integral_v2_fechas(value: str) -> dict[str, str]:
    dt = _integral_v2_parse_fecha(value)

    return {
        "fecha_proceso": dt.strftime("%Y%m%d"),
        "fecha_sql": dt.strftime("%Y-%m-%d"),
        "fecha_ddmmaaaa": dt.strftime("%d%m%Y"),
        "fecha_visual": dt.strftime("%d/%m/%Y"),
        "mes_gestion": dt.strftime("%Y%m"),
    }


def _integral_v2_sqlserver_cadena(cfg: dict[str, Any], database: str | None = None) -> str:
    db = database or cfg.get("database") or "Aster_Integral_Api"

    partes = [
        f"DRIVER={{{cfg.get('driver', 'ODBC Driver 18 for SQL Server')}}}",
        f"SERVER={cfg.get('server', '')}",
        f"DATABASE={db}",
        f"Encrypt={cfg.get('encrypt', 'yes')}",
        f"TrustServerCertificate={cfg.get('trust', 'yes')}",
    ]

    if cfg.get("username"):
        partes.append(f"UID={cfg.get('username', '')}")
        partes.append(f"PWD={cfg.get('password', '')}")
    else:
        partes.append("Trusted_Connection=yes")

    return ";".join(partes) + ";"


def _integral_v2_check_sqlserver(nombre: str, cfg: dict[str, Any], database: str) -> dict[str, Any]:
    inicio = _integral_v2_perf_counter()

    try:
        import pyodbc

        cadena = _integral_v2_sqlserver_cadena(cfg, database=database)

        with pyodbc.connect(cadena, timeout=5) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()

        return {
            "nombre": nombre,
            "ok": True,
            "estado": "Conectado",
            "mensaje": "Conexión correcta",
            "servidor": cfg.get("server", ""),
            "database": database,
            "ms": int((_integral_v2_perf_counter() - inicio) * 1000),
        }

    except Exception:
        return {
            "nombre": nombre,
            "ok": False,
            "estado": "Sin conexión",
            "mensaje": "Sin conexión",
            "servidor": cfg.get("server", ""),
            "database": database,
            "ms": int((_integral_v2_perf_counter() - inicio) * 1000),
        }


def _integral_v2_check_source(nombre: str, conexion: str) -> dict[str, Any]:
    inicio = _integral_v2_perf_counter()
    modo = IntegralConnectionFactory.normalizar_conexion(conexion)

    try:
        if modo == "remoto":
            conn = IntegralConnectionFactory.connect_source_comentarios(modo)
            database = "gestioncomercial"
            servidor = "MySQL remoto"
        else:
            conn = IntegralConnectionFactory.connect_source_comentarios(modo)
            database = IntegralConnectionFactory._env_first(
                "INTEGRAL_SQL_LOCAL_SOURCE_DATABASE",
                "SQLSERVER_DATABASE",
                default="gestioncomercial_dev",
            )
            servidor = IntegralConnectionFactory._sqlserver_destino_cfg(modo).get("server", "")

        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return {
            "nombre": nombre,
            "ok": True,
            "estado": "Conectado",
            "mensaje": "Conexión correcta",
            "servidor": servidor,
            "database": database,
            "ms": int((_integral_v2_perf_counter() - inicio) * 1000),
        }

    except Exception:
        if modo == "remoto":
            database = "gestioncomercial"
            servidor = "MySQL remoto"
        else:
            database = IntegralConnectionFactory._env_first(
                "INTEGRAL_SQL_LOCAL_SOURCE_DATABASE",
                "SQLSERVER_DATABASE",
                default="gestioncomercial_dev",
            )
            servidor = IntegralConnectionFactory._sqlserver_destino_cfg(modo).get("server", "")

        return {
            "nombre": nombre,
            "ok": False,
            "estado": "Sin conexión",
            "mensaje": "Sin conexión",
            "servidor": servidor,
            "database": database,
            "ms": int((_integral_v2_perf_counter() - inicio) * 1000),
        }


def construir_contexto_integral_v2(form) -> dict[str, Any]:
    """
    Contexto oficial de Integral Diario v2.

    Responsabilidad:
    - Normalizar fecha proceso.
    - Determinar conexión local/remota.
    - Determinar origen y destino.
    - Probar conexiones necesarias.
    - Entregar datos al resumen/sidebar de la vista.
    """

    fecha_raw = (
        form.get("fecha_proceso")
        or form.get("fecha")
        or "20260429"
    )

    conexion = IntegralConnectionFactory.normalizar_conexion(
        form.get("conexion") or form.get("conexion_global") or "local"
    )

    tipo_proceso = (
        form.get("tipo_proceso")
        or form.get("tipo")
        or "discador"
    ).lower()

    fechas = _integral_v2_fechas(fecha_raw)

    mes_gestion = (
        form.get("mes_gestion")
        or form.get("mes_gestion_texto")
        or fechas["mes_gestion"]
    )

    destino_cfg = IntegralConnectionFactory._sqlserver_destino_cfg(conexion)

    aster_db = destino_cfg.get("database") or "Aster_Integral_Api"

    vencorp_db = IntegralConnectionFactory._env_first(
        "INTEGRAL_SQL_LOCAL_VENCORP_DATABASE" if conexion == "local" else "INTEGRAL_SQL_REMOTO_VENCORP_DATABASE",
        "INTEGRAL_SQL_VENCORP_DATABASE",
        default="Vencorp_Integral",
    )

    origen_db = IntegralConnectionFactory._env_first(
        "INTEGRAL_SQL_LOCAL_SOURCE_DATABASE",
        "SQLSERVER_DATABASE",
        default="gestioncomercial_dev",
    ) if conexion == "local" else "gestioncomercial"

    origen_check = _integral_v2_check_source("Origen", conexion)
    aster_check = _integral_v2_check_sqlserver("Aster Integral", destino_cfg, aster_db)
    vencorp_check = _integral_v2_check_sqlserver("Vencorp Integral", destino_cfg, vencorp_db)

    contexto = {
        "conexion": conexion,
        "tipo_proceso": tipo_proceso,

        "fecha_proceso": fechas["fecha_proceso"],
        "fecha_sql": fechas["fecha_sql"],
        "fecha_ddmmaaaa": fechas["fecha_ddmmaaaa"],
        "fecha_visual": fechas["fecha_visual"],
        "mes_gestion": mes_gestion,

        "servidor": destino_cfg.get("server", ""),
        "origen": origen_db,
        "database_origen": origen_db,
        "aster_db": aster_db,
        "vencorp_db": vencorp_db,

        "tablas_origen": "dbo.comentarios / dbo.usuarios" if conexion == "local" else "comentarios / crm",
        "tabla_comentarios": "dbo.comentarios" if conexion == "local" else "comentarios",
        "tabla_usuarios": "dbo.usuarios" if conexion == "local" else "crm",

        "origen_check": origen_check,
        "aster_check": aster_check,
        "vencorp_check": vencorp_check,

        "conexion_origen_ok": origen_check["ok"],
        "conexion_aster_ok": aster_check["ok"],
        "conexion_vencorp_ok": vencorp_check["ok"],

        "estado_origen": origen_check["estado"],
        "estado_aster": aster_check["estado"],
        "estado_vencorp": vencorp_check["estado"],

        "checks": [
            origen_check,
            aster_check,
            vencorp_check,
        ],
    }

    return contexto
