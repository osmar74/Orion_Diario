"""
Servicio SQL Server ASTER.

Responsabilidad:
- Construir cadena pyodbc para SQL Server ASTER.
- Elegir conexión local/remota.
- Probar conexión contra tabla destino.
- Obtener metadatos de columnas SQL Server.
"""

from __future__ import annotations

from typing import Any

import pyodbc


def valor_config_sql(config: Any, *nombres: str) -> str:
    """
    Lee un valor desde una configuración tipo dict de forma flexible.
    """
    if not isinstance(config, dict):
        return ""

    claves = {str(k).lower(): v for k, v in config.items()}

    for nombre in nombres:
        valor = claves.get(nombre.lower())

        if valor is not None:
            return str(valor).strip()

    return ""


def _sql_identificador(nombre: str) -> str:
    """
    Escapa identificadores SQL Server con corchetes.
    """
    return f"[{str(nombre).replace(']', ']]')}]"


def construir_cadena_pyodbc_aster(
    config: Any,
    database_default: str = "Aster_Api",
) -> str:
    """
    Convierte SQL_LOCAL / SQL_REMOTO a cadena pyodbc.

    Soporta:
    - string directo
    - dict con server/database/user/password/driver/port/auth
    """
    if isinstance(config, str):
        cadena = config.strip()

        if not cadena:
            raise ValueError("La cadena de conexión SQL Server está vacía.")

        return cadena

    if not isinstance(config, dict):
        raise TypeError(
            "La configuración SQL Server debe ser string o dict. "
            f"Tipo recibido: {type(config).__name__}"
        )

    driver = (
        valor_config_sql(config, "driver", "DRIVER")
        or "ODBC Driver 17 for SQL Server"
    )

    server = valor_config_sql(config, "server", "SERVER", "host", "HOST")
    port = valor_config_sql(config, "port", "PORT")

    database = (
        valor_config_sql(config, "database", "DATABASE", "db", "DB")
        or database_default
    )

    user = valor_config_sql(config, "user", "USER", "uid", "UID", "username")
    password = valor_config_sql(config, "password", "PASSWORD", "pwd", "PWD")

    trusted = valor_config_sql(
        config,
        "trusted_connection",
        "Trusted_Connection",
        "trusted",
    )

    auth = valor_config_sql(config, "auth", "authentication")

    if not server:
        raise ValueError("Falta SERVER en la configuración SQL Server.")

    if port and "," not in server and "\\" not in server:
        server = f"{server},{port}"

    partes = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        "TrustServerCertificate=yes",
    ]

    usa_windows = (
        trusted.lower() in {"yes", "true", "1", "si", "sí"}
        or auth.lower() in {"windows", "trusted", "integrated"}
    )

    if usa_windows:
        partes.append("Trusted_Connection=yes")
    else:
        if not user:
            raise ValueError("Falta USER/UID en la configuración SQL Server.")

        partes.append(f"UID={user}")
        partes.append(f"PWD={password}")

    return ";".join(partes)


def obtener_cadena_sqlserver_aster(
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    database_default: str = "Aster_Api",
) -> str:
    """
    Devuelve cadena pyodbc según conexión solicitada.

    local  = pruebas/desarrollo
    remoto = producción
    """
    conexion_normalizada = (conexion or "local").strip().lower()

    config = sql_remoto if conexion_normalizada == "remoto" else sql_local

    return construir_cadena_pyodbc_aster(
        config,
        database_default=database_default,
    )


def obtener_columnas_sqlserver_tabla(
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla: str,
) -> list[dict[str, Any]]:
    """
    Obtiene columnas de una tabla SQL Server.
    """
    cadena = obtener_cadena_sqlserver_aster(
        conexion=conexion,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        database_default=base,
    )

    sql = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            ORDINAL_POSITION,
            COLUMNPROPERTY(
                OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME),
                COLUMN_NAME,
                'IsIdentity'
            ) AS IS_IDENTITY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """

    conn = pyodbc.connect(cadena, timeout=10)
    conn.timeout = 120

    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {_sql_identificador(base)}")

        cursor.execute(
            sql,
            schema,
            tabla,
        )

        columnas: list[dict[str, Any]] = []

        for row in cursor.fetchall():
            columnas.append(
                {
                    "columna": str(row.COLUMN_NAME),
                    "tipo_sql": str(row.DATA_TYPE),
                    "nullable": str(row.IS_NULLABLE),
                    "longitud": row.CHARACTER_MAXIMUM_LENGTH,
                    "precision": row.NUMERIC_PRECISION,
                    "escala": row.NUMERIC_SCALE,
                    "orden": int(row.ORDINAL_POSITION),
                    "is_identity": int(row.IS_IDENTITY or 0),
                }
            )

        if not columnas:
            raise ValueError(
                "No se encontraron columnas para la tabla "
                f"{base}.{schema}.{tabla}."
            )

        return columnas

    finally:
        conn.close()


def probar_conexion_tabla_sqlserver_aster(
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla: str,
) -> dict[str, Any]:
    """
    Prueba conexión SQL Server y existencia de tabla destino.
    """
    conexion_normalizada = (conexion or "local").strip().lower()

    try:
        cadena = obtener_cadena_sqlserver_aster(
            conexion=conexion_normalizada,
            sql_local=sql_local,
            sql_remoto=sql_remoto,
            database_default=base,
        )

        conn = pyodbc.connect(cadena, timeout=10)
        conn.timeout = 120

        try:
            cursor = conn.cursor()
            cursor.execute(f"USE {_sql_identificador(base)}")
            cursor.execute("SELECT DB_NAME() AS base_actual")
            row_base = cursor.fetchone()
            base_actual = str(row_base.base_actual)

            cursor.execute(
                """
                SELECT COUNT(*) AS total_columnas
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ?
                  AND TABLE_NAME = ?
                """,
                schema,
                tabla,
            )

            row_cols = cursor.fetchone()
            total_columnas = int(row_cols.total_columnas or 0)

        finally:
            conn.close()

        if total_columnas <= 0:
            return {
                "success": False,
                "status": "tabla_no_encontrada",
                "conexion": conexion_normalizada,
                "base_actual": base_actual,
                "base": base,
                "schema": schema,
                "tabla": tabla,
                "total_columnas": total_columnas,
                "error": (
                    "Conexión correcta, pero no se encontró la tabla "
                    f"{base}.{schema}.{tabla}."
                ),
            }

        return {
            "success": True,
            "conexion": conexion_normalizada,
            "base_actual": base_actual,
            "base": base,
            "schema": schema,
            "tabla": tabla,
            "total_columnas": total_columnas,
        }

    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "conexion": conexion_normalizada,
            "base": base,
            "schema": schema,
            "tabla": tabla,
            "error": str(exc),
        }