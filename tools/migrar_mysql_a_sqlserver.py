"""
migrar_mysql_a_sqlserver.py

Copia datos desde MySQL/MariaDB remoto hacia SQL Server local de desarrollo.

Tablas:
- comentarios
- usuarios

Requisitos:
    pip install pymysql pyodbc python-dotenv

Antes de ejecutar:
1. Crear la base y tablas en SQL Server con gestioncomercial_sqlserver.sql.
2. Crear un archivo .env basado en .env.example.
3. Instalar Microsoft ODBC Driver 18 for SQL Server si no está instalado.

Ejecución:
    python migrar_mysql_a_sqlserver.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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


def normalize_datetime(value: Any) -> datetime:
    """Convierte fechas cero/NULL de MySQL a 1900-01-01 para SQL Server."""
    if value is None:
        return FALLBACK_DATETIME

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        clean = value.strip()
        if clean in ZERO_DATE_STRINGS or clean.startswith("0000-00-00"):
            return FALLBACK_DATETIME

        # Intentos comunes de parseo
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                parsed = datetime.strptime(clean, fmt)
                if parsed.year < 1:
                    return FALLBACK_DATETIME
                return parsed
            except ValueError:
                pass

    # Último intento: que pyodbc reciba valor o usar fallback.
    return FALLBACK_DATETIME


def normalize_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def mysql_connect():
    return pymysql.connect(
        host=getenv_required("10.24.90.101"),
        port=getenv_int("MYSQL_PORT", 3306),
        user=getenv_required("root"),
        password=getenv_required("1234"),
        database=getenv_required("gestioncomercial"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=30,
        read_timeout=120,
        write_timeout=120,
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

    conn = pyodbc.connect(conn_str, autocommit=False)
    return conn


def chunked(iterable: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def fetch_mysql_rows(mysql_conn, table: str, order_by: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    sql = f"SELECT * FROM `{table}`"
    if order_by:
        sql += f" ORDER BY `{order_by}`"
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"

    with mysql_conn.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


def prepare_sqlserver(sql_conn, truncate: bool) -> None:
    if not truncate:
        return

    print("Limpiando tablas destino en SQL Server...")
    cur = sql_conn.cursor()
    cur.execute("DELETE FROM dbo.comentarios;")
    cur.execute("DBCC CHECKIDENT ('dbo.comentarios', RESEED, 0);")
    cur.execute("DELETE FROM dbo.usuarios;")
    sql_conn.commit()


def insert_usuarios(sql_conn, rows: list[dict[str, Any]], batch_size: int) -> int:
    if not rows:
        return 0

    insert_sql = """
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

    cur = sql_conn.cursor()
    cur.fast_executemany = True

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
        cur.executemany(insert_sql, params)
        sql_conn.commit()
        total += len(batch)
        print(f"  usuarios: {total}/{len(rows)}")

    return total


def insert_comentarios(sql_conn, rows: list[dict[str, Any]], batch_size: int) -> int:
    if not rows:
        return 0

    insert_sql = """
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

    cur = sql_conn.cursor()
    cur.fast_executemany = True

    total = 0
    cur.execute("SET IDENTITY_INSERT dbo.comentarios ON;")
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
            cur.executemany(insert_sql, params)
            sql_conn.commit()
            total += len(batch)
            print(f"  comentarios: {total}/{len(rows)}")
    finally:
        cur.execute("SET IDENTITY_INSERT dbo.comentarios OFF;")
        sql_conn.commit()

    return total


def verify_counts(mysql_conn, sql_conn) -> None:
    print("\nVerificando conteos...")

    with mysql_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM `usuarios`;")
        mysql_usuarios = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM `comentarios`;")
        mysql_comentarios = cur.fetchone()["total"]

    cur_sql = sql_conn.cursor()
    sql_usuarios = cur_sql.execute("SELECT COUNT(*) FROM dbo.usuarios;").fetchone()[0]
    sql_comentarios = cur_sql.execute("SELECT COUNT(*) FROM dbo.comentarios;").fetchone()[0]

    print(f"MySQL usuarios:       {mysql_usuarios}")
    print(f"SQL Server usuarios:  {sql_usuarios}")
    print(f"MySQL comentarios:    {mysql_comentarios}")
    print(f"SQL Server comentarios:{sql_comentarios}")

    if mysql_usuarios == sql_usuarios and mysql_comentarios == sql_comentarios:
        print("\nOK: Los conteos coinciden.")
    else:
        print("\nATENCIÓN: Los conteos no coinciden. Revisa errores o filtros.")


def main() -> int:
    load_dotenv()

    batch_size = getenv_int("BATCH_SIZE", 1000)
    truncate = getenv_bool("TRUNCATE_DESTINATION", True)
    limit_rows = getenv_int("LIMIT_ROWS", 10)

    print("Conectando a MySQL/MariaDB origen...")
    mysql_conn = mysql_connect()

    print("Conectando a SQL Server destino...")
    sql_conn = sqlserver_connect()

    try:
        prepare_sqlserver(sql_conn, truncate)

        print("\nLeyendo usuarios desde MySQL...")
        usuarios = fetch_mysql_rows(mysql_conn, "usuarios", order_by="usuario", limit=limit_rows)
        print(f"Filas leídas usuarios: {len(usuarios)}")

        print("Insertando usuarios en SQL Server...")
        insert_usuarios(sql_conn, usuarios, batch_size)

        print("\nLeyendo comentarios desde MySQL...")
        comentarios = fetch_mysql_rows(mysql_conn, "comentarios", order_by="id", limit=limit_rows)
        print(f"Filas leídas comentarios: {len(comentarios)}")

        print("Insertando comentarios en SQL Server...")
        insert_comentarios(sql_conn, comentarios, batch_size)

        verify_counts(mysql_conn, sql_conn)
        print("\nMigración terminada correctamente.")
        return 0

    except Exception as exc:
        sql_conn.rollback()
        print("\nERROR durante la migración:")
        print(str(exc))
        return 1

    finally:
        mysql_conn.close()
        sql_conn.close()


if __name__ == "__main__":
    sys.exit(main())
