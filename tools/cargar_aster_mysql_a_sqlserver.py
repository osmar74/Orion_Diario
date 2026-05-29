"""
cargar_aster_mysql_a_sqlserver.py

Carga datos desde el MySQL/MariaDB remoto de ASTER hacia SQL Server local de desarrollo.

Origen MySQL:
- Variables ASTER_DB_HOST, ASTER_DB_USER, ASTER_DB_PASSWORD, ASTER_DB_NAME

Destino SQL Server:
- Base local gestioncomercial_dev
- Tablas dbo.usuarios y dbo.comentarios

Requisitos:
    pip install pymysql pyodbc python-dotenv

Uso recomendado:
    1) Crear las tablas en SQL Server con gestioncomercial_sqlserver.sql
    2) Crear archivo .env en la raíz del proyecto
    3) Ejecutar:
       python tools\cargar_aster_mysql_a_sqlserver.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

import pyodbc
import pymysql
from dotenv import load_dotenv


ZERO_DATE_STRINGS = {
    "0000-00-00",
    "0000-00-00 00:00:00",
    "0000-00-00 00:00:00.000000",
}

FALLBACK_DATETIME = datetime(1900, 1, 1, 0, 0, 0)


def getenv_required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Falta configurar {name} en el archivo .env")
    return value.strip()


def getenv_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def getenv_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí"}


def normalize_text(value: Any) -> str:
    """Convierte NULL de MySQL a cadena vacía para columnas NOT NULL de SQL Server."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def normalize_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def normalize_datetime(value: Any) -> datetime:
    """
    SQL Server no acepta fechas cero de MySQL.
    Cualquier fecha inválida o NULL se transforma a 1900-01-01.
    """
    if value is None:
        return FALLBACK_DATETIME

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    if isinstance(value, str):
        clean = value.strip()
        if clean in ZERO_DATE_STRINGS or clean.startswith("0000-00-00"):
            return FALLBACK_DATETIME

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                pass

    return FALLBACK_DATETIME


def mysql_connect():
    return pymysql.connect(
        host=getenv_required("ASTER_DB_HOST"),
        port=getenv_int("ASTER_DB_PORT", 3306),
        user=getenv_required("ASTER_DB_USER"),
        password=getenv_required("ASTER_DB_PASSWORD"),
        database=getenv_required("ASTER_DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=30,
        read_timeout=180,
        write_timeout=180,
    )


def sqlserver_connect():
    server = getenv_required("SQLSERVER_SERVER")
    database = getenv_required("SQLSERVER_DATABASE")
    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server").strip()
    trust_cert = getenv_bool("SQLSERVER_TRUST_CERTIFICATE", True)

    auth_mode = os.getenv("SQLSERVER_AUTH", "windows").strip().lower()

    if auth_mode == "sql":
        user = getenv_required("SQLSERVER_USER")
        password = getenv_required("SQLSERVER_PASSWORD")
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate={'yes' if trust_cert else 'no'};"
        )
    else:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            f"TrustServerCertificate={'yes' if trust_cert else 'no'};"
        )

    return pyodbc.connect(conn_str, autocommit=False)


