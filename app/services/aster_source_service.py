"""
Servicio de origen ASTER LOCAL/REMOTO.

Regla:
- LOCAL  = SQL Server local gestioncomercial_dev.
- REMOTO = MySQL/MariaDB 10.24.90.101, se mantiene como producción.

Este servicio evita que el modo LOCAL siga leyendo desde MySQL remoto.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd


COLUMNAS_USUARIOS_FASE_I = [
        "usuario",
        "interno",
        "grupos",
        "permisosr2",
        "seleccion",
        "filtrar",
        "pausaragente",
        "agente",
        "modificarinterno",
        "modificaragente",
        "callback",
    ]


COLUMNAS_COMENTARIOS_FASE_I = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


def normalizar_conexion_aster_origen(conexion: str | None = None) -> str:
    valor = str(conexion or os.getenv("APP_CONNECTION_MODE", "local")).strip().lower()

    if valor not in {"local", "remoto"}:
        valor = "local"

    return valor


def origen_aster_engine(conexion: str | None = None) -> str:
    """
    Retorna:
    - sqlserver para LOCAL.
    - mysql para REMOTO.
    """
    modo = normalizar_conexion_aster_origen(conexion)

    if modo == "remoto":
        return "mysql"

    return "sqlserver"


def construir_cadena_sqlserver_origen_aster(database: str | None = None) -> str:
    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server").strip()
    server = os.getenv("SQLSERVER_SERVER", r"localhost\SQL2025DEV").strip()
    db = (database or os.getenv("SQLSERVER_DATABASE", "gestioncomercial_dev")).strip()
    trust = os.getenv("SQLSERVER_TRUST_CERTIFICATE", "yes").strip()
    auth = os.getenv("SQLSERVER_AUTH", "windows").strip().lower()

    partes = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={db}",
        "Encrypt=yes",
        f"TrustServerCertificate={trust}",
    ]

    if auth == "sql":
        user = os.getenv("SQLSERVER_USER", "").strip()
        password = os.getenv("SQLSERVER_PASSWORD", "").strip()

        if not user:
            raise ValueError("SQLSERVER_AUTH=sql pero falta SQLSERVER_USER en .env")

        partes.append(f"UID={user}")
        partes.append(f"PWD={password}")
    else:
        partes.append("Trusted_Connection=yes")

    return ";".join(partes) + ";"


def conectar_sqlserver_origen_aster(database: str | None = None):
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("No está instalado pyodbc. Ejecute: pip install pyodbc") from exc

    return pyodbc.connect(
        construir_cadena_sqlserver_origen_aster(database),
        timeout=30,
    )


def obtener_config_mysql_remoto_aster(database: str | None = None) -> dict[str, Any]:
    host = os.getenv("ASTER_DB_HOST", "").strip()
    user = os.getenv("ASTER_DB_USER", "").strip()
    password = os.getenv("ASTER_DB_PASSWORD", "").strip()
    port_raw = os.getenv("ASTER_DB_PORT", "3306").strip()
    db = (database or os.getenv("ASTER_DB_NAME", "gestioncomercial")).strip()

    if not host or not user:
        raise ValueError("Faltan variables remotas ASTER_DB_HOST / ASTER_DB_USER en .env")

    try:
        port = int(port_raw)
    except Exception:
        port = 3306

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": db,
        "port": port,
        "charset": "utf8mb4",
    }


def conectar_mysql_remoto_aster(database: str | None = None):
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("No está instalado PyMySQL. Ejecute: pip install PyMySQL") from exc

    config = obtener_config_mysql_remoto_aster(database)

    return pymysql.connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        port=config["port"],
        charset=config["charset"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def probar_origen_aster(conexion: str, db_usuarios: str = "usuarios", db_gestion: str = "gestioncomercial") -> dict[str, Any]:
    modo = normalizar_conexion_aster_origen(conexion)
    engine = origen_aster_engine(modo)

    if engine == "sqlserver":
        conn = conectar_sqlserver_origen_aster()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()
        finally:
            conn.close()

        return {
            "ok": True,
            "conexion": modo,
            "engine": "sqlserver",
            "servidor": os.getenv("SQLSERVER_SERVER", r"localhost\SQL2025DEV"),
            "database": os.getenv("SQLSERVER_DATABASE", "gestioncomercial_dev"),
        }

    conn_usuarios = conectar_mysql_remoto_aster(db_usuarios)
    try:
        with conn_usuarios.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()
    finally:
        conn_usuarios.close()

    conn_gestion = conectar_mysql_remoto_aster(db_gestion)
    try:
        with conn_gestion.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()
    finally:
        conn_gestion.close()

    return {
        "ok": True,
        "conexion": modo,
        "engine": "mysql",
        "servidor": os.getenv("ASTER_DB_HOST", ""),
        "database": db_gestion,
    }


def _sqlserver_identificador(nombre: str) -> str:
    return "[" + str(nombre).replace("]", "]]") + "]"


def _mysql_identificador(nombre: str) -> str:
    return "`" + str(nombre).replace("`", "``") + "`"


def _df_sqlserver(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    conn = conectar_sqlserver_origen_aster()
    try:
        return pd.read_sql(sql, conn, params=params or [])
    finally:
        conn.close()


def _fetchone_sqlserver(sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    conn = conectar_sqlserver_origen_aster()
    try:
        cursor = conn.cursor()
        row = cursor.execute(sql, *(params or [])).fetchone()

        if not row:
            return {}

        columns = [column[0] for column in cursor.description]

        return dict(zip(columns, row))
    finally:
        conn.close()


def _df_mysql(database: str, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    conn = conectar_mysql_remoto_aster(database)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or [])
            filas = cursor.fetchall()

        return pd.DataFrame(filas)
    finally:
        conn.close()


def _fetchone_mysql(database: str, sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    conn = conectar_mysql_remoto_aster(database)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or [])
            row = cursor.fetchone()

        return row or {}
    finally:
        conn.close()


def columnas_usuarios_origen_fase_i() -> list[str]:
    return list(COLUMNAS_USUARIOS_FASE_I)


def columnas_comentarios_origen_fase_i() -> list[str]:
    return list(COLUMNAS_COMENTARIOS_FASE_I)


def contar_usuarios_origen_fase_i(
    db_usuarios: str = "usuarios",
    conexion: str = "local",
) -> int:
    engine = origen_aster_engine(conexion)

    if engine == "sqlserver":
        sql = "SELECT COUNT(*) AS total FROM dbo.crm"
        row = _fetchone_sqlserver(sql)
        return int(row.get("total") or 0)

    row = _fetchone_mysql(db_usuarios, "SELECT COUNT(*) AS total FROM crm")
    return int(row.get("total") or 0)


def contar_comentarios_origen_fase_i(
    db_gestion: str = "gestioncomercial",
    fecha_yyyymmdd: str = "",
    entidades: list[str] | None = None,
    conexion: str = "local",
) -> int:
    entidades = entidades or []

    if not entidades:
        return 0

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    engine = origen_aster_engine(conexion)

    if engine == "sqlserver":
        placeholders = ", ".join(["?"] * len(entidades))
        sql = f"""
            SELECT COUNT(*) AS total
            FROM dbo.comentarios
            WHERE CAST(fecha AS date) = ?
              AND entidad IN ({placeholders})
              AND COALESCE(LTRIM(RTRIM(usuario)), '') <> 'SystemUser'
        """
        row = _fetchone_sqlserver(sql, [fecha_sql, *entidades])
        return int(row.get("total") or 0)

    placeholders = ", ".join(["%s"] * len(entidades))
    sql = f"""
        SELECT COUNT(*) AS total
        FROM comentarios
        WHERE DATE(fecha) = %s
          AND entidad IN ({placeholders})
          AND COALESCE(TRIM(usuario), '') <> 'SystemUser'
    """
    row = _fetchone_mysql(db_gestion, sql, [fecha_sql, *entidades])
    return int(row.get("total") or 0)


def leer_usuarios_origen_fase_i(
    db_usuarios: str = "usuarios",
    conexion: str = "local",
) -> pd.DataFrame:
    columnas = columnas_usuarios_origen_fase_i()
    engine = origen_aster_engine(conexion)

    if engine == "sqlserver":
        columnas_sql = ", ".join(
            f"{_sqlserver_identificador(col)} AS {_sqlserver_identificador(col)}"
            for col in columnas
        )
        sql = f"SELECT {columnas_sql} FROM dbo.crm"
        df = _df_sqlserver(sql)
        return df.reindex(columns=columnas)

    columnas_sql = ", ".join(
        f"{_mysql_identificador(col)} AS {_mysql_identificador(col)}"
        for col in columnas
    )
    sql = f"SELECT {columnas_sql} FROM crm"
    df = _df_mysql(db_usuarios, sql)
    return df.reindex(columns=columnas)


def leer_comentarios_origen_fase_i(
    db_gestion: str = "gestioncomercial",
    fecha_yyyymmdd: str = "",
    entidades: list[str] | None = None,
    conexion: str = "local",
) -> pd.DataFrame:
    columnas = columnas_comentarios_origen_fase_i()
    entidades = entidades or []

    if not entidades:
        return pd.DataFrame(columns=columnas)

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    engine = origen_aster_engine(conexion)

    if engine == "sqlserver":
        columnas_sql = ", ".join(
            f"{_sqlserver_identificador(col)} AS {_sqlserver_identificador(col)}"
            for col in columnas
        )
        placeholders = ", ".join(["?"] * len(entidades))
        sql = f"""
            SELECT {columnas_sql}
            FROM dbo.comentarios
            WHERE CAST(fecha AS date) = ?
              AND entidad IN ({placeholders})
              AND COALESCE(LTRIM(RTRIM(usuario)), '') <> 'SystemUser'
        """
        df = _df_sqlserver(sql, [fecha_sql, *entidades])
        return df.reindex(columns=columnas)

    columnas_sql = ", ".join(
        f"{_mysql_identificador(col)} AS {_mysql_identificador(col)}"
        for col in columnas
    )
    placeholders = ", ".join(["%s"] * len(entidades))
    sql = f"""
        SELECT {columnas_sql}
        FROM comentarios
        WHERE DATE(fecha) = %s
          AND entidad IN ({placeholders})
          AND COALESCE(TRIM(usuario), '') <> 'SystemUser'
    """
    df = _df_mysql(db_gestion, sql, [fecha_sql, *entidades])
    return df.reindex(columns=columnas)


def consultar_entidades_sql_aster_origen(
    fecha_sql: str,
    conexion: str = "local",
) -> dict[str, Any]:
    """
    Devuelve entidades desde origen ASTER.
    LOCAL: SQL Server gestioncomercial_dev.dbo.comentarios.
    REMOTO: MySQL gestioncomercial.comentarios.
    """
    engine = origen_aster_engine(conexion)

    if engine == "sqlserver":
        sql = """
            SELECT
                entidad,
                COUNT(DISTINCT data) AS numero
            FROM dbo.comentarios
            WHERE CAST(fecha AS date) = ?
            GROUP BY entidad
            ORDER BY numero DESC
        """
        df = _df_sqlserver(sql, [fecha_sql])
    else:
        db_gestion = os.getenv("ASTER_MYSQL_DB_GESTION", "gestioncomercial")
        sql = """
            SELECT
                entidad,
                COUNT(DISTINCT data) AS numero
            FROM comentarios
            WHERE DATE(fecha) = %s
            GROUP BY entidad
            ORDER BY numero DESC
        """
        df = _df_mysql(db_gestion, sql, [fecha_sql])

    resultados = []

    for _, row in df.iterrows():
        entidad = str(row.get("entidad") or "").strip()
        numero = int(row.get("numero") or 0)

        resultados.append(
            {
                "entidad": entidad,
                "numero": numero,
                "SSS": f"'{entidad}'",
            }
        )

    return {
        "success": True,
        "conexion": normalizar_conexion_aster_origen(conexion),
        "engine": engine,
        "fecha": fecha_sql,
        "fecha_sql": fecha_sql,
        "resultados": resultados,
        "total_entidades": len(resultados),
        "total_registros": sum(int(item["numero"]) for item in resultados),
    }

# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_BEGIN ===
# Fix local ASTER Fase I:
#
# En gestioncomercial_dev.dbo.usuarios no existe la columna id.
# La columna lógica para usuarios local es usuario.
#
# Este helper evita que la validación bloquee Fase I por faltar id
# cuando la conexión es local.
#
# Fecha generación: 2026-05-30 09:44:58.461653


def _aster_phase_i_es_local_required_id_fix(scope=None):
    scope = scope or {}

    conexion = (
        scope.get("conexion")
        or scope.get("modo")
        or scope.get("origen")
        or scope.get("tipo_conexion")
        or "local"
    )

    conexion = str(conexion or "local").strip().lower()

    return conexion in [
        "local",
        "sqlserver",
        "sql_server",
        "dev",
        "desarrollo",
    ]


def _aster_phase_i_filtrar_faltantes_usuarios_local(faltantes, scope=None):
    """
    En local, dbo.usuarios no tiene id.
    Por tanto, si la única columna faltante es id, no debe bloquear la Fase I.
    """
    if not faltantes:
        return faltantes

    faltantes_lista = list(faltantes)

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return faltantes_lista

    ignorables_local = {
        "id",
    }

    filtrados = [
        col for col in faltantes_lista
        if str(col).strip().lower() not in ignorables_local
    ]

    return filtrados


def _aster_phase_i_columnas_requeridas_usuarios_local(columnas=None, scope=None):
    """
    Normaliza columnas requeridas para usuarios local.
    Si aparece id, se elimina.
    Si no aparece usuario, se agrega como mínimo requerido.
    """
    columnas = list(columnas or [])

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return columnas

    columnas = [
        col for col in columnas
        if str(col).strip().lower() != "id"
    ]

    if "usuario" not in [str(c).strip().lower() for c in columnas]:
        columnas.insert(0, "usuario")

    return columnas


# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_END ===
