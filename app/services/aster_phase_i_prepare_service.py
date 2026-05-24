"""
Servicio de preparación Fase I ASTER.

Responsabilidad:
- Probar conexiones MySQL usuarios / MySQL gestioncomercial / SQL Server.
- Leer entidades_aster_YYYYMMDD.xlsx.
- Contar usuarios MySQL.
- Contar comentarios MySQL filtrados por fecha y entidades.
- Comparar columnas origen MySQL vs destino SQL Server.
- Preparar Fase I sin ejecutar DELETE ni INSERT.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.services.aster_file_service import normalizar_fecha_aster
from app.services.aster_sqlserver_service import obtener_columnas_sqlserver_tabla
from app.services.daily_paths import ruta_aster_subcarpeta


def columnas_mysql_usuarios_fase_i() -> list[str]:
    return [
        "id",
        "usuario",
        "pass",
        "perfil",
        "nombre",
        "owned_by",
        "type",
        "web",
        "created_at",
        "updated_at",
    ]


def columnas_mysql_comentarios_fase_i() -> list[str]:
    return [
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


def obtener_config_mysql_fase_i(database: str) -> dict[str, Any]:
    """
    Obtiene configuración MySQL desde .env.

    Variables:
    - ASTER_DB_HOST
    - ASTER_DB_USER
    - ASTER_DB_PASSWORD
    - ASTER_DB_PORT
    """
    host = os.getenv("ASTER_DB_HOST", "").strip()
    user = os.getenv("ASTER_DB_USER", "").strip()
    password = os.getenv("ASTER_DB_PASSWORD", "").strip()
    port_raw = os.getenv("ASTER_DB_PORT", "3306").strip()

    if not host or not user:
        raise ValueError(
            "Faltan variables MySQL ASTER en .env: ASTER_DB_HOST / ASTER_DB_USER"
        )

    try:
        port = int(port_raw)
    except Exception:
        port = 3306

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": port,
        "charset": "utf8mb4",
    }


def conectar_mysql_fase_i(database: str):
    """
    Conecta a MySQL para lectura.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(
            "No está instalado PyMySQL. Ejecute: pip install PyMySQL"
        ) from exc

    config = obtener_config_mysql_fase_i(database)

    return pymysql.connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        port=config["port"],
        charset=config["charset"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def validar_sql_mysql_solo_select(sql: str) -> None:
    """
    Bloquea cualquier operación que no sea SELECT en MySQL.
    """
    sql_limpio = re.sub(r"\s+", " ", sql or "").strip().lower()

    if not sql_limpio.startswith("select "):
        raise ValueError("MySQL solo permite SELECT en Fase I.")

    prohibidas = [
        "delete ",
        "insert ",
        "update ",
        "drop ",
        "alter ",
        "truncate ",
        "create ",
        "replace ",
    ]

    for palabra in prohibidas:
        if palabra in sql_limpio:
            raise ValueError(
                f"Operación MySQL prohibida detectada: {palabra.strip().upper()}"
            )


def obtener_fecha_fase_i(
    fecha_raw: str = "",
    fecha_default: str = "",
) -> str:
    """
    Obtiene fecha Fase I en YYYYMMDD.
    """
    if fecha_raw:
        return normalizar_fecha_aster(fecha_raw)

    fecha_default_limpia = re.sub(r"[^0-9]", "", fecha_default or "")

    if len(fecha_default_limpia) >= 8:
        return fecha_default_limpia[:8]

    return datetime.now().strftime("%Y%m%d")


def ruta_entidades_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> str:
    """
    Ruta esperada de entidades_aster_YYYYMMDD.xlsx.
    """
    return os.path.join(
        ruta_aster_subcarpeta(data_dir, fecha_yyyymmdd, "Entidades"),
        f"entidades_aster_{fecha_yyyymmdd}.xlsx",
    )


def leer_entidades_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> tuple[list[str], str]:
    """
    Lee entidades filtradas finales desde entidades_aster_YYYYMMDD.xlsx.
    """
    ruta = ruta_entidades_fase_i(data_dir, fecha_yyyymmdd)

    if not os.path.isfile(ruta):
        raise FileNotFoundError(
            f"No existe el archivo de entidades ASTER: {ruta}"
        )

    df = pd.read_excel(ruta, dtype=str)

    if "Entidad" not in df.columns:
        raise ValueError("El archivo de entidades no tiene columna Entidad.")

    entidades = sorted(
        {
            str(valor).strip()
            for valor in df["Entidad"].dropna().tolist()
            if str(valor).strip()
        }
    )

    if not entidades:
        raise ValueError("El archivo de entidades no contiene entidades válidas.")

    return entidades, ruta


def comparar_columnas_fase_i(
    columnas_origen: list[str],
    columnas_destino: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compara columnas origen contra destino SQL Server.
    """
    destino_lower = {
        str(col["columna"]).lower(): col
        for col in columnas_destino
    }

    comparacion: list[dict[str, Any]] = []

    for col_origen in columnas_origen:
        col_sql = destino_lower.get(col_origen.lower())

        comparacion.append(
            {
                "columna_origen": col_origen,
                "columna_destino": str(col_sql["columna"]) if col_sql else "",
                "tipo_sql": str(col_sql["tipo_sql"]) if col_sql else "",
                "longitud": col_sql.get("longitud") if col_sql else "",
                "nullable": str(col_sql["nullable"]) if col_sql else "",
                "estado": "OK" if col_sql else "NO_EXISTE_EN_DESTINO",
            }
        )

    return comparacion


def contar_usuarios_mysql_fase_i(
    db_usuarios: str,
) -> int:
    """
    Cuenta usuarios desde MySQL usuarios.crm.
    """
    sql = "SELECT COUNT(*) AS total FROM crm"
    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_usuarios)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()

            return int(row.get("total") or 0)

    finally:
        conn.close()


def contar_comentarios_mysql_fase_i(
    db_gestion: str,
    fecha_yyyymmdd: str,
    entidades: list[str],
) -> int:
    """
    Cuenta comentarios MySQL filtrados por fecha y entidades.

    Excluye usuario SystemUser.
    """
    if not entidades:
        return 0

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    placeholders = ", ".join(["%s"] * len(entidades))

    sql = f"""
        SELECT COUNT(*) AS total
        FROM comentarios
        WHERE DATE(fecha) = %s
          AND entidad IN ({placeholders})
          AND COALESCE(TRIM(usuario), '') <> 'SystemUser'
    """

    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_gestion)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, [fecha_sql, *entidades])
            row = cursor.fetchone()

            return int(row.get("total") or 0)

    finally:
        conn.close()


def probar_conexiones_fase_i_aster(
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla_usuarios: str,
    tabla_comentarios: str,
    db_usuarios: str,
    db_gestion: str,
) -> dict[str, Any]:
    """
    Prueba conexiones de Fase I:
    - MySQL usuarios
    - MySQL gestioncomercial
    - SQL Server usuarios/comentarios
    """
    conexion_normalizada = str(conexion or "local").strip().lower()

    if conexion_normalizada not in {"local", "remoto"}:
        conexion_normalizada = "local"

    conn_usuarios = conectar_mysql_fase_i(db_usuarios)

    try:
        with conn_usuarios.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()
    finally:
        conn_usuarios.close()

    conn_gestion = conectar_mysql_fase_i(db_gestion)

    try:
        with conn_gestion.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()
    finally:
        conn_gestion.close()

    columnas_usuarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_usuarios,
    )

    columnas_comentarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_comentarios,
    )

    return {
        "success": True,
        "conexion": conexion_normalizada,
        "db_usuarios": db_usuarios,
        "db_gestion": db_gestion,
        "base": base,
        "total_columnas_usuarios": len(columnas_usuarios),
        "total_columnas_comentarios": len(columnas_comentarios),
    }


def preparar_fase_i_aster(
    data_dir: str,
    fecha_raw: str,
    fecha_default: str,
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla_usuarios: str,
    tabla_comentarios: str,
    db_usuarios: str,
    db_gestion: str,
) -> dict[str, Any]:
    """
    Prepara Fase I sin ejecutar DELETE ni INSERT.
    """
    conexion_normalizada = str(conexion or "local").strip().lower()

    if conexion_normalizada not in {"local", "remoto"}:
        conexion_normalizada = "local"

    fecha_yyyymmdd = obtener_fecha_fase_i(
        fecha_raw=fecha_raw,
        fecha_default=fecha_default,
    )

    entidades, ruta_entidades = leer_entidades_fase_i(
        data_dir=data_dir,
        fecha_yyyymmdd=fecha_yyyymmdd,
    )

    total_usuarios = contar_usuarios_mysql_fase_i(db_usuarios)

    total_comentarios = contar_comentarios_mysql_fase_i(
        db_gestion=db_gestion,
        fecha_yyyymmdd=fecha_yyyymmdd,
        entidades=entidades,
    )

    columnas_sql_usuarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_usuarios,
    )

    columnas_sql_comentarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_comentarios,
    )

    comparacion_usuarios = comparar_columnas_fase_i(
        columnas_mysql_usuarios_fase_i(),
        columnas_sql_usuarios,
    )

    comparacion_comentarios = comparar_columnas_fase_i(
        columnas_mysql_comentarios_fase_i(),
        columnas_sql_comentarios,
    )

    return {
        "success": True,
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "conexion": conexion_normalizada,
        "entidades": entidades,
        "ruta_entidades": ruta_entidades,
        "total_entidades": len(entidades),
        "total_usuarios": total_usuarios,
        "total_comentarios": total_comentarios,
        "comparacion_usuarios": comparacion_usuarios,
        "comparacion_comentarios": comparacion_comentarios,
    }