def chunked(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def fetch_mysql_rows(
    mysql_conn,
    table_name: str,
    order_by: str | None = None,
    limit_rows: int = 0,
) -> list[dict[str, Any]]:
    sql = f"SELECT * FROM `{table_name}`"

    if order_by:
        sql += f" ORDER BY `{order_by}`"

    if limit_rows > 0:
        sql += f" LIMIT {int(limit_rows)}"

    with mysql_conn.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


def limpiar_tablas_destino(sql_conn) -> None:
    print("Limpiando tablas destino en SQL Server...")

    cursor = sql_conn.cursor()

    # Primero comentarios, luego usuarios.
    cursor.execute("DELETE FROM dbo.comentarios;")
    cursor.execute("DBCC CHECKIDENT ('dbo.comentarios', RESEED, 0);")

    cursor.execute("DELETE FROM dbo.usuarios;")

    sql_conn.commit()


def insertar_usuarios(sql_conn, rows: list[dict[str, Any]], batch_size: int) -> int:
    if not rows:
        print("No hay usuarios para insertar.")
        return 0

    sql_insert = """
        INSERT INTO dbo.usuarios (
            usuario,
            interno,
            grupos,
            permisosr2,
            seleccion,
            filtrar,
            pausaragente,
            agente,
            modificarinterno,
            modificaragente,
            callback
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    cursor = sql_conn.cursor()
    cursor.fast_executemany = True

    total = 0

    for batch in chunked(rows, batch_size):
        params = [
            (
                normalize_text(r.get("usuario")),
                normalize_text(r.get("interno")),
                normalize_text(r.get("grupos")),
                normalize_text(r.get("permisosr2")),
                normalize_text(r.get("seleccion")),
                normalize_text(r.get("filtrar"))[:5],
                normalize_text(r.get("pausaragente")),
                normalize_text(r.get("agente")),
                normalize_text(r.get("modificarinterno"))[:1],
                normalize_text(r.get("modificaragente"))[:1],
                normalize_text(r.get("callback"))[:1],
            )
            for r in batch
        ]

        cursor.executemany(sql_insert, params)
        sql_conn.commit()

        total += len(batch)
        print(f"  usuarios insertados: {total}/{len(rows)}")

    return total


def insertar_comentarios(sql_conn, rows: list[dict[str, Any]], batch_size: int) -> int:
    if not rows:
        print("No hay comentarios para insertar.")
        return 0

    sql_insert = """
        INSERT INTO dbo.comentarios (
            id,
            [data],
            fecha,
            comentario,
            resultado1,
            resultado2,
            entidad,
            usuario,
            fechaagenda,
            unico,
            fechainicio,
            telefono,
            uniqueid,
            linkedid,
            datafijos,
            datapers
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    cursor = sql_conn.cursor()
    cursor.fast_executemany = True

    total = 0

    cursor.execute("SET IDENTITY_INSERT dbo.comentarios ON;")
    sql_conn.commit()

    try:
        for batch in chunked(rows, batch_size):
            params = [
                (
                    normalize_int(r.get("id")),
                    normalize_text(r.get("data")),
                    normalize_datetime(r.get("fecha")),
                    normalize_text(r.get("comentario")),
                    normalize_text(r.get("resultado1")),
                    normalize_text(r.get("resultado2")),
                    normalize_text(r.get("entidad")),
                    normalize_text(r.get("usuario")),
                    normalize_datetime(r.get("fechaagenda")),
                    normalize_text(r.get("unico")),
                    normalize_datetime(r.get("fechainicio")),
                    normalize_text(r.get("telefono")),
                    normalize_text(r.get("uniqueid")),
                    normalize_text(r.get("linkedid")),
                    normalize_text(r.get("datafijos")),
                    normalize_text(r.get("datapers")),
                )
                for r in batch
            ]

            cursor.executemany(sql_insert, params)
            sql_conn.commit()

            total += len(batch)
            print(f"  comentarios insertados: {total}/{len(rows)}")

    finally:
        cursor.execute("SET IDENTITY_INSERT dbo.comentarios OFF;")
        sql_conn.commit()

    return total


def verificar_conteos(mysql_conn, sql_conn, limit_rows: int) -> None:
    print("\nVerificando conteos...")

    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM `usuarios`;")
        mysql_usuarios_total = int(cursor.fetchone()["total"])

        cursor.execute("SELECT COUNT(*) AS total FROM `comentarios`;")
        mysql_comentarios_total = int(cursor.fetchone()["total"])

    cursor_sql = sql_conn.cursor()
    sql_usuarios = int(cursor_sql.execute("SELECT COUNT(*) FROM dbo.usuarios;").fetchone()[0])
    sql_comentarios = int(cursor_sql.execute("SELECT COUNT(*) FROM dbo.comentarios;").fetchone()[0])

    if limit_rows > 0:
        mysql_usuarios_esperado = min(mysql_usuarios_total, limit_rows)
        mysql_comentarios_esperado = min(mysql_comentarios_total, limit_rows)
    else:
        mysql_usuarios_esperado = mysql_usuarios_total
        mysql_comentarios_esperado = mysql_comentarios_total

    print(f"MySQL usuarios total:           {mysql_usuarios_total}")
    print(f"SQL Server usuarios insertados: {sql_usuarios}")
    print(f"Esperado usuarios:              {mysql_usuarios_esperado}")
    print("")
    print(f"MySQL comentarios total:           {mysql_comentarios_total}")
    print(f"SQL Server comentarios insertados: {sql_comentarios}")
    print(f"Esperado comentarios:              {mysql_comentarios_esperado}")

    if sql_usuarios == mysql_usuarios_esperado and sql_comentarios == mysql_comentarios_esperado:
        print("\nOK: Los conteos coinciden con lo esperado.")
    else:
        print("\nATENCIÓN: Los conteos no coinciden. Revisa errores o filtros.")


def probar_conexiones(mysql_conn, sql_conn) -> None:
    print("Probando conexión MySQL...")
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT DATABASE() AS db_actual;")
        row = cursor.fetchone()
        print(f"  MySQL conectado a base: {row['db_actual']}")

    print("Probando conexión SQL Server...")
    cursor_sql = sql_conn.cursor()
    row = cursor_sql.execute("SELECT DB_NAME();").fetchone()
    print(f"  SQL Server conectado a base: {row[0]}")


def main() -> int:
    load_dotenv()

    batch_size = getenv_int("BATCH_SIZE", 1000)
    limit_rows = getenv_int("LIMIT_ROWS", 10)
    truncate_destination = getenv_bool("TRUNCATE_DESTINATION", True)

    print("Conectando a MySQL/MariaDB remoto ASTER...")
    mysql_conn = mysql_connect()

    print("Conectando a SQL Server local...")
    sql_conn = sqlserver_connect()

    try:
        probar_conexiones(mysql_conn, sql_conn)

        if truncate_destination:
            limpiar_tablas_destino(sql_conn)
        else:
            print("TRUNCATE_DESTINATION=false. No se limpiarán tablas destino.")

        print("\nLeyendo usuarios desde MySQL...")
        usuarios = fetch_mysql_rows(
            mysql_conn,
            table_name="usuarios",
            order_by="usuario",
            limit_rows=limit_rows,
        )
        print(f"Usuarios leídos: {len(usuarios)}")

        print("Insertando usuarios en SQL Server...")
        insertar_usuarios(sql_conn, usuarios, batch_size)

        print("\nLeyendo comentarios desde MySQL...")
        comentarios = fetch_mysql_rows(
            mysql_conn,
            table_name="comentarios",
            order_by="id",
            limit_rows=limit_rows,
        )
        print(f"Comentarios leídos: {len(comentarios)}")

        print("Insertando comentarios en SQL Server...")
        insertar_comentarios(sql_conn, comentarios, batch_size)

        verificar_conteos(mysql_conn, sql_conn, limit_rows)

        print("\nCarga terminada correctamente.")
        return 0

    except Exception as exc:
        sql_conn.rollback()
        print("\nERROR durante la carga:")
        print(type(exc).__name__)
        print(str(exc))
        return 1

    finally:
        mysql_conn.close()
        sql_conn.close()


if __name__ == "__main__":
    sys.exit(main())
