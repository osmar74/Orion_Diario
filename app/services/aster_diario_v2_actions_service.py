from __future__ import annotations

import pyodbc
from datetime import datetime, timedelta

from datetime import date, datetime
from pathlib import Path
from typing import Any
import shutil
import json

from app.services.orion_aster_config_service import (
    get_data_root,
    get_module_paths,
    get_sql_config_legacy,
)

from app.services.aster_phase_i_prepare_service import (
    preparar_fase_i_aster,
    probar_conexiones_fase_i_aster,
)

from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster


ASTER_FASE_I_BASE = "Aster_Api"
ASTER_FASE_I_SCHEMA = "dbo"
ASTER_FASE_I_TABLA_USUARIOS = "usuarios"
ASTER_FASE_I_TABLA_COMENTARIOS = "comentarios"
ASTER_MYSQL_DB_USUARIOS = "usuarios"
ASTER_MYSQL_DB_GESTION = "gestioncomercial"


def _fecha_yyyymmdd(fecha: str) -> str:
    raw = str(fecha or "").strip()

    if len(raw) == 8 and raw.isdigit():
        return raw

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw.replace("-", "")

    return raw


def _fecha_sql(fecha: str) -> str:
    raw = _fecha_yyyymmdd(fecha)

    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"

    return raw


def _sql_local_destino() -> dict[str, Any]:
    return get_sql_config_legacy("local", "aster_api")


def _sql_remoto_destino() -> dict[str, Any]:
    return get_sql_config_legacy("remoto", "aster_api")


def _sql_local_origen() -> dict[str, Any]:
    return get_sql_config_legacy("local", "gestioncomercial")


def _qident(value: str) -> str:
    return str(value).replace("]", "]]")


def _conn_str_sqlserver_aster_v2(cfg: dict[str, Any]) -> str:
    driver = str(cfg.get("driver") or "ODBC Driver 18 for SQL Server").strip()
    server = str(cfg.get("server") or cfg.get("servidor") or r"localhost\SQL2025DEV").strip()
    database = str(cfg.get("database") or cfg.get("bd") or "Aster_Api").strip()
    auth = str(cfg.get("auth") or "sql").strip().lower()
    username = str(cfg.get("username") or cfg.get("user") or "").strip()
    password = str(cfg.get("password") or "").strip()
    encrypt = str(cfg.get("encrypt") or "no").strip()
    trust = str(cfg.get("trust") or cfg.get("trust_server_certificate") or "yes").strip()

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust}",
    ]

    if auth == "windows" or not username:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={username}")
        parts.append(f"PWD={password}")

    return ";".join(parts) + ";"


def _probar_sqlserver_cfg_aster_v2(nombre: str, cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        import pyodbc

        cadena = _conn_str_sqlserver_aster_v2(cfg)

        with pyodbc.connect(cadena, timeout=8) as conn:
            cur = conn.cursor()
            cur.execute("SELECT DB_NAME()")
            db_actual = cur.fetchone()[0]

        return {
            "ok": True,
            "success": True,
            "nombre": nombre,
            "engine": "sqlserver",
            "servidor": cfg.get("server") or cfg.get("servidor") or "",
            "database": db_actual or cfg.get("database") or "",
            "mensaje": "Conexión correcta.",
        }

    except Exception as exc:
        return {
            "ok": False,
            "success": False,
            "nombre": nombre,
            "engine": "sqlserver",
            "servidor": cfg.get("server") or cfg.get("servidor") or "",
            "database": cfg.get("database") or "",
            "error": str(exc),
        }


def _probar_fase_i_local_sqlserver_v2() -> dict[str, Any]:
    origen = _probar_sqlserver_cfg_aster_v2(
        "Origen ASTER gestioncomercial_dev",
        _sql_local_origen(),
    )

    destino = _probar_sqlserver_cfg_aster_v2(
        "Destino ASTER Aster_Api",
        _sql_local_destino(),
    )

    ok = bool(origen.get("ok")) and bool(destino.get("ok"))

    return {
        "success": ok,
        "ok": ok,
        "modo": "local_sqlserver",
        "mensaje": (
            "Conexiones locales correctas."
            if ok
            else "Una o más conexiones locales fallaron."
        ),
        "origen": origen,
        "destino": destino,
        "origen_servidor": origen.get("servidor", ""),
        "origen_database": origen.get("database", ""),
        "destino_servidor": destino.get("servidor", ""),
        "destino_database": destino.get("database", ""),
    }


def _table_columns_sqlserver_v2(cur, database: str, schema: str, tabla: str) -> list[dict[str, Any]]:
    db = _qident(database)
    schema_q = _qident(schema)
    tabla_q = _qident(tabla)

    cur.execute(
        f"""
        SELECT
            c.COLUMN_NAME,
            c.DATA_TYPE,
            COLUMNPROPERTY(
                OBJECT_ID(N'[{db}].[{schema_q}].[{tabla_q}]'),
                c.COLUMN_NAME,
                'IsIdentity'
            ) AS IS_IDENTITY
        FROM [{db}].INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = ?
          AND c.TABLE_NAME = ?
        ORDER BY c.ORDINAL_POSITION
        """,
        schema,
        tabla,
    )

    return [
        {
            "name": str(row.COLUMN_NAME),
            "type": str(row.DATA_TYPE),
            "is_identity": bool(row.IS_IDENTITY),
        }
        for row in cur.fetchall()
    ]


def _count_table_crossdb_v2(cur, database: str, schema: str, tabla: str) -> int:
    db = _qident(database)
    sc = _qident(schema)
    tb = _qident(tabla)

    cur.execute(f"SELECT COUNT(1) FROM [{db}].[{sc}].[{tb}]")
    return int(cur.fetchone()[0] or 0)


def _table_exists_crossdb_v2(cur, database: str, schema: str, tabla: str) -> bool:
    db = _qident(database)

    cur.execute(
        f"""
        SELECT COUNT(1)
        FROM [{db}].INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
        """,
        schema,
        tabla,
    )

    return int(cur.fetchone()[0] or 0) > 0


def _detect_fecha_column_crossdb_v2(cur, database: str, schema: str, tabla: str) -> str:
    columnas = _table_columns_sqlserver_v2(cur, database, schema, tabla)
    normalizadas = {
        c["name"].lower().replace("_", "").replace(" ", ""): c["name"]
        for c in columnas
    }

    candidatos = [
        "fecha",
        "Fecha",
        "fecha_gestion",
        "Fecha_Gestion",
        "fechaGestion",
        "FechaGestion",
        "FechayHora",
        "FechaHora",
        "created_at",
        "updated_at",
    ]

    for candidato in candidatos:
        key = candidato.lower().replace("_", "").replace(" ", "")
        if key in normalizadas:
            return normalizadas[key]

    return ""


def _count_fecha_crossdb_v2(
    cur,
    database: str,
    schema: str,
    tabla: str,
    columna_fecha: str,
    fecha_sql: str,
) -> int:
    db = _qident(database)
    sc = _qident(schema)
    tb = _qident(tabla)
    col = _qident(columna_fecha)

    cur.execute(
        f"""
        SELECT COUNT(1)
        FROM [{db}].[{sc}].[{tb}]
        WHERE TRY_CAST([{col}] AS DATE) = ?
        """,
        fecha_sql,
    )

    return int(cur.fetchone()[0] or 0)


def _common_insert_columns_v2(
    source_cols: list[dict[str, Any]],
    dest_cols: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    source_by_norm = {
        c["name"].lower(): c["name"]
        for c in source_cols
    }

    pares: list[tuple[str, str]] = []

    for d in dest_cols:
        if d.get("is_identity"):
            continue

        dest_name = d["name"]
        source_name = source_by_norm.get(dest_name.lower())

        if source_name:
            pares.append((source_name, dest_name))

    return pares



# === ASTER_V2_FASE_I_EXCLUIR_SYSTEMUSER_BEGIN ===

def _aster_v2_sys_q(name):
    return "[" + str(name).replace("]", "]]") + "]"


def _aster_v2_sys_pair_source(pair):
    if isinstance(pair, dict):
        return (
            pair.get("source")
            or pair.get("origen")
            or pair.get("source_column")
            or pair.get("columna_origen")
            or pair.get("sql")
            or pair.get("name")
            or ""
        )

    if isinstance(pair, (list, tuple)) and len(pair) >= 1:
        return pair[0]

    return ""


def _aster_v2_sys_pair_dest(pair):
    if isinstance(pair, dict):
        return (
            pair.get("dest")
            or pair.get("destino")
            or pair.get("target")
            or pair.get("target_column")
            or pair.get("columna_destino")
            or pair.get("sql")
            or pair.get("name")
            or ""
        )

    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
        return pair[1]

    if isinstance(pair, (list, tuple)) and len(pair) >= 1:
        return pair[0]

    return ""


def _aster_v2_sys_user_filter(alias=""):
    prefix = f"{alias}." if alias else ""
    return f"ISNULL(LTRIM(RTRIM(CONVERT(NVARCHAR(255), {prefix}[usuario]))), '') <> ?"


def _aster_v2_count_table_no_systemuser_crossdb_v2(cur, database, schema, tabla):
    sql = f"""
    SELECT COUNT(1)
    FROM {_aster_v2_sys_q(database)}.{_aster_v2_sys_q(schema)}.{_aster_v2_sys_q(tabla)}
    WHERE {_aster_v2_sys_user_filter()}
    """

    cur.execute(sql, "SystemUser")
    row = cur.fetchone()
    return int(row[0] or 0)


def _aster_v2_count_fecha_no_systemuser_crossdb_v2(cur, database, schema, tabla, fecha_col, fecha_sql):
    fecha_sql = _fecha_sql(fecha_sql)

    sql = f"""
    SELECT COUNT(1)
    FROM {_aster_v2_sys_q(database)}.{_aster_v2_sys_q(schema)}.{_aster_v2_sys_q(tabla)}
    WHERE {_aster_v2_sys_q(fecha_col)} >= ?
      AND {_aster_v2_sys_q(fecha_col)} < DATEADD(DAY, 1, ?)
      AND {_aster_v2_sys_user_filter()}
    """

    cur.execute(sql, fecha_sql, fecha_sql, "SystemUser")
    row = cur.fetchone()
    return int(row[0] or 0)

# === ASTER_V2_FASE_I_EXCLUIR_SYSTEMUSER_END ===

def _insert_comentarios_local_v2(cur, fecha_sql: str) -> dict:
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    source_db = origen_cfg.get("database", "gestioncomercial_dev")
    dest_db = destino_cfg.get("database", "Aster_Api")
    schema = "dbo"
    tabla = "comentarios"

    if not _table_exists_crossdb_v2(cur, source_db, schema, tabla):
        return {"ok": False, "error": f"No existe origen {source_db}.dbo.comentarios"}

    if not _table_exists_crossdb_v2(cur, dest_db, schema, tabla):
        return {"ok": False, "error": f"No existe destino {dest_db}.dbo.comentarios"}

    source_fecha = _detect_fecha_column_crossdb_v2(cur, source_db, schema, tabla)
    dest_fecha = _detect_fecha_column_crossdb_v2(cur, dest_db, schema, tabla)

    if not source_fecha:
        return {"ok": False, "error": "No se encontró columna fecha en origen comentarios."}

    if not dest_fecha:
        return {"ok": False, "error": "No se encontró columna fecha en destino comentarios."}

    origen_fecha_total_sin_filtro = _count_fecha_crossdb_v2(
        cur, source_db, schema, tabla, source_fecha, fecha_sql
    )

    origen_fecha_total = _aster_v2_count_fecha_no_systemuser_crossdb_v2(
        cur, source_db, schema, tabla, source_fecha, fecha_sql
    )

    systemuser_excluidos_fecha = max(
        0,
        int(origen_fecha_total_sin_filtro or 0) - int(origen_fecha_total or 0),
    )

    destino_antes_fecha = _count_fecha_crossdb_v2(
        cur, dest_db, schema, tabla, dest_fecha, fecha_sql
    )

    destino_antes_total = _count_table_crossdb_v2(cur, dest_db, schema, tabla)

    if destino_antes_fecha > 0:
        return {
            "ok": False,
            "bloqueado": True,
            "error": f"Ya existen {destino_antes_fecha} comentarios en destino para {fecha_sql}.",
            "origen_fecha_total": origen_fecha_total,
            "origen_fecha_total_sin_filtro": origen_fecha_total_sin_filtro,
            "systemuser_excluidos_fecha": systemuser_excluidos_fecha,
            "destino_antes_fecha": destino_antes_fecha,
            "destino_antes_total": destino_antes_total,
        }

    if origen_fecha_total <= 0:
        return {
            "ok": False,
            "error": f"No hay comentarios origen para {fecha_sql} luego de excluir SystemUser. No se insertó nada.",
            "origen_fecha_total": origen_fecha_total,
            "origen_fecha_total_sin_filtro": origen_fecha_total_sin_filtro,
            "systemuser_excluidos_fecha": systemuser_excluidos_fecha,
            "destino_antes_fecha": destino_antes_fecha,
            "destino_antes_total": destino_antes_total,
        }

    source_cols = _table_columns_sqlserver_v2(cur, source_db, schema, tabla)
    dest_cols = _table_columns_sqlserver_v2(cur, dest_db, schema, tabla)
    pares = _common_insert_columns_v2(source_cols, dest_cols)

    if not pares:
        return {"ok": False, "error": "No hay columnas comunes para insertar comentarios."}

    source_columns = ", ".join(
        "src." + _aster_v2_sys_q(_aster_v2_sys_pair_source(p))
        for p in pares
    )

    dest_columns = ", ".join(
        _aster_v2_sys_q(_aster_v2_sys_pair_dest(p))
        for p in pares
    )

    sql = f"""
    INSERT INTO {_aster_v2_sys_q(dest_db)}.{_aster_v2_sys_q(schema)}.{_aster_v2_sys_q(tabla)}
        ({dest_columns})
    SELECT {source_columns}
    FROM {_aster_v2_sys_q(source_db)}.{_aster_v2_sys_q(schema)}.{_aster_v2_sys_q(tabla)} src
    WHERE src.{_aster_v2_sys_q(source_fecha)} >= ?
      AND src.{_aster_v2_sys_q(source_fecha)} < DATEADD(DAY, 1, ?)
      AND {_aster_v2_sys_user_filter("src")}
    """

    cur.execute(sql, _fecha_sql(fecha_sql), _fecha_sql(fecha_sql), "SystemUser")

    destino_despues_fecha = _count_fecha_crossdb_v2(
        cur, dest_db, schema, tabla, dest_fecha, fecha_sql
    )

    destino_despues_total = _count_table_crossdb_v2(cur, dest_db, schema, tabla)

    insertados = max(0, int(destino_despues_total or 0) - int(destino_antes_total or 0))

    return {
        "ok": True,
        "filtro_usuario": "usuario <> SystemUser",
        "origen_fecha_total": origen_fecha_total,
        "origen_fecha_total_sin_filtro": origen_fecha_total_sin_filtro,
        "systemuser_excluidos_fecha": systemuser_excluidos_fecha,
        "destino_antes_fecha": destino_antes_fecha,
        "destino_despues_fecha": destino_despues_fecha,
        "destino_antes_total": destino_antes_total,
        "destino_despues_total": destino_despues_total,
        "comentarios_insertados": insertados,
        "columnas_insertadas": len(pares),
    }

def _insert_usuarios_local_v2(cur) -> dict[str, Any]:
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    source_db = origen_cfg.get("database", "gestioncomercial_dev")
    dest_db = destino_cfg.get("database", "Aster_Api")

    schema = "dbo"
    tabla = "usuarios"

    if not _table_exists_crossdb_v2(cur, source_db, schema, tabla):
        return {"ok": False, "error": f"No existe origen {source_db}.dbo.usuarios"}

    if not _table_exists_crossdb_v2(cur, dest_db, schema, tabla):
        return {"ok": False, "error": f"No existe destino {dest_db}.dbo.usuarios"}

    source_cols = _table_columns_sqlserver_v2(cur, source_db, schema, tabla)
    dest_cols = _table_columns_sqlserver_v2(cur, dest_db, schema, tabla)
    pares = _common_insert_columns_v2(source_cols, dest_cols)

    if not pares:
        return {
            "ok": False,
            "error": "No hay columnas comunes para insertar usuarios.",
        }

    source_total = _count_table_crossdb_v2(cur, source_db, schema, tabla)
    dest_antes = _count_table_crossdb_v2(cur, dest_db, schema, tabla)

    source_names = {src.lower() for src, _ in pares}
    dest_names = {dest.lower() for _, dest in pares}

    key = ""
    for candidato in ["id", "usuario", "login", "username", "nombre"]:
        if candidato in source_names and candidato in dest_names:
            key = candidato
            break

    dest_columns = ", ".join(f"[{_qident(dest)}]" for _, dest in pares)
    source_columns = ", ".join(f"s.[{_qident(src)}]" for src, _ in pares)

    sdb = _qident(source_db)
    ddb = _qident(dest_db)
    sc = _qident(schema)
    tb = _qident(tabla)

    if dest_antes <= 0:
        sql = f"""
        INSERT INTO [{ddb}].[{sc}].[{tb}] ({dest_columns})
        SELECT {source_columns}
        FROM [{sdb}].[{sc}].[{tb}] s
        """

        cur.execute(sql)

    elif key:
        src_key = next(src for src, dest in pares if src.lower() == key)
        dest_key = next(dest for src, dest in pares if dest.lower() == key)

        source_type = next(
            (
                str(c.get("type", "")).lower()
                for c in source_cols
                if str(c.get("name", "")).lower() == str(src_key).lower()
            ),
            "",
        )

        dest_type = next(
            (
                str(c.get("type", "")).lower()
                for c in dest_cols
                if str(c.get("name", "")).lower() == str(dest_key).lower()
            ),
            "",
        )

        text_types = {
            "char",
            "varchar",
            "nchar",
            "nvarchar",
            "text",
            "ntext",
        }

        if source_type in text_types or dest_type in text_types:
            equal_condition = (
                f"d.[{_qident(dest_key)}] COLLATE DATABASE_DEFAULT = "
                f"s.[{_qident(src_key)}] COLLATE DATABASE_DEFAULT"
            )
        else:
            equal_condition = f"d.[{_qident(dest_key)}] = s.[{_qident(src_key)}]"

        sql = f"""
        INSERT INTO [{ddb}].[{sc}].[{tb}] ({dest_columns})
        SELECT {source_columns}
        FROM [{sdb}].[{sc}].[{tb}] s
        WHERE s.[{_qident(src_key)}] IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM [{ddb}].[{sc}].[{tb}] d
              WHERE {equal_condition}
          )
        """

        cur.execute(sql)

    else:
        dest_despues_skip = _count_table_crossdb_v2(cur, dest_db, schema, tabla)

        return {
            "ok": True,
            "saltado": True,
            "motivo": "Destino usuarios ya tenía datos y no se encontró clave común segura.",
            "usuarios_origen_total": source_total,
            "usuarios_destino_antes": dest_antes,
            "usuarios_destino_despues": dest_despues_skip,
            "usuarios_insertados": 0,
            "columnas_insertadas": len(pares),
        }

    dest_despues = _count_table_crossdb_v2(cur, dest_db, schema, tabla)
    insertados = max(0, dest_despues - dest_antes)

    return {
        "ok": True,
        "saltado": False,
        "usuarios_origen_total": source_total,
        "usuarios_destino_antes": dest_antes,
        "usuarios_destino_despues": dest_despues,
        "usuarios_insertados": insertados,
        "columnas_insertadas": len(pares),
        "clave_usada": key or "destino_vacio",
    }


def _preparar_fase_i_local_sqlserver_v2(fecha_sql: str) -> dict:
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    source_db = origen_cfg.get("database", "gestioncomercial_dev")
    dest_db = destino_cfg.get("database", "Aster_Api")

    cadena = _conn_str_sqlserver_aster_v2(destino_cfg)

    with pyodbc.connect(cadena, timeout=30) as conn:
        cur = conn.cursor()

        origen_usuarios_total = _count_table_crossdb_v2(cur, source_db, "dbo", "usuarios")
        destino_usuarios_total = _count_table_crossdb_v2(cur, dest_db, "dbo", "usuarios")

        origen_comentarios_total_sin_filtro = _count_table_crossdb_v2(
            cur, source_db, "dbo", "comentarios"
        )

        origen_comentarios_total = _aster_v2_count_table_no_systemuser_crossdb_v2(
            cur, source_db, "dbo", "comentarios"
        )

        destino_comentarios_total = _count_table_crossdb_v2(
            cur, dest_db, "dbo", "comentarios"
        )

        source_fecha = _detect_fecha_column_crossdb_v2(
            cur, source_db, "dbo", "comentarios"
        )

        dest_fecha = _detect_fecha_column_crossdb_v2(
            cur, dest_db, "dbo", "comentarios"
        )

        comentarios_origen_fecha_sin_filtro = (
            _count_fecha_crossdb_v2(cur, source_db, "dbo", "comentarios", source_fecha, fecha_sql)
            if source_fecha
            else 0
        )

        comentarios_origen_fecha = (
            _aster_v2_count_fecha_no_systemuser_crossdb_v2(
                cur, source_db, "dbo", "comentarios", source_fecha, fecha_sql
            )
            if source_fecha
            else 0
        )

        comentarios_systemuser_excluidos_fecha = max(
            0,
            int(comentarios_origen_fecha_sin_filtro or 0) - int(comentarios_origen_fecha or 0),
        )

        comentarios_destino_fecha = (
            _count_fecha_crossdb_v2(cur, dest_db, "dbo", "comentarios", dest_fecha, fecha_sql)
            if dest_fecha
            else 0
        )

    return {
        "success": True,
        "ok": True,
        "modo": "local_sqlserver_preparacion",
        "mensaje": "Preparación local correcta. Puede ejecutar Fase I.",
        "fecha_sql": fecha_sql,
        "origen_servidor": origen_cfg.get("server") or origen_cfg.get("servidor"),
        "origen_database": source_db,
        "destino_servidor": destino_cfg.get("server") or destino_cfg.get("servidor"),
        "destino_database": dest_db,
        "tabla_origen": "dbo.comentarios / dbo.usuarios",
        "tabla_destino": "dbo.comentarios / dbo.usuarios",
        "filtro_comentarios": "usuario <> SystemUser",
        "usuarios_origen_total": origen_usuarios_total,
        "usuarios_destino_antes": destino_usuarios_total,
        "comentarios_origen_total": origen_comentarios_total,
        "comentarios_origen_total_sin_filtro": origen_comentarios_total_sin_filtro,
        "comentarios_origen_fecha": comentarios_origen_fecha,
        "comentarios_origen_fecha_sin_filtro": comentarios_origen_fecha_sin_filtro,
        "comentarios_systemuser_excluidos_fecha": comentarios_systemuser_excluidos_fecha,
        "comentarios_destino_antes": destino_comentarios_total,
        "comentarios_destino_fecha": comentarios_destino_fecha,
        "columna_fecha_comentarios_origen": source_fecha,
        "columna_fecha_comentarios_destino": dest_fecha,
    }

def _ejecutar_fase_i_local_sqlserver_v2_sin_gestion(fecha_sql: str) -> dict[str, Any]:
    """
    Ejecuta Fase I LOCAL sin tocar MySQL remoto.

    Bloquea si ya hay comentarios en destino para la fecha.
    """
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    try:

        cadena = _conn_str_sqlserver_aster_v2(destino_cfg)

        with pyodbc.connect(cadena, timeout=20) as conn:
            conn.autocommit = False
            cur = conn.cursor()

            source_db = origen_cfg.get("database", "gestioncomercial_dev")
            dest_db = destino_cfg.get("database", "Aster_Api")

            dest_fecha = _detect_fecha_column_crossdb_v2(cur, dest_db, "dbo", "comentarios")

            if not dest_fecha:
                return {
                    "success": False,
                    "ok": False,
                    "bloqueado": True,
                    "modo": "local_sqlserver_ejecucion",
                    "mensaje": "No se encontró columna fecha en destino comentarios.",
                }

            destino_existente_fecha = _count_fecha_crossdb_v2(
                cur,
                dest_db,
                "dbo",
                "comentarios",
                dest_fecha,
                fecha_sql,
            )

            if destino_existente_fecha > 0:
                return {
                    "success": False,
                    "ok": False,
                    "bloqueado": True,
                    "modo": "local_sqlserver_ejecucion",
                    "mensaje": (
                        f"Inserción bloqueada: ya existen {destino_existente_fecha} "
                        f"comentarios en destino para {fecha_sql}."
                    ),
                    "fecha_sql": fecha_sql,
                    "comentarios_destino_fecha": destino_existente_fecha,
                }

            usuarios = _insert_usuarios_local_v2(cur)
            comentarios = _insert_comentarios_local_v2(cur, fecha_sql)

            if not comentarios.get("ok"):
                conn.rollback()

                return {
                    "success": False,
                    "ok": False,
                    "bloqueado": bool(comentarios.get("bloqueado")),
                    "modo": "local_sqlserver_ejecucion",
                    "mensaje": comentarios.get("error") or "No se pudieron insertar comentarios.",
                    "fecha_sql": fecha_sql,
                    "usuarios": usuarios,
                    "comentarios": comentarios,
                }

            conn.commit()

            ok = bool(usuarios.get("ok")) and bool(comentarios.get("ok"))

            return {
                "success": ok,
                "ok": ok,
                "modo": "local_sqlserver_ejecucion",
                "mensaje": (
                    "Fase I ejecutada correctamente en SQL Server local."
                    if ok
                    else "Fase I ejecutada con observaciones."
                ),
                "fecha_sql": fecha_sql,
                "origen_servidor": origen_cfg.get("server", ""),
                "origen_database": source_db,
                "destino_servidor": destino_cfg.get("server", ""),
                "destino_database": dest_db,
                "usuarios_insertados": usuarios.get("usuarios_insertados", 0),
                "usuarios_destino_antes": usuarios.get("usuarios_destino_antes", 0),
                "usuarios_destino_despues": usuarios.get("usuarios_destino_despues", 0),
                "comentarios_origen_fecha": comentarios.get("origen_fecha_total", 0),
                "comentarios_insertados": comentarios.get("comentarios_insertados", 0),
                "comentarios_destino_antes_fecha": comentarios.get("destino_antes_fecha", 0),
                "comentarios_destino_despues_fecha": comentarios.get("destino_despues_fecha", 0),
                "comentarios_destino_antes_total": comentarios.get("destino_antes_total", 0),
                "comentarios_destino_despues_total": comentarios.get("destino_despues_total", 0),
                "usuarios": usuarios,
                "comentarios": comentarios,
            }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass

        return {
            "success": False,
            "ok": False,
            "modo": "local_sqlserver_ejecucion",
            "mensaje": str(exc),
            "error": str(exc),
            "tipo_error": type(exc).__name__,
        }


def _resumen_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        limpio = {}

        for key, value in obj.items():
            if key in {"html", "tabla_html", "detalle_html"}:
                continue

            if key in {"dataframe", "df", "datos"}:
                continue

            limpio[str(key)] = _resumen_dict(value)

        return limpio

    if isinstance(obj, list):
        return [_resumen_dict(x) for x in obj[:80]]

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict(orient="records")[:80]
        except Exception:
            return str(obj)

    try:
        import numpy as np

        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
    except Exception:
        pass

    return obj


def _status_from_result(resultado: dict[str, Any]) -> str:
    if resultado.get("success") or resultado.get("ok"):
        return "correcto"

    if resultado.get("duplicado") or resultado.get("bloqueado"):
        return "revisar"

    return "error"


def _safe_result(
    comunes: dict[str, Any],
    titulo: str,
    resultado: dict[str, Any],
) -> dict[str, Any]:
    return {
        **comunes,
        "ok": bool(resultado.get("success") or resultado.get("ok")),
        "estado": _status_from_result(resultado),
        "titulo": titulo,
        "mensaje": resultado.get("mensaje") or resultado.get("error") or "Acción finalizada.",
        "resultado": _resumen_dict(resultado),
    }


def _error_result(
    comunes: dict[str, Any],
    titulo: str,
    exc: Exception,
) -> dict[str, Any]:
    return {
        **comunes,
        "ok": False,
        "estado": "error",
        "titulo": titulo,
        "mensaje": str(exc),
        "resultado": {
            "error": str(exc),
            "tipo_error": type(exc).__name__,
        },
    }




# === ASTER_V2_FASES_ABC_JSON_BEGIN ===

def _aster_v2_file_size(path: str) -> int:
    try:
        return int(Path(path).stat().st_size)
    except Exception:
        return 0


def _aster_v2_expected_after_name(fecha: str) -> str:
    return f"After{_fecha_yyyymmdd(fecha)}.xlsx"


def _aster_v2_data_paths(fecha: str) -> dict[str, str]:
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    root = Path(get_data_root())
    base = root / fecha_yyyymmdd / "Aster"

    return {
        "data_root": str(root),
        "aster_base": str(base),
        "archivo_original": str(base / "Archivo_Original"),
        "normalizado": str(base / "Normalizado"),
        "reportes": str(base / "Reportes"),
    }


def _aster_v2_ensure_dirs(fecha: str) -> dict[str, str]:
    paths = _aster_v2_data_paths(fecha)

    for key, value in paths.items():
        if key == "data_root":
            continue

        Path(value).mkdir(parents=True, exist_ok=True)

    return paths


def _aster_v2_find_after_file(fecha: str, conexion: str) -> dict[str, Any]:
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    nombre = _aster_v2_expected_after_name(fecha_yyyymmdd)
    rutas = get_module_paths("aster", conexion)

    revisadas = []

    for base in rutas:
        base_path = Path(str(base))
        candidato = base_path / nombre

        revisadas.append(str(candidato))

        if candidato.exists() and candidato.is_file():
            return {
                "ok": True,
                "success": True,
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "nombre_archivo": nombre,
                "ruta_origen": str(candidato),
                "rutas_revisadas": revisadas,
                "rutas_configuradas": rutas,
                "peso_bytes": _aster_v2_file_size(str(candidato)),
            }

    return {
        "ok": False,
        "success": False,
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "nombre_archivo": nombre,
        "rutas_revisadas": revisadas,
        "rutas_configuradas": rutas,
        "error": f"No se encontró {nombre} en las rutas ASTER configuradas para {conexion}.",
    }


def _aster_v2_count_excel_rows(path: str) -> dict[str, Any]:
    try:
        import pandas as pd

        excel = pd.ExcelFile(path)
        sheet = excel.sheet_names[0] if excel.sheet_names else None

        if not sheet:
            return {
                "ok": False,
                "total_registros": 0,
                "hoja": "",
                "columnas": [],
                "error": "El archivo no tiene hojas.",
            }

        df = pd.read_excel(path, sheet_name=sheet)

        return {
            "ok": True,
            "total_registros": int(len(df.index)),
            "total_columnas": int(len(df.columns)),
            "hoja": str(sheet),
            "columnas": [str(c) for c in list(df.columns)[:80]],
            "previsualizacion": df.head(5).fillna("").astype(str).to_dict(orient="records"),
        }

    except Exception as exc:
        return {
            "ok": False,
            "total_registros": 0,
            "hoja": "",
            "columnas": [],
            "error": str(exc),
        }


def _aster_v2_find_original_file(fecha: str) -> str:
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    paths = _aster_v2_data_paths(fecha_yyyymmdd)
    carpeta = Path(paths["archivo_original"])

    esperado = carpeta / _aster_v2_expected_after_name(fecha_yyyymmdd)

    if esperado.exists():
        return str(esperado)

    if carpeta.exists():
        archivos = sorted(carpeta.glob("After*.xlsx"))

        if archivos:
            return str(archivos[-1])

    return ""





# === ASTER_V2_NORMALIZADO_DIRECTO_BEGIN ===

def _aster_v2_aster_base_directa(fecha_yyyymmdd: str) -> Path:
    """
    Devuelve la carpeta directa ASTER:
    E:/data/YYYYMMDD/Aster

    Si algún helper anterior devuelve E:/data/YYYYMMDD/Aster/aster_YYYYMMDD,
    se corrige automáticamente al padre.
    """
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(base_raw)

    if not str(base):
        raise RuntimeError("No se pudo determinar la carpeta base ASTER.")

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_dir_normalizado(fecha_yyyymmdd: str) -> Path:
    """
    Carpeta correcta:
    E:/data/YYYYMMDD/Aster/Normalizado
    """
    carpeta = _aster_v2_aster_base_directa(fecha_yyyymmdd) / "Normalizado"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_dir_entidades(fecha_yyyymmdd: str) -> Path:
    """
    Carpeta correcta para entidades:
    E:/data/YYYYMMDD/Aster/Entidades
    """
    carpeta = _aster_v2_aster_base_directa(fecha_yyyymmdd) / "Entidades"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta

# === ASTER_V2_NORMALIZADO_DIRECTO_END ===

def _aster_v2_find_normalized_file(fecha_yyyymmdd: str) -> str | None:
    """
    Busca el archivo normalizado ASTER.

    Prioridad nueva:
    1. E:/data/YYYYMMDD/Aster/Normalizado

    Compatibilidad temporal:
    2. E:/data/YYYYMMDD/Aster/aster_YYYYMMDD/Normalizado
    """
    base = _aster_v2_aster_base_directa(fecha_yyyymmdd)

    carpetas = [
        base / "Normalizado",
        base / f"aster_{fecha_yyyymmdd}" / "Normalizado",
    ]

    patrones = [
        f"*{fecha_yyyymmdd}*normalizado*.xlsx",
        f"*{fecha_yyyymmdd}*Normalizado*.xlsx",
        "*normalizado*.xlsx",
        "*Normalizado*.xlsx",
        "*.xlsx",
    ]

    for carpeta in carpetas:
        if not carpeta.exists():
            continue

        for patron in patrones:
            encontrados = sorted(
                carpeta.glob(patron),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if encontrados:
                return str(encontrados[0])

    return None

def _accion_aster_total_actual_v2(fecha: str, conexion: str) -> dict[str, Any]:
    encontrado = _aster_v2_find_after_file(fecha, conexion)

    if not encontrado.get("ok"):
        return {
            "success": False,
            "ok": False,
            "modo": "buscar_total_desde_after",
            "mensaje": encontrado.get("error", "No se encontró archivo ASTER."),
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "nombre_archivo": encontrado.get("nombre_archivo"),
            "rutas_revisadas": encontrado.get("rutas_revisadas", []),
        }

    conteo = _aster_v2_count_excel_rows(encontrado["ruta_origen"])
    ok = bool(conteo.get("ok"))

    return {
        "success": ok,
        "ok": ok,
        "modo": "total_desde_after",
        "mensaje": (
            "Total ASTER detectado correctamente desde archivo After."
            if ok
            else "Se encontró archivo, pero no se pudo leer el total."
        ),
        "fecha_yyyymmdd": encontrado["fecha_yyyymmdd"],
        "nombre_archivo": encontrado["nombre_archivo"],
        "ruta_origen": encontrado["ruta_origen"],
        "peso_bytes": encontrado.get("peso_bytes", 0),
        "total_aster": conteo.get("total_registros", 0),
        "total_registros": conteo.get("total_registros", 0),
        "total_columnas": conteo.get("total_columnas", 0),
        "hoja": conteo.get("hoja", ""),
        "columnas": conteo.get("columnas", []),
        "previsualizacion": conteo.get("previsualizacion", []),
        "rutas_revisadas": encontrado.get("rutas_revisadas", []),
        "error": conteo.get("error", ""),
    }


def _accion_aster_buscar_archivo_v2_legacy_carpetas(fecha: str, conexion: str) -> dict[str, Any]:
    encontrado = _aster_v2_find_after_file(fecha, conexion)

    if not encontrado.get("ok"):
        return {
            "success": False,
            "ok": False,
            "modo": "buscar_archivo_after",
            "mensaje": encontrado.get("error", "No se encontró archivo ASTER."),
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "nombre_archivo": encontrado.get("nombre_archivo"),
            "rutas_revisadas": encontrado.get("rutas_revisadas", []),
        }

    paths = _aster_v2_ensure_dirs(fecha)
    origen = Path(encontrado["ruta_origen"])
    destino = Path(paths["archivo_original"]) / origen.name

    shutil.copy2(origen, destino)

    conteo = _aster_v2_count_excel_rows(str(destino))

    return {
        "success": True,
        "ok": True,
        "modo": "copiar_archivo_after",
        "mensaje": "Archivo ASTER copiado correctamente a DATA.",
        "fecha_yyyymmdd": encontrado["fecha_yyyymmdd"],
        "nombre_archivo": origen.name,
        "ruta_origen": str(origen),
        "ruta_destino": str(destino),
        "carpeta_destino": paths["archivo_original"],
        "peso_bytes": _aster_v2_file_size(str(destino)),
        "total_registros": conteo.get("total_registros", 0),
        "total_columnas": conteo.get("total_columnas", 0),
        "hoja": conteo.get("hoja", ""),
        "columnas": conteo.get("columnas", []),
        "previsualizacion": conteo.get("previsualizacion", []),
    }


def _accion_aster_normalizar_encabezados_v2_legacy_nested(fecha: str, conexion: str) -> dict[str, Any]:
    from app.services.aster_normalization_service import normalizar_archivo_aster

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    ruta_archivo = _aster_v2_find_original_file(fecha_yyyymmdd)

    if not ruta_archivo:
        return {
            "success": False,
            "ok": False,
            "modo": "normalizar_encabezados",
            "mensaje": "No se encontró archivo original ASTER. Ejecute primero la Fase B.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
        }

    resultado = normalizar_archivo_aster(
        data_dir=get_data_root(),
        ruta_archivo=ruta_archivo,
        fecha_yyyymmdd=fecha_yyyymmdd,
    )

    if not resultado.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "normalizar_encabezados",
            "mensaje": resultado.get("error") or "Error normalizando encabezados ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "ruta_archivo": ruta_archivo,
            "resultado_normalizacion": _resumen_dict(resultado),
        }

    ruta_normalizado = str(resultado.get("ruta_normalizado") or "")
    conteo = _aster_v2_count_excel_rows(ruta_normalizado) if ruta_normalizado else {}

    columnas_originales = [str(x) for x in resultado.get("columnas_originales", [])]
    columnas_normalizadas = [str(x) for x in resultado.get("columnas_normalizadas", [])]

    pares = [
        {
            "original": columnas_originales[i] if i < len(columnas_originales) else "",
            "normalizado": columnas_normalizadas[i] if i < len(columnas_normalizadas) else "",
        }
        for i in range(max(len(columnas_originales), len(columnas_normalizadas)))
    ]

    return {
        "success": True,
        "ok": True,
        "modo": "normalizar_encabezados",
        "mensaje": "Encabezados ASTER normalizados correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "ruta_archivo": ruta_archivo,
        "ruta_normalizado": ruta_normalizado,
        "total_columnas_originales": len(columnas_originales),
        "total_columnas_normalizadas": len(columnas_normalizadas),
        "columnas_originales": columnas_originales,
        "columnas_normalizadas": columnas_normalizadas,
        "comparacion_columnas": pares,
        "total_registros": conteo.get("total_registros", 0),
        "total_columnas": conteo.get("total_columnas", 0),
        "hoja": conteo.get("hoja", ""),
        "previsualizacion": conteo.get("previsualizacion", []),
    }

# === ASTER_V2_FASES_ABC_JSON_END ===




# === ASTER_V2_FASE_D_ENTIDADES_BEGIN ===

def _normalizar_lista_entidades_v2(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        salida = []

        for item in value:
            if isinstance(item, dict):
                entidad = (
                    item.get("entidad")
                    or item.get("Entidad")
                    or item.get("valor")
                    or item.get("nombre")
                    or str(item)
                )
                salida.append(str(entidad).strip())
            else:
                salida.append(str(item).strip())

        return [x for x in salida if x]

    try:
        return [str(x).strip() for x in list(value) if str(x).strip()]
    except Exception:
        return []


def _accion_aster_entidades_excel_v2(fecha: str, conexion: str) -> dict[str, Any]:
    from app.services.aster_entity_service import analizar_entidades_excel_aster

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    ruta_normalizado = _aster_v2_find_normalized_file(fecha_yyyymmdd)

    if not ruta_normalizado:
        return {
            "success": False,
            "ok": False,
            "modo": "entidades_excel",
            "mensaje": "No se encontró archivo ASTER normalizado. Ejecute primero la Fase C.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
        }

    resultado = analizar_entidades_excel_aster(ruta_normalizado)

    if not resultado.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "entidades_excel",
            "mensaje": resultado.get("error") or "No se pudieron analizar las entidades del Excel ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "ruta_normalizado": ruta_normalizado,
            "status": resultado.get("status", ""),
            "columnas": resultado.get("columnas", []),
            "resultado_entidades": _resumen_dict(resultado),
        }

    entidades = (
        resultado.get("entidades")
        or resultado.get("entidades_excel")
        or resultado.get("valores_unicos")
        or resultado.get("valores")
        or resultado.get("items")
        or []
    )

    entidades = _normalizar_lista_entidades_v2(entidades)

    total_entidades = (
        resultado.get("total_entidades")
        or resultado.get("total")
        or resultado.get("cantidad")
        or len(entidades)
    )

    return {
        "success": True,
        "ok": True,
        "modo": "entidades_excel",
        "mensaje": "Entidades ASTER analizadas correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "ruta_normalizado": ruta_normalizado,
        "columna": resultado.get("columna") or resultado.get("columna_entidad") or "Entidad",
        "total_entidades": int(total_entidades or 0),
        "entidades": entidades,
        "primeras_entidades": entidades[:20],
        "resultado_entidades": _resumen_dict(resultado),
    }

# === ASTER_V2_FASE_D_ENTIDADES_END ===




# === ASTER_V2_FASE_E_SQL_BEGIN ===

def _normalizar_resultados_sql_v2(resultados: Any) -> list[dict[str, Any]]:
    if not resultados:
        return []

    salida: list[dict[str, Any]] = []

    if isinstance(resultados, list):
        iterable = resultados
    else:
        try:
            iterable = list(resultados)
        except Exception:
            iterable = []

    for item in iterable:
        if isinstance(item, dict):
            salida.append({str(k): v for k, v in item.items()})
        else:
            try:
                salida.append(dict(item))
            except Exception:
                salida.append({"valor": str(item)})

    return salida


def _accion_aster_consulta_sql_v2(fecha: str, conexion: str) -> dict[str, Any]:
    from app.services.aster_sql_entity_service import consultar_entidades_sql_aster

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    resultado = consultar_entidades_sql_aster(
        fecha_sql,
        conexion=conexion,
    )

    if not resultado.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "consulta_sql",
            "mensaje": resultado.get("error") or "Error ejecutando consulta SQL ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": resultado.get("fecha_sql") or fecha_sql,
            "conexion": conexion,
            "resultado_sql": _resumen_dict(resultado),
        }

    resultados = _normalizar_resultados_sql_v2(resultado.get("resultados") or [])
    total_entidades = int(resultado.get("total_entidades") or len(resultados) or 0)
    total_registros = int(resultado.get("total_registros") or 0)

    preview = resultados[:300]

    return {
        "success": True,
        "ok": True,
        "modo": "consulta_sql",
        "mensaje": "Consulta SQL ASTER ejecutada correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": resultado.get("fecha_sql") or fecha_sql,
        "conexion": resultado.get("conexion") or conexion,
        "engine": resultado.get("engine") or ("sqlserver" if conexion == "local" else "mysql"),
        "total_entidades_sql": total_entidades,
        "total_registros_sql": total_registros,
        "resultados_sql": resultados,
        "preview_sql": preview,
        "resultado_sql": _resumen_dict({
            k: v
            for k, v in resultado.items()
            if k not in {"resultados"}
        }),
    }

# === ASTER_V2_FASE_E_SQL_END ===




# === ASTER_V2_FASE_F1_DEPURACION_BEGIN ===

def _accion_aster_depuracion_preparar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    """
    Prepara la depuracion ASTER v2 sin usar session.

    1. Ejecuta consulta SQL por fecha/conexion.
    2. Usa preparar_depuracion_aster(resultados_sql).
    3. Devuelve JSON limpio para visualizacion.
    """
    from app.services.aster_classification_service import preparar_depuracion_aster

    consulta = _accion_aster_consulta_sql_v2(fecha, conexion)

    if not consulta.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_preparar",
            "mensaje": consulta.get("mensaje") or "No se pudo obtener resultados SQL ASTER.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": _fecha_sql(fecha),
            "conexion": conexion,
            "consulta": _resumen_dict(consulta),
        }

    resultados_sql = consulta.get("resultados_sql") or []

    resultado = preparar_depuracion_aster(resultados_sql)

    if not resultado.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_preparar",
            "mensaje": resultado.get("error") or "No hay resultados SQL ASTER para depurar.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": consulta.get("fecha_sql") or _fecha_sql(fecha),
            "conexion": conexion,
            "total_entidades_sql": consulta.get("total_entidades_sql", 0),
            "total_registros_sql": consulta.get("total_registros_sql", 0),
            "resultado_depuracion": _resumen_dict(resultado),
        }

    resultados = _normalizar_resultados_sql_v2(resultado.get("resultados") or [])

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_preparar",
        "mensaje": "Depuración ASTER preparada correctamente.",
        "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
        "fecha_sql": consulta.get("fecha_sql") or _fecha_sql(fecha),
        "conexion": conexion,
        "engine": consulta.get("engine"),
        "total_entidades_sql": consulta.get("total_entidades_sql", len(resultados)),
        "total_registros_sql": consulta.get("total_registros_sql", 0),
        "total_entidades_depuracion": len(resultados),
        "resultados_depuracion": resultados,
        "preview_depuracion": resultados[:300],
    }

# === ASTER_V2_FASE_F1_DEPURACION_END ===




# === ASTER_V2_FASE_F2_EXCLUSIONES_BEGIN ===

def _extraer_entidades_excluir_v2(payload: dict[str, Any] | None) -> set[str]:
    payload = payload or {}

    posibles = (
        payload.get("entidades_excluir")
        or payload.get("excluir")
        or payload.get("exclusiones")
        or []
    )

    if isinstance(posibles, str):
        posibles = [x.strip() for x in posibles.split(",") if x.strip()]

    if not isinstance(posibles, (list, tuple, set)):
        posibles = []

    return {
        str(x).strip()
        for x in posibles
        if str(x).strip()
    }


def _accion_aster_depuracion_excluir_v2(
    fecha: str,
    conexion: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Aplica exclusiones ASTER v2 sin usar session.

    - Reconsulta SQL por fecha/conexion.
    - Aplica aplicar_exclusiones_aster.
    - Devuelve removidos y filtrados por JSON.
    """
    from app.services.aster_classification_service import aplicar_exclusiones_aster

    entidades_excluir = _extraer_entidades_excluir_v2(payload)

    consulta = _accion_aster_consulta_sql_v2(fecha, conexion)

    if not consulta.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_excluir",
            "mensaje": consulta.get("mensaje") or "No se pudo obtener resultados SQL ASTER.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": _fecha_sql(fecha),
            "conexion": conexion,
            "consulta": _resumen_dict(consulta),
        }

    resultados_sql = consulta.get("resultados_sql") or []

    resultado = aplicar_exclusiones_aster(
        resultados_sql=resultados_sql,
        entidades_excluir=entidades_excluir,
    )

    if not resultado.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_excluir",
            "mensaje": resultado.get("error") or "No se pudieron aplicar exclusiones ASTER.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": consulta.get("fecha_sql") or _fecha_sql(fecha),
            "conexion": conexion,
            "total_entidades_sql": consulta.get("total_entidades_sql", 0),
            "total_registros_sql": consulta.get("total_registros_sql", 0),
            "entidades_excluir": sorted(entidades_excluir),
            "resultado_exclusiones": _resumen_dict(resultado),
        }

    removidos = _normalizar_resultados_sql_v2(resultado.get("removidos") or [])
    filtrados = _normalizar_resultados_sql_v2(resultado.get("filtrados") or [])

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_excluir",
        "mensaje": "Exclusiones ASTER aplicadas correctamente.",
        "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
        "fecha_sql": consulta.get("fecha_sql") or _fecha_sql(fecha),
        "conexion": conexion,
        "engine": consulta.get("engine"),
        "total_entidades_sql": consulta.get("total_entidades_sql", len(resultados_sql)),
        "total_registros_sql": consulta.get("total_registros_sql", 0),
        "total_excluidas": len(removidos),
        "total_filtradas": len(filtrados),
        "entidades_excluir": sorted(entidades_excluir),
        "removidos": removidos,
        "filtrados": filtrados,
        "preview_filtrados": filtrados[:300],
        "preview_removidos": removidos[:300],
    }

# === ASTER_V2_FASE_F2_EXCLUSIONES_END ===




# === ASTER_V2_FASE_F_FLUJO_CORRECTO_BEGIN ===

def _accion_aster_clasificacion_guardar_v2(
    fecha: str,
    conexion: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Guarda clasificación ASTER v2 en Excel.

    Genera:
    - Entidades/entidades_aster_YYYYMMDD.xlsx
    - Entidades/exclu_entidades_aster_YYYYMMDD.xlsx
    """
    import pandas as pd


    payload = payload or {}

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha)

    clasificaciones = payload.get("clasificaciones") or []
    removidos = payload.get("removidos") or payload.get("excluidas") or []

    if not isinstance(clasificaciones, list):
        clasificaciones = []

    if not isinstance(removidos, list):
        removidos = []

    def norm_item(item: dict[str, Any], idx: int, excluida: bool = False) -> dict[str, Any]:
        item = item or {}

        sql = str(item.get("sql") or item.get("SQL") or item.get("entidad") or item.get("Entidad") or "").strip()
        excel = str(item.get("excel") or item.get("Excel") or "").strip()
        sss = str(item.get("sss") or item.get("SSS") or item.get("ss") or item.get("SS") or sql or "").strip()

        cant_excel = _aster_v2_f_int(
            item.get("cant_excel")
            or item.get("Cant_excel")
            or item.get("cantidad_excel")
            or 0
        )

        cant_sql = _aster_v2_f_int(
            item.get("cant_sql")
            or item.get("Cant_sql")
            or item.get("cantidad_sql")
            or item.get("numero")
            or item.get("Numero")
            or 0
        )

        clasificacion = str(item.get("clasificacion") or item.get("Clasificacion") or "no_seleccionado").strip()

        if not clasificacion:
            clasificacion = "no_seleccionado"

        return {
            "Nro": idx,
            "SQL": sql,
            "Excel": excel,
            "SSS": sss,
            "Cant_excel": cant_excel,
            "Cant_sql": cant_sql,
            "Diferencia": cant_sql - cant_excel,
            "Clasificacion": clasificacion if not excluida else "excluida",
            "Estado": "Excluida" if excluida else "Considerada",
            "Fecha_proceso": fecha_yyyymmdd,
            "Fecha_sql": fecha_sql,
            "Conexion": conexion,
        }

    entidades = [
        norm_item(item, idx, excluida=False)
        for idx, item in enumerate(clasificaciones, start=1)
    ]

    excluidas = [
        norm_item(item, idx, excluida=True)
        for idx, item in enumerate(removidos, start=1)
    ]

    bases_cobranza = [
        x for x in entidades
        if str(x.get("Clasificacion", "")).lower() in {"cobranza", "cobranza_%", "cobranza %"}
    ]

    bases_integral = [
        x for x in entidades
        if str(x.get("Clasificacion", "")).lower() == "integral"
    ]

    no_seleccionadas = [
        x for x in entidades
        if str(x.get("Clasificacion", "")).lower() in {"", "no_seleccionado", "no seleccionado"}
    ]

    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    # Normalmente paths["aster_base"] apunta a:
    # E:\data\YYYYMMDD\Aster
    # La carpeta final debe ser:
    # E:\data\YYYYMMDD\Aster\aster_YYYYMMDD\Entidades
    aster_base = Path(paths.get("aster_base") or paths.get("aster") or paths.get("base") or "")

    if not aster_base:
        raise RuntimeError("No se pudo determinar carpeta base ASTER.")

    if aster_base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        carpeta_aster_fecha = aster_base
    else:
        carpeta_aster_fecha = aster_base / f"aster_{fecha_yyyymmdd}"

    carpeta_entidades = _aster_v2_dir_entidades(fecha_yyyymmdd)
    carpeta_entidades.mkdir(parents=True, exist_ok=True)

    archivo_entidades = carpeta_entidades / f"entidades_aster_{fecha_yyyymmdd}.xlsx"
    archivo_excluidas = carpeta_entidades / f"exclu_entidades_aster_{fecha_yyyymmdd}.xlsx"

    columnas_entidades = [
        "Nro",
        "SQL",
        "Excel",
        "SSS",
        "Cant_excel",
        "Cant_sql",
        "Diferencia",
        "Clasificacion",
        "Estado",
        "Fecha_proceso",
        "Fecha_sql",
        "Conexion",
    ]

    columnas_excluidas = [
        "Nro",
        "SQL",
        "Excel",
        "SSS",
        "Cant_excel",
        "Cant_sql",
        "Diferencia",
        "Estado",
        "Fecha_proceso",
        "Fecha_sql",
        "Conexion",
    ]

    df_entidades = pd.DataFrame(entidades, columns=columnas_entidades)
    df_excluidas = pd.DataFrame(excluidas, columns=columnas_excluidas)

    resumen_entidades = pd.DataFrame([
        {"Concepto": "Registros removidos", "Total": len(excluidas)},
        {"Concepto": "Bases Cobranza %", "Total": len(bases_cobranza)},
        {"Concepto": "Bases Integral", "Total": len(bases_integral)},
        {"Concepto": "No seleccionadas", "Total": len(no_seleccionadas)},
        {"Concepto": "Entidades revisadas después de exclusiones", "Total": len(entidades)},
        {"Concepto": "Fecha proceso", "Total": fecha_yyyymmdd},
        {"Concepto": "Fecha SQL", "Total": fecha_sql},
        {"Concepto": "Conexión", "Total": conexion},
    ])

    resumen_excluidas = pd.DataFrame([
        {"Concepto": "Registros excluidos", "Total": len(excluidas)},
        {"Concepto": "Fecha proceso", "Total": fecha_yyyymmdd},
        {"Concepto": "Fecha SQL", "Total": fecha_sql},
        {"Concepto": "Conexión", "Total": conexion},
    ])

    with pd.ExcelWriter(archivo_entidades, engine="openpyxl") as writer:
        df_entidades.to_excel(writer, index=False, sheet_name="Entidades")
        resumen_entidades.to_excel(writer, index=False, sheet_name="Resumen")

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 45)

    with pd.ExcelWriter(archivo_excluidas, engine="openpyxl") as writer:
        df_excluidas.to_excel(writer, index=False, sheet_name="Excluidas")
        resumen_excluidas.to_excel(writer, index=False, sheet_name="Resumen")

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 45)

    archivos_generados = [
        {
            "tipo": "Entidades consideradas",
            "archivo": archivo_entidades.name,
            "ruta": str(archivo_entidades),
            "registros": len(entidades),
        },
        {
            "tipo": "Entidades excluidas",
            "archivo": archivo_excluidas.name,
            "ruta": str(archivo_excluidas),
            "registros": len(excluidas),
        },
    ]

    return {
        "success": True,
        "ok": True,
        "modo": "clasificacion_guardar",
        "mensaje": "Clasificación ASTER guardada correctamente en Excel.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "carpeta_entidades": str(carpeta_entidades),
        "ruta_entidades": str(archivo_entidades),
        "ruta_excluidas": str(archivo_excluidas),
        "archivo_entidades": archivo_entidades.name,
        "archivo_excluidas": archivo_excluidas.name,
        "archivos_generados": archivos_generados,
        "registros_removidos": len(excluidas),
        "bases_cobranza": len(bases_cobranza),
        "bases_integral": len(bases_integral),
        "no_seleccionadas": len(no_seleccionadas),
        "entidades_revisadas": len(entidades),
        "removidos": excluidas,
        "bases_cobranza_items": bases_cobranza,
        "bases_integral_items": bases_integral,
        "bases_no_seleccionadas_items": no_seleccionadas,
        "no_excluidas_items": entidades,
    }





# === ASTER_V2_FASE_DE_VALIDACION_BEGIN ===

def _aster_v2_norm_key_entidad(value):
    text = str(value or "").strip()
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1].strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    return " ".join(text.upper().split())


def _aster_v2_int_count(value):
    if value is None:
        return 0

    try:
        return int(round(float(value)))
    except Exception:
        pass

    text = str(value or "").strip()

    if not text:
        return 0

    # En pantalla usamos punto como miles. Para conteos, 10.750 = 10750.
    text = text.replace(".", "").replace(",", ".")

    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _aster_v2_extraer_entidad_sql(row):
    row = row or {}

    entidad = (
        row.get("entidad")
        or row.get("Entidad")
        or row.get("base")
        or row.get("Base")
        or row.get("SQL")
        or row.get("sss")
        or row.get("SSS")
        or ""
    )

    sss = row.get("SSS") or row.get("sss") or entidad

    numero = (
        row.get("Numero")
        or row.get("numero")
        or row.get("cantidad")
        or row.get("Cantidad")
        or row.get("total")
        or row.get("Total")
        or row.get("registros")
        or row.get("Registros")
        or 0
    )

    return {
        "entidad": str(entidad or "").strip().strip("'").strip('"'),
        "sss": str(sss or "").strip(),
        "cantidad": _aster_v2_int_count(numero),
    }


def _aster_v2_leer_entidades_excel_normalizado(fecha):

    import pandas as pd

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    ruta = _aster_v2_find_normalized_file(fecha_yyyymmdd)

    if not ruta:
        return {
            "success": False,
            "error": "No se encontró archivo ASTER normalizado. Ejecute primero la Fase C.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
        }

    excel = pd.ExcelFile(ruta)
    hoja = excel.sheet_names[0] if excel.sheet_names else ""

    if not hoja:
        return {
            "success": False,
            "error": "El archivo normalizado no tiene hojas.",
            "ruta": ruta,
        }

    df = pd.read_excel(ruta, sheet_name=hoja)

    candidatos = [
        "Entidad",
        "entidad",
        "ENTIDAD",
        "Base",
        "base",
        "BASE",
        "Campaña",
        "campaña",
        "Campana",
        "campana",
    ]

    columna_entidad = ""

    for col in candidatos:
        if col in df.columns:
            columna_entidad = col
            break

    if not columna_entidad:
        for col in df.columns:
            nombre = str(col).lower()
            if "entidad" in nombre or "base" in nombre or "camp" in nombre:
                columna_entidad = col
                break

    if not columna_entidad:
        return {
            "success": False,
            "error": "No se encontró columna de entidad/base/campaña en el Excel normalizado.",
            "ruta": ruta,
            "hoja": hoja,
            "columnas": [str(c) for c in df.columns],
        }

    serie = (
        df[columna_entidad]
        .dropna()
        .astype(str)
        .map(lambda x: x.strip())
    )

    serie = serie[
        (serie != "")
        & (serie.str.lower() != "nan")
        & (serie.str.lower() != "none")
    ]

    conteos = serie.value_counts(dropna=True)

    entidades = []

    for entidad, cantidad in conteos.items():
        entidades.append({
            "entidad": str(entidad).strip(),
            "cantidad": int(cantidad),
        })

    return {
        "success": True,
        "ruta": ruta,
        "archivo": Path(ruta).name,
        "hoja": hoja,
        "columna_entidad": str(columna_entidad),
        "total_registros_excel": int(sum(x["cantidad"] for x in entidades)),
        "total_entidades_excel": int(len(entidades)),
        "entidades": entidades,
    }


def _accion_aster_validacion_entidades_de_v2_cache_source(fecha, conexion):
    from app.services.orion_aster_config_service import get_sql_config_legacy

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    excel = _aster_v2_leer_entidades_excel_normalizado(fecha_yyyymmdd)

    if not excel.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "validacion_entidades_de",
            "mensaje": excel.get("error") or "No se pudo leer entidades del Excel ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "excel": _resumen_dict(excel),
        }

    sql = _accion_aster_consulta_sql_v2(fecha_yyyymmdd, conexion)

    if not sql.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "validacion_entidades_de",
            "mensaje": sql.get("mensaje") or "No se pudo ejecutar consulta SQL ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "origen_excel": _resumen_dict(excel),
            "sql": _resumen_dict(sql),
        }

    excel_map = {}

    for item in excel.get("entidades", []):
        key = _aster_v2_norm_key_entidad(item.get("entidad"))
        if not key:
            continue
        excel_map[key] = {
            "nombre": item.get("entidad", ""),
            "cantidad": _aster_v2_int_count(item.get("cantidad")),
        }

    sql_map = {}

    for row in sql.get("resultados_sql", []):
        item = _aster_v2_extraer_entidad_sql(row)
        key = _aster_v2_norm_key_entidad(item.get("entidad"))

        if not key:
            continue

        sql_map[key] = {
            "nombre": item.get("entidad", ""),
            "sss": item.get("sss", ""),
            "cantidad": _aster_v2_int_count(item.get("cantidad")),
        }

    filas = []
    usados = set()

    for key, item_excel in sorted(
        excel_map.items(),
        key=lambda kv: (-kv[1]["cantidad"], kv[1]["nombre"])
    ):
        item_sql = sql_map.get(key)
        usados.add(key)

        if item_sql:
            if item_excel["cantidad"] == item_sql["cantidad"]:
                estado = "Coincide"
            else:
                estado = "Diferencia cantidad"

            filas.append({
                "excel": item_excel["nombre"],
                "cant_excel": item_excel["cantidad"],
                "sql": item_sql["nombre"],
                "cant_sql": item_sql["cantidad"],
                "sss": item_sql.get("sss", ""),
                "estado": estado,
            })
        else:
            filas.append({
                "excel": item_excel["nombre"],
                "cant_excel": item_excel["cantidad"],
                "sql": "",
                "cant_sql": 0,
                "sss": "",
                "estado": "Solo Excel",
            })

    for key, item_sql in sorted(
        sql_map.items(),
        key=lambda kv: (-kv[1]["cantidad"], kv[1]["nombre"])
    ):
        if key in usados:
            continue

        filas.append({
            "excel": "",
            "cant_excel": 0,
            "sql": item_sql["nombre"],
            "cant_sql": item_sql["cantidad"],
            "sss": item_sql.get("sss", ""),
            "estado": "Solo SQL",
        })

    for i, row in enumerate(filas, start=1):
        row["nro"] = i

    coincidencias = sum(1 for x in filas if x["estado"] == "Coincide")
    solo_excel = sum(1 for x in filas if x["estado"] == "Solo Excel")
    solo_sql = sum(1 for x in filas if x["estado"] == "Solo SQL")
    diferencias = sum(1 for x in filas if x["estado"] == "Diferencia cantidad")

    try:
        sql_cfg = get_sql_config_legacy(conexion, "gestioncomercial")
    except Exception:
        sql_cfg = {}

    origen_excel = {
        "tipo": "Excel normalizado ASTER",
        "archivo": excel.get("archivo", ""),
        "ruta": excel.get("ruta", ""),
        "hoja": excel.get("hoja", ""),
        "columna_entidad": excel.get("columna_entidad", ""),
        "total_registros": excel.get("total_registros_excel", 0),
        "total_entidades": excel.get("total_entidades_excel", 0),
    }

    origen_sql = {
        "tipo": "Consulta SQL ASTER",
        "conexion": conexion,
        "engine": sql.get("engine", ""),
        "servidor": sql_cfg.get("server") or sql_cfg.get("servidor") or sql.get("servidor") or "",
        "database": sql_cfg.get("database") or sql.get("database") or "",
        "tabla": "consulta entidades ASTER",
        "fecha_sql": sql.get("fecha_sql") or fecha_sql,
        "total_registros": sql.get("total_registros_sql", 0),
        "total_entidades": sql.get("total_entidades_sql", len(sql_map)),
    }

    kpis = {
        "total_entidades_excel": int(excel.get("total_entidades_excel", 0)),
        "total_entidades_sql": int(sql.get("total_entidades_sql", len(sql_map))),
        "coincidentes": int(coincidencias),
        "solo_excel": int(solo_excel),
        "solo_sql": int(solo_sql),
        "diferencia_cantidad": int(diferencias),
        "total_registros_excel": int(excel.get("total_registros_excel", 0)),
        "total_registros_sql": int(sql.get("total_registros_sql", 0)),
    }

    return {
        "success": True,
        "ok": True,
        "modo": "validacion_entidades_de",
        "mensaje": "Preparación y validación de entidades ASTER generada correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "kpis": kpis,
        "origen_excel": origen_excel,
        "origen_sql": origen_sql,
        "tabla_comparativa": filas,
        "total_filas_comparacion": len(filas),
        "total_entidades_excel": kpis["total_entidades_excel"],
        "total_entidades_sql": kpis["total_entidades_sql"],
        "coincidentes": kpis["coincidentes"],
        "solo_excel": kpis["solo_excel"],
        "solo_sql": kpis["solo_sql"],
        "diferencia_cantidad": kpis["diferencia_cantidad"],
    }

# === ASTER_V2_FASE_DE_VALIDACION_END ===



# === ASTER_V2_F_CONCILIACION_DEPURACION_BEGIN ===

def _aster_v2_f_norm_key(value):
    text = str(value or "").strip()
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1].strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    return " ".join(text.upper().split())


def _aster_v2_f_int(value):
    if value is None:
        return 0

    try:
        return int(round(float(value)))
    except Exception:
        pass

    text = str(value or "").strip()

    if not text:
        return 0

    text = text.replace(".", "").replace(",", ".")

    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _aster_v2_f_row_key(row):
    return _aster_v2_f_norm_key(
        row.get("sql")
        or row.get("SQL")
        or row.get("excel")
        or row.get("Excel")
        or row.get("entidad")
        or row.get("Entidad")
        or ""
    )


def _aster_v2_f_normalizar_filas_validacion(tabla):
    filas = []

    for i, row in enumerate(tabla or [], start=1):
        sql = str(row.get("sql") or row.get("SQL") or "").strip()
        excel = str(row.get("excel") or row.get("Excel") or "").strip()
        sss = str(row.get("sss") or row.get("SSS") or sql or "").strip()

        cant_excel = _aster_v2_f_int(row.get("cant_excel") or row.get("Cant_excel"))
        cant_sql = _aster_v2_f_int(row.get("cant_sql") or row.get("Cant_sql"))

        estado = str(row.get("estado") or row.get("Estado") or "").strip()

        if not estado:
            if sql and excel and cant_excel == cant_sql:
                estado = "Coincide"
            elif sql and excel and cant_excel != cant_sql:
                estado = "Diferencia cantidad"
            elif excel and not sql:
                estado = "Solo Excel"
            elif sql and not excel:
                estado = "Solo SQL"
            else:
                estado = "Sin dato"

        filas.append({
            "nro": int(row.get("nro") or row.get("#") or i),
            "sql": sql,
            "excel": excel,
            "sss": sss,
            "cant_excel": cant_excel,
            "cant_sql": cant_sql,
            "estado": estado,
            "clave": _aster_v2_f_row_key({
                "sql": sql,
                "excel": excel,
            }),
        })

    return filas


def _aster_v2_f_extraer_exclusiones(payload):
    payload = payload or {}

    valores = (
        payload.get("entidades_excluir")
        or payload.get("excluir")
        or payload.get("exclusiones")
        or []
    )

    if isinstance(valores, str):
        valores = [x.strip() for x in valores.split(",") if x.strip()]

    if not isinstance(valores, (list, tuple, set)):
        valores = []

    return {_aster_v2_f_norm_key(x) for x in valores if str(x).strip()}


def _aster_v2_f_calcular_resumen(no_excluidas, excluidas, validacion):
    excel_unicas = int((validacion.get("kpis") or {}).get("total_entidades_excel") or 0)

    sql_consideradas = sum(1 for row in no_excluidas if row.get("sql"))
    no_tomadas = len(excluidas)

    excel_faltan_sql = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo Excel"
    )

    sql_faltan_excel = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo SQL"
    )

    cant_excel_considerada = sum(_aster_v2_f_int(row.get("cant_excel")) for row in no_excluidas)
    cant_sql_considerada = sum(_aster_v2_f_int(row.get("cant_sql")) for row in no_excluidas)
    diferencia_cantidad = cant_sql_considerada - cant_excel_considerada

    return {
        "entidades_unicas_excel": excel_unicas,
        "entidades_sql_consideradas": sql_consideradas,
        "entidades_no_tomadas_en_cuenta": no_tomadas,
        "entidades_excel_faltan_sql": excel_faltan_sql,
        "entidades_sql_faltan_excel": sql_faltan_excel,
        "cant_excel_considerada": cant_excel_considerada,
        "cant_sql_considerada": cant_sql_considerada,
        "diferencia_cantidad_sql_excel": diferencia_cantidad,
        "diferencia_absoluta": abs(diferencia_cantidad),
    }


def _accion_aster_depuracion_preparar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    validacion = _accion_aster_validacion_entidades_de_v2(fecha, conexion)

    if not validacion.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_preparar",
            "mensaje": validacion.get("mensaje") or "No se pudo preparar la depuración.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": _fecha_sql(fecha),
            "validacion": _resumen_dict(validacion),
        }

    filas = _aster_v2_f_normalizar_filas_validacion(
        validacion.get("tabla_comparativa") or []
    )

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_preparar",
        "mensaje": "Depuración ASTER preparada correctamente.",
        "fecha_yyyymmdd": validacion.get("fecha_yyyymmdd") or _fecha_yyyymmdd(fecha),
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha),
        "conexion": conexion,
        "kpis": validacion.get("kpis") or {},
        "tabla_depuracion": filas,
        "total_filas_depuracion": len(filas),
        "total_entidades_excel": validacion.get("total_entidades_excel", 0),
        "total_entidades_sql": validacion.get("total_entidades_sql", 0),
    }


def _accion_aster_depuracion_excluir_v2(
    fecha: str,
    conexion: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validacion = _accion_aster_validacion_entidades_de_v2(fecha, conexion)

    if not validacion.get("success"):
        return {
            "success": False,
            "ok": False,
            "modo": "depuracion_excluir",
            "mensaje": validacion.get("mensaje") or "No se pudo aplicar exclusiones.",
            "fecha_yyyymmdd": _fecha_yyyymmdd(fecha),
            "fecha_sql": _fecha_sql(fecha),
            "validacion": _resumen_dict(validacion),
        }

    filas = _aster_v2_f_normalizar_filas_validacion(
        validacion.get("tabla_comparativa") or []
    )

    seleccionadas = _aster_v2_f_extraer_exclusiones(payload)

    excluidas = []
    no_excluidas = []

    for row in filas:
        claves = {
            _aster_v2_f_norm_key(row.get("sql")),
            _aster_v2_f_norm_key(row.get("excel")),
            _aster_v2_f_norm_key(row.get("sss")),
            _aster_v2_f_norm_key(row.get("clave")),
        }

        if claves.intersection(seleccionadas):
            excluidas.append(row)
        else:
            no_excluidas.append(row)

    resumen = _aster_v2_f_calcular_resumen(no_excluidas, excluidas, validacion)

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_excluir",
        "mensaje": "Exclusiones ASTER aplicadas correctamente.",
        "fecha_yyyymmdd": validacion.get("fecha_yyyymmdd") or _fecha_yyyymmdd(fecha),
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha),
        "conexion": conexion,
        "resumen_conciliacion": resumen,
        "kpi_conciliacion": {
            "entidades_unicas_excel": resumen["entidades_unicas_excel"],
            "entidades_sql_consideradas": resumen["entidades_sql_consideradas"],
            "entidades_no_tomadas_en_cuenta": resumen["entidades_no_tomadas_en_cuenta"],
            "entidades_excel_faltan_sql": resumen["entidades_excel_faltan_sql"],
            "entidades_sql_faltan_excel": resumen["entidades_sql_faltan_excel"],
            "cant_excel_considerada": resumen["cant_excel_considerada"],
            "cant_sql_considerada": resumen["cant_sql_considerada"],
            "diferencia_absoluta": resumen["diferencia_absoluta"],
        },
        "no_excluidas": no_excluidas,
        "excluidas": excluidas,
        "filtrados": no_excluidas,
        "removidos": excluidas,
        "total_no_excluidas": len(no_excluidas),
        "total_excluidas": len(excluidas),
        "entidades_excluir": sorted(seleccionadas),
    }

# === ASTER_V2_F_CONCILIACION_DEPURACION_END ===


# === ASTER_V2_FASE_C_MOVER_NORMALIZADO_DIRECTO_BEGIN ===

def _aster_v2_normalizado_directo_desde_ruta(ruta_original: str, fecha_yyyymmdd: str) -> str:
    """
    Convierte:
    E:/data/YYYYMMDD/Aster/aster_YYYYMMDD/Normalizado/archivo.xlsx

    a:
    E:/data/YYYYMMDD/Aster/Normalizado/archivo.xlsx
    """
    ruta = Path(str(ruta_original))

    partes = [p.lower() for p in ruta.parts]
    carpeta_fecha = f"aster_{fecha_yyyymmdd}".lower()

    if carpeta_fecha in partes:
        idx = partes.index(carpeta_fecha)

        # Esperado: ... / Aster / aster_YYYYMMDD / Normalizado / archivo.xlsx
        if idx > 0:
            aster_base = Path(*ruta.parts[:idx])
            destino_dir = aster_base / "Normalizado"
            destino_dir.mkdir(parents=True, exist_ok=True)

            destino = destino_dir / ruta.name

            if ruta.exists():
                if destino.exists():
                    destino.unlink()

                shutil.copy2(ruta, destino)

                # Eliminar archivo viejo para no dejar duplicado.
                try:
                    ruta.unlink()
                except Exception:
                    pass

                # Eliminar Normalizado viejo si quedó vacío.
                try:
                    ruta.parent.rmdir()
                except Exception:
                    pass

                # Eliminar aster_YYYYMMDD si quedó vacío.
                try:
                    ruta.parent.parent.rmdir()
                except Exception:
                    pass

            return str(destino)

    return str(ruta)


def _aster_v2_actualizar_rutas_normalizado_directo(obj, fecha_yyyymmdd: str):
    """
    Recorre el resultado JSON de Fase C y corrige cualquier ruta normalizada
    que apunte a Aster/aster_YYYYMMDD/Normalizado.
    """
    if isinstance(obj, dict):
        nuevo = {}

        for key, value in obj.items():
            key_l = str(key).lower()

            if isinstance(value, str):
                value_l = value.lower().replace("/", "\\")

                if (
                    f"\\aster_{fecha_yyyymmdd.lower()}\\normalizado\\" in value_l
                    or (
                        "normalizado" in key_l
                        and f"aster_{fecha_yyyymmdd.lower()}" in value_l
                    )
                ):
                    nuevo[key] = _aster_v2_normalizado_directo_desde_ruta(value, fecha_yyyymmdd)
                else:
                    nuevo[key] = value
            else:
                nuevo[key] = _aster_v2_actualizar_rutas_normalizado_directo(value, fecha_yyyymmdd)

        return nuevo

    if isinstance(obj, list):
        return [
            _aster_v2_actualizar_rutas_normalizado_directo(x, fecha_yyyymmdd)
            for x in obj
        ]

    return obj


def _accion_aster_normalizar_encabezados_v2_visual_source(*args, **kwargs) -> dict[str, Any]:
    """
    Wrapper definitivo para Fase C.

    Ejecuta la lógica existente, pero fuerza que el archivo normalizado quede en:
    E:/data/YYYYMMDD/Aster/Normalizado
    """
    resultado = _accion_aster_normalizar_encabezados_v2_legacy_nested(*args, **kwargs)

    fecha = (
        kwargs.get("fecha")
        or kwargs.get("fecha_proceso")
        or kwargs.get("fecha_yyyymmdd")
        or (args[0] if args else "")
    )

    fecha_yyyymmdd = _fecha_yyyymmdd(str(fecha))

    resultado = _aster_v2_actualizar_rutas_normalizado_directo(resultado, fecha_yyyymmdd)

    # Si el resultado tiene ruta_normalizado directa, agregar bandera visible.
    if isinstance(resultado, dict):
        ruta_norm = (
            resultado.get("ruta_normalizado")
            or resultado.get("ruta_normalizada")
            or resultado.get("ruta_normalizado_xlsx")
        )

        if ruta_norm:
            resultado["normalizado_directo"] = True
            resultado["carpeta_normalizado_correcta"] = str(Path(ruta_norm).parent)

    return resultado

# === ASTER_V2_FASE_C_MOVER_NORMALIZADO_DIRECTO_END ===


# === ASTER_V2_CACHE_VALIDACION_DE_F_BEGIN ===

def _aster_v2_cache_aster_base(fecha_yyyymmdd: str) -> Path:
    """
    Base directa:
    E:/data/YYYYMMDD/Aster
    """
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if not str(base):
        raise RuntimeError("No se pudo determinar carpeta base ASTER.")

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_cache_entidades_dir(fecha_yyyymmdd: str) -> Path:
    """
    Carpeta cache/salida:
    E:/data/YYYYMMDD/Aster/Entidades
    """
    carpeta = _aster_v2_cache_aster_base(fecha_yyyymmdd) / "Entidades"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_cache_validacion_path(fecha_yyyymmdd: str) -> Path:
    return _aster_v2_cache_entidades_dir(fecha_yyyymmdd) / f"validacion_entidades_aster_{fecha_yyyymmdd}.json"


def _aster_v2_cache_write_validacion(fecha_yyyymmdd: str, data: dict[str, Any]) -> str:
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    payload = dict(data or {})
    payload["cache_generado"] = True
    payload["cache_generado_en"] = datetime.now().isoformat(timespec="seconds")
    payload["ruta_cache"] = str(ruta)

    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return str(ruta)


def _aster_v2_cache_read_validacion(fecha_yyyymmdd: str) -> dict[str, Any] | None:
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    if not ruta.exists():
        return None

    try:
        data = json.loads(ruta.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    data["cache_usado"] = True
    data["ruta_cache"] = str(ruta)
    return data


def _accion_aster_validacion_entidades_de_v2(fecha, conexion):
    """
    D-E: ejecuta validación pesada una vez y guarda cache JSON.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)

    resultado = _accion_aster_validacion_entidades_de_v2_cache_source(fecha, conexion)

    if isinstance(resultado, dict) and resultado.get("success"):
        ruta_cache = _aster_v2_cache_write_validacion(fecha_yyyymmdd, resultado)
        resultado["cache_generado"] = True
        resultado["ruta_cache"] = ruta_cache
        resultado["mensaje"] = (
            str(resultado.get("mensaje") or "Validación generada correctamente.")
            + " Cache D-E actualizado."
        )

    return resultado


def _aster_v2_cache_norm_key(value):
    text = str(value or "").strip()

    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1].strip()

    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return " ".join(text.upper().split())


def _aster_v2_cache_int(value):
    if value is None:
        return 0

    try:
        return int(round(float(value)))
    except Exception:
        pass

    text = str(value or "").strip()

    if not text:
        return 0

    text = text.replace(".", "").replace(",", ".")

    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _aster_v2_cache_normalizar_filas(tabla):
    filas = []

    for i, row in enumerate(tabla or [], start=1):
        row = row or {}

        sql = str(row.get("sql") or row.get("SQL") or "").strip()
        excel = str(row.get("excel") or row.get("Excel") or "").strip()
        sss = str(row.get("sss") or row.get("SSS") or sql or "").strip()

        cant_excel = _aster_v2_cache_int(row.get("cant_excel") or row.get("Cant_excel"))
        cant_sql = _aster_v2_cache_int(row.get("cant_sql") or row.get("Cant_sql"))

        estado = str(row.get("estado") or row.get("Estado") or "").strip()

        if not estado:
            if sql and excel and cant_excel == cant_sql:
                estado = "Coincide"
            elif sql and excel and cant_excel != cant_sql:
                estado = "Diferencia cantidad"
            elif excel and not sql:
                estado = "Solo Excel"
            elif sql and not excel:
                estado = "Solo SQL"
            else:
                estado = "Sin dato"

        clave = _aster_v2_cache_norm_key(sql or excel or sss)

        filas.append({
            "nro": int(row.get("nro") or row.get("#") or i),
            "sql": sql,
            "excel": excel,
            "sss": sss,
            "cant_excel": cant_excel,
            "cant_sql": cant_sql,
            "estado": estado,
            "clave": clave,
        })

    return filas


def _aster_v2_cache_extraer_exclusiones(payload):
    payload = payload or {}

    valores = (
        payload.get("entidades_excluir")
        or payload.get("excluir")
        or payload.get("exclusiones")
        or []
    )

    if isinstance(valores, str):
        valores = [x.strip() for x in valores.split(",") if x.strip()]

    if not isinstance(valores, (list, tuple, set)):
        valores = []

    return {_aster_v2_cache_norm_key(x) for x in valores if str(x).strip()}


def _aster_v2_cache_resumen(no_excluidas, excluidas, validacion):
    kpis = validacion.get("kpis") or {}

    excel_unicas = int(kpis.get("total_entidades_excel") or 0)
    sql_consideradas = sum(1 for row in no_excluidas if row.get("sql"))
    no_tomadas = len(excluidas)

    excel_faltan_sql = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo Excel"
    )

    sql_faltan_excel = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo SQL"
    )

    cant_excel_considerada = sum(_aster_v2_cache_int(row.get("cant_excel")) for row in no_excluidas)
    cant_sql_considerada = sum(_aster_v2_cache_int(row.get("cant_sql")) for row in no_excluidas)
    diferencia = cant_sql_considerada - cant_excel_considerada

    return {
        "entidades_unicas_excel": excel_unicas,
        "entidades_sql_consideradas": sql_consideradas,
        "entidades_no_tomadas_en_cuenta": no_tomadas,
        "entidades_excel_faltan_sql": excel_faltan_sql,
        "entidades_sql_faltan_excel": sql_faltan_excel,
        "cant_excel_considerada": cant_excel_considerada,
        "cant_sql_considerada": cant_sql_considerada,
        "diferencia_cantidad_sql_excel": diferencia,
        "diferencia_absoluta": abs(diferencia),
    }


def _aster_v2_cache_required_response(fecha, conexion, modo):
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    return {
        "success": False,
        "ok": False,
        "modo": modo,
        "mensaje": "Debe ejecutar primero D-E → Preparar validación D-E para generar el cache.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_requerido": True,
        "ruta_cache_esperada": str(ruta),
    }


def _accion_aster_depuracion_preparar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    """
    F preparar: usa cache D-E. No vuelve a leer Excel ni consultar SQL.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    validacion = _aster_v2_cache_read_validacion(fecha_yyyymmdd)

    if not validacion:
        return _aster_v2_cache_required_response(fecha, conexion, "depuracion_preparar")

    filas = _aster_v2_cache_normalizar_filas(
        validacion.get("tabla_comparativa") or []
    )

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_preparar",
        "mensaje": "Depuración ASTER preparada desde cache D-E.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_usado": True,
        "ruta_cache": validacion.get("ruta_cache") or str(_aster_v2_cache_validacion_path(fecha_yyyymmdd)),
        "kpis": validacion.get("kpis") or {},
        "tabla_depuracion": filas,
        "total_filas_depuracion": len(filas),
        "total_entidades_excel": validacion.get("total_entidades_excel", 0),
        "total_entidades_sql": validacion.get("total_entidades_sql", 0),
    }


def _accion_aster_depuracion_excluir_v2(
    fecha: str,
    conexion: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    F aplicar exclusiones: usa cache D-E. No vuelve a leer Excel ni consultar SQL.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    validacion = _aster_v2_cache_read_validacion(fecha_yyyymmdd)

    if not validacion:
        return _aster_v2_cache_required_response(fecha, conexion, "depuracion_excluir")

    filas = _aster_v2_cache_normalizar_filas(
        validacion.get("tabla_comparativa") or []
    )

    seleccionadas = _aster_v2_cache_extraer_exclusiones(payload)

    excluidas = []
    no_excluidas = []

    for row in filas:
        claves = {
            _aster_v2_cache_norm_key(row.get("sql")),
            _aster_v2_cache_norm_key(row.get("excel")),
            _aster_v2_cache_norm_key(row.get("sss")),
            _aster_v2_cache_norm_key(row.get("clave")),
        }

        if claves.intersection(seleccionadas):
            excluidas.append(row)
        else:
            no_excluidas.append(row)

    resumen = _aster_v2_cache_resumen(no_excluidas, excluidas, validacion)

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_excluir",
        "mensaje": "Exclusiones ASTER aplicadas desde cache D-E.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_usado": True,
        "ruta_cache": validacion.get("ruta_cache") or str(_aster_v2_cache_validacion_path(fecha_yyyymmdd)),
        "resumen_conciliacion": resumen,
        "kpi_conciliacion": {
            "entidades_unicas_excel": resumen["entidades_unicas_excel"],
            "entidades_sql_consideradas": resumen["entidades_sql_consideradas"],
            "entidades_no_tomadas_en_cuenta": resumen["entidades_no_tomadas_en_cuenta"],
            "entidades_excel_faltan_sql": resumen["entidades_excel_faltan_sql"],
            "entidades_sql_faltan_excel": resumen["entidades_sql_faltan_excel"],
            "cant_excel_considerada": resumen["cant_excel_considerada"],
            "cant_sql_considerada": resumen["cant_sql_considerada"],
            "diferencia_absoluta": resumen["diferencia_absoluta"],
        },
        "no_excluidas": no_excluidas,
        "excluidas": excluidas,
        "filtrados": no_excluidas,
        "removidos": excluidas,
        "total_no_excluidas": len(no_excluidas),
        "total_excluidas": len(excluidas),
        "entidades_excluir": sorted(seleccionadas),
    }

# === ASTER_V2_CACHE_VALIDACION_DE_F_END ===


# === ASTER_V2_FASE_G_CONCILIACION_BEGIN ===

def _aster_v2_g_entidades_dir(fecha_yyyymmdd: str) -> Path:
    """
    Carpeta fuente de Fase G:
    E:/data/YYYYMMDD/Aster/Entidades
    """
    if "_aster_v2_cache_entidades_dir" in globals():
        return _aster_v2_cache_entidades_dir(fecha_yyyymmdd)

    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    carpeta = base / "Entidades"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_g_paths(fecha_yyyymmdd: str) -> dict[str, str]:
    carpeta = _aster_v2_g_entidades_dir(fecha_yyyymmdd)

    return {
        "carpeta_entidades": str(carpeta),
        "entidades": str(carpeta / f"entidades_aster_{fecha_yyyymmdd}.xlsx"),
        "excluidas": str(carpeta / f"exclu_entidades_aster_{fecha_yyyymmdd}.xlsx"),
        "cache": str(carpeta / f"validacion_entidades_aster_{fecha_yyyymmdd}.json"),
    }


def _aster_v2_g_int(value) -> int:
    if value is None:
        return 0

    try:
        return int(round(float(value)))
    except Exception:
        pass

    text = str(value or "").strip()

    if not text:
        return 0

    text = text.replace(".", "").replace(",", ".")

    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _aster_v2_g_read_excel(path: str, sheet_name: str) -> list[dict[str, Any]]:

    import pandas as pd

    ruta = Path(path)

    if not ruta.exists():
        return []

    try:
        df = pd.read_excel(ruta, sheet_name=sheet_name)
    except Exception:
        df = pd.read_excel(ruta)

    df = df.fillna("")

    rows = []

    for _, row in df.iterrows():
        item = {}

        for col in df.columns:
            item[str(col)] = row[col]

        rows.append(item)

    return rows


def _aster_v2_g_read_cache(path: str) -> dict[str, Any]:
    ruta = Path(path)

    if not ruta.exists():
        return {}

    try:
        data = json.loads(ruta.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _aster_v2_g_required_columns(rows: list[dict[str, Any]], required: list[str]) -> list[str]:
    if not rows:
        return required

    columns = set(rows[0].keys())
    return [col for col in required if col not in columns]


def _aster_v2_g_normalizar_clasificacion(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"cobranza", "cobranza %", "cobranza_%"}:
        return "cobranza"

    if text == "integral":
        return "integral"

    if text == "excluida":
        return "excluida"

    return "no_seleccionado"


def _accion_aster_conciliacion_validar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    """
    Fase G v2.

    Valida los productos generados por F:
    - entidades_aster_YYYYMMDD.xlsx
    - exclu_entidades_aster_YYYYMMDD.xlsx
    - validacion_entidades_aster_YYYYMMDD.json
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    paths = _aster_v2_g_paths(fecha_yyyymmdd)

    ruta_entidades = Path(paths["entidades"])
    ruta_excluidas = Path(paths["excluidas"])
    ruta_cache = Path(paths["cache"])

    archivos = [
        {
            "tipo": "Entidades consideradas",
            "archivo": ruta_entidades.name,
            "ruta": str(ruta_entidades),
            "existe": ruta_entidades.exists(),
        },
        {
            "tipo": "Entidades excluidas",
            "archivo": ruta_excluidas.name,
            "ruta": str(ruta_excluidas),
            "existe": ruta_excluidas.exists(),
        },
        {
            "tipo": "Cache validación D-E",
            "archivo": ruta_cache.name,
            "ruta": str(ruta_cache),
            "existe": ruta_cache.exists(),
        },
    ]

    faltantes = [x for x in archivos if not x["existe"]]

    if faltantes:
        return {
            "success": False,
            "ok": False,
            "modo": "conciliacion_validacion",
            "mensaje": "No se puede validar Fase G. Faltan archivos generados por F o por D-E.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
            "archivos": archivos,
            "faltantes": faltantes,
            "carpeta_entidades": paths["carpeta_entidades"],
        }

    entidades = _aster_v2_g_read_excel(str(ruta_entidades), "Entidades")
    excluidas = _aster_v2_g_read_excel(str(ruta_excluidas), "Excluidas")
    cache = _aster_v2_g_read_cache(str(ruta_cache))

    columnas_entidades_faltantes = _aster_v2_g_required_columns(
        entidades,
        ["SQL", "Cant_excel", "Cant_sql", "Diferencia", "Clasificacion"],
    )

    columnas_excluidas_faltantes = _aster_v2_g_required_columns(
        excluidas,
        ["SQL", "Cant_excel", "Cant_sql", "Diferencia", "Estado"],
    )

    errores = []

    if columnas_entidades_faltantes:
        errores.append({
            "tipo": "columnas_entidades",
            "mensaje": "Faltan columnas en entidades_aster.",
            "detalle": columnas_entidades_faltantes,
        })

    if columnas_excluidas_faltantes:
        errores.append({
            "tipo": "columnas_excluidas",
            "mensaje": "Faltan columnas en exclu_entidades_aster.",
            "detalle": columnas_excluidas_faltantes,
        })

    total_entidades = len(entidades)
    total_excluidas = len(excluidas)
    total_cache_filas = len(cache.get("tabla_comparativa") or [])

    cant_excel = sum(_aster_v2_g_int(x.get("Cant_excel")) for x in entidades)
    cant_sql = sum(_aster_v2_g_int(x.get("Cant_sql")) for x in entidades)
    diferencia = cant_sql - cant_excel

    diferencias = []

    for item in entidades:
        dif = _aster_v2_g_int(item.get("Diferencia"))

        if dif != 0:
            diferencias.append({
                "SQL": item.get("SQL", ""),
                "Excel": item.get("Excel", ""),
                "Cant_excel": _aster_v2_g_int(item.get("Cant_excel")),
                "Cant_sql": _aster_v2_g_int(item.get("Cant_sql")),
                "Diferencia": dif,
                "Clasificacion": item.get("Clasificacion", ""),
            })

    clasificaciones = {
        "cobranza": 0,
        "integral": 0,
        "no_seleccionado": 0,
    }

    for item in entidades:
        clasif = _aster_v2_g_normalizar_clasificacion(item.get("Clasificacion"))
        if clasif not in clasificaciones:
            clasif = "no_seleccionado"
        clasificaciones[clasif] += 1

    sql_vacios = [
        {
            "fila": i + 2,
            "SQL": item.get("SQL", ""),
            "Clasificacion": item.get("Clasificacion", ""),
        }
        for i, item in enumerate(entidades)
        if not str(item.get("SQL") or "").strip()
    ]

    duplicados = []
    vistos = {}

    for i, item in enumerate(entidades, start=2):
        sql = str(item.get("SQL") or "").strip().upper()

        if not sql:
            continue

        if sql in vistos:
            duplicados.append({
                "SQL": item.get("SQL", ""),
                "fila_original": vistos[sql],
                "fila_duplicada": i,
            })
        else:
            vistos[sql] = i

    if sql_vacios:
        errores.append({
            "tipo": "sql_vacios",
            "mensaje": "Existen entidades consideradas sin SQL.",
            "total": len(sql_vacios),
        })

    if duplicados:
        errores.append({
            "tipo": "duplicados",
            "mensaje": "Existen entidades SQL duplicadas en entidades_aster.",
            "total": len(duplicados),
        })

    estado_general = "correcto" if not errores else "revisar"

    resumen = {
        "entidades_consideradas": total_entidades,
        "entidades_excluidas": total_excluidas,
        "filas_cache_validacion": total_cache_filas,
        "bases_cobranza": clasificaciones["cobranza"],
        "bases_integral": clasificaciones["integral"],
        "no_seleccionadas": clasificaciones["no_seleccionado"],
        "cantidad_excel_considerada": cant_excel,
        "cantidad_sql_considerada": cant_sql,
        "diferencia_sql_excel": diferencia,
        "diferencias_cantidad": len(diferencias),
        "errores_validacion": len(errores),
    }

    kpis = {
        "entidades_consideradas": total_entidades,
        "entidades_excluidas": total_excluidas,
        "bases_cobranza": clasificaciones["cobranza"],
        "bases_integral": clasificaciones["integral"],
        "no_seleccionadas": clasificaciones["no_seleccionado"],
        "diferencias_cantidad": len(diferencias),
        "errores_validacion": len(errores),
        "cantidad_excel_considerada": cant_excel,
        "cantidad_sql_considerada": cant_sql,
        "diferencia_abs": abs(diferencia),
    }

    return {
        "success": True,
        "ok": True,
        "estado_validacion": estado_general,
        "modo": "conciliacion_validacion",
        "mensaje": (
            "Conciliación ASTER validada correctamente."
            if estado_general == "correcto"
            else "Conciliación ASTER validada con observaciones."
        ),
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "carpeta_entidades": paths["carpeta_entidades"],
        "archivos": archivos,
        "resumen": resumen,
        "kpis": kpis,
        "errores": errores,
        "duplicados": duplicados[:100],
        "sql_vacios": sql_vacios[:100],
        "diferencias": diferencias[:300],
        "preview_entidades": entidades[:300],
        "preview_excluidas": excluidas[:300],
    }

# === ASTER_V2_FASE_G_CONCILIACION_END ===


# === ASTER_V2_FASE_H1_PREPARAR_INSERCION_BEGIN ===

def _aster_v2_h_base_directa(fecha_yyyymmdd: str) -> Path:
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if not str(base):
        raise RuntimeError("No se pudo determinar la carpeta base ASTER.")

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_h_normalizado_path(fecha_yyyymmdd: str) -> Path | None:
    base = _aster_v2_h_base_directa(fecha_yyyymmdd)
    carpeta = base / "Normalizado"

    candidatos = []

    if carpeta.exists():
        for patron in [
            f"*{fecha_yyyymmdd}*normalizado*.xlsx",
            f"*{fecha_yyyymmdd}*Normalizado*.xlsx",
            "*normalizado*.xlsx",
            "*Normalizado*.xlsx",
            "*.xlsx",
        ]:
            candidatos.extend(list(carpeta.glob(patron)))

    candidatos = sorted(
        set(candidatos),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return candidatos[0] if candidatos else None


def _aster_v2_h_entidades_dir(fecha_yyyymmdd: str) -> Path:
    carpeta = _aster_v2_h_base_directa(fecha_yyyymmdd) / "Entidades"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_h_prepare_cache_path(fecha_yyyymmdd: str) -> Path:
    return _aster_v2_h_entidades_dir(fecha_yyyymmdd) / f"preparacion_insercion_aster_{fecha_yyyymmdd}.json"


def _aster_v2_h_read_excel_headers_fast(path: Path) -> dict[str, Any]:
    """
    Optimizado:
    - Lee solo encabezados con pandas nrows=0.
    - Cuenta filas con openpyxl read_only.
    """
    import pandas as pd
    import openpyxl

    import openpyxl

    if not path.exists():
        return {
            "ok": False,
            "error": "No existe archivo normalizado.",
            "ruta": str(path),
        }

    df_head = pd.read_excel(path, nrows=0)
    columnas = [str(c).strip() for c in df_head.columns]

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    total_filas = max(int(ws.max_row or 1) - 1, 0)
    hoja = ws.title
    wb.close()

    return {
        "ok": True,
        "ruta": str(path),
        "archivo": path.name,
        "hoja": hoja,
        "columnas_excel": columnas,
        "total_columnas_excel": len(columnas),
        "total_registros_excel": total_filas,
    }


def _aster_v2_h_column_name(col: dict[str, Any]) -> str:
    """
    Obtiene nombre de columna SQL de forma robusta.

    Evita KeyError: 'columna' porque la metadata puede llegar como:
    COLUMN_NAME, column_name, name, nombre, columna, sql, etc.
    """
    col = col or {}

    for key in [
        "columna",
        "Columna",
        "COLUMN_NAME",
        "column_name",
        "name",
        "Name",
        "nombre",
        "Nombre",
        "sql",
        "SQL",
    ]:
        value = col.get(key)
        if value not in (None, ""):
            return str(value).strip()

    return ""

def _aster_v2_h_sql_columns_from_db(conexion: str) -> dict[str, Any]:
    import pyodbc

    cfg = _sql_remoto_destino() if str(conexion).lower() == "remoto" else _sql_local_destino()

    database = str(cfg.get("database") or cfg.get("bd") or ASTER_FASE_I_BASE or "Aster_Api")
    schema = "dbo"
    tabla = "aster_dia_nc"

    cadena = _conn_str_sqlserver_aster_v2(cfg)

    with pyodbc.connect(cadena, timeout=10) as conn:
        cur = conn.cursor()
        columnas = _table_columns_sqlserver_v2(cur, database, schema, tabla)

    columnas_norm = []

    for col in columnas:
        col = col or {}
        nombre = _aster_v2_h_column_name(col)

        columnas_norm.append({
            "columna": nombre,
            "COLUMN_NAME": nombre,
            "tipo_sql": str(
                col.get("tipo_sql")
                or col.get("DATA_TYPE")
                or col.get("data_type")
                or col.get("tipo")
                or col.get("type")
                or ""
            ),
            "nullable": str(
                col.get("nullable")
                or col.get("IS_NULLABLE")
                or col.get("is_nullable")
                or ""
            ),
            "max_length": (
                col.get("max_length")
                or col.get("CHARACTER_MAXIMUM_LENGTH")
                or col.get("character_maximum_length")
                or ""
            ),
            "raw": col,
        })

    return {
        "conexion": conexion,
        "servidor": cfg.get("server") or cfg.get("servidor") or "",
        "database": database,
        "schema": schema,
        "tabla": tabla,
        "columnas_sql": columnas_norm,
        "total_columnas_sql": len(columnas_norm),
    }

def _aster_v2_h_detect_fecha_column(columns: list[dict[str, Any]]) -> str:
    nombres = [_aster_v2_h_column_name(c) for c in columns]

    candidatos = [
        "fecha_proceso",
        "Fecha_Proceso",
        "FECHA_PROCESO",
        "fecha",
        "Fecha",
        "FECHA",
        "fecha_gestion",
        "Fecha_Gestion",
        "fechagestion",
        "FechaGestion",
        "fecha_inicio",
        "fechainicio",
        "FechaInicio",
        "created_at",
    ]

    for candidato in candidatos:
        for nombre in nombres:
            if str(nombre).lower() == candidato.lower():
                return nombre

    for nombre in nombres:
        if "fecha" in str(nombre).lower():
            return nombre

    return ""

def _aster_v2_h_count_fecha_destino(
    conexion: str,
    fecha_sql: str,
    columnas_sql: list[dict[str, Any]],
) -> dict[str, Any]:
    import pyodbc
    from datetime import datetime, timedelta

    cfg = _sql_remoto_destino() if str(conexion).lower() == "remoto" else _sql_local_destino()

    database = str(cfg.get("database") or cfg.get("bd") or ASTER_FASE_I_BASE or "Aster_Api")
    schema = "dbo"
    tabla = "aster_dia_nc"
    columna_fecha = _aster_v2_h_detect_fecha_column(columnas_sql)

    if not columna_fecha:
        return {
            "ok": False,
            "error": "No se encontró columna de fecha de proceso en Aster_Api.dbo.aster_dia_nc.",
            "database": database,
            "schema": schema,
            "tabla": tabla,
            "registros_fecha_destino": None,
            "existe_fecha_destino": False,
        }

    fecha_inicio = _fecha_sql(fecha_sql)
    dt_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fecha_fin = (dt_inicio + timedelta(days=1)).strftime("%Y-%m-%d")

    cadena = _conn_str_sqlserver_aster_v2(cfg)

    sql_range = f"""
    SELECT COUNT(1)
    FROM [{database}].[{schema}].[{tabla}]
    WHERE [{columna_fecha}] >= ?
      AND [{columna_fecha}] < ?
    """

    total = 0
    metodo = "rango_fecha"

    try:
        with pyodbc.connect(cadena, timeout=10) as conn:
            cur = conn.cursor()
            cur.execute(sql_range, fecha_inicio, fecha_fin)
            total = int(cur.fetchone()[0] or 0)
    except Exception:
        # Fallback para columnas texto o formatos no datetime.
        sql_convert = f"""
        SELECT COUNT(1)
        FROM [{database}].[{schema}].[{tabla}]
        WHERE TRY_CONVERT(date, [{columna_fecha}]) = ?
        """

        metodo = "try_convert_date"

        with pyodbc.connect(cadena, timeout=10) as conn:
            cur = conn.cursor()
            cur.execute(sql_convert, fecha_inicio)
            total = int(cur.fetchone()[0] or 0)

    return {
        "ok": True,
        "database": database,
        "schema": schema,
        "tabla": tabla,
        "columna_fecha": columna_fecha,
        "fecha_inicio": fecha_inicio,
        "fecha_fin_exclusiva": fecha_fin,
        "metodo": metodo,
        "registros_fecha_destino": total,
        "existe_fecha_destino": total > 0,
    }

def _aster_v2_h_compare_columns(columnas_excel: list[str], columnas_sql: list[dict[str, Any]]) -> dict[str, Any]:
    excel_map = {str(c).strip().lower(): str(c).strip() for c in columnas_excel if str(c).strip()}
    sql_names = [_aster_v2_h_column_name(c) for c in columnas_sql]
    sql_map = {str(c).strip().lower(): str(c).strip() for c in sql_names if str(c).strip()}

    comunes = []
    solo_excel = []
    solo_sql = []

    for key, excel_name in excel_map.items():
        if key in sql_map:
            comunes.append({
                "excel": excel_name,
                "sql": sql_map[key],
                "estado": "comun",
            })
        else:
            solo_excel.append(excel_name)

    for key, sql_name in sql_map.items():
        if key not in excel_map:
            solo_sql.append(sql_name)

    columnas_minimas = {"fecha", "data", "comentario", "entidad", "usuario"}
    comunes_lower = {x["sql"].lower() for x in comunes}
    minimas_faltantes = sorted([x for x in columnas_minimas if x not in comunes_lower])

    return {
        "columnas_comunes": comunes,
        "total_columnas_comunes": len(comunes),
        "solo_excel": sorted(solo_excel),
        "solo_sql": sorted(solo_sql),
        "total_solo_excel": len(solo_excel),
        "total_solo_sql": len(solo_sql),
        "columnas_minimas_referencia": sorted(columnas_minimas),
        "columnas_minimas_faltantes": minimas_faltantes,
        "columnas_ok": len(comunes) > 0 and not minimas_faltantes,
    }


def _accion_aster_insercion_preparar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    """
    H1 v2:
    - No inserta.
    - Compara encabezado de AfterYYYYMMDD_normalizado.xlsx contra Aster_Api.dbo.aster_dia_nc.
    - Revisa si el JSON de validación tiene encabezado y si coincide con el Excel.
    - Valida si ya existen datos para la misma fecha de proceso.
    """
    import json
    from datetime import datetime

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    ruta_normalizado = _aster_v2_h_normalizado_path(fecha_yyyymmdd)

    if not ruta_normalizado:
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_preparar",
            "mensaje": "No se encontró archivo ASTER normalizado. Ejecute primero la Fase C.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
        }

    excel = _aster_v2_h_read_excel_headers_fast(ruta_normalizado)

    if not excel.get("ok"):
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_preparar",
            "mensaje": excel.get("error") or "No se pudo leer archivo normalizado.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
            "excel": excel,
        }

    sql_info = _aster_v2_h_sql_columns_from_db(conexion)

    columnas_excel = [str(c).strip() for c in excel.get("columnas_excel", []) if str(c).strip()]
    columnas_sql_meta = sql_info.get("columnas_sql", [])
    columnas_sql = [_aster_v2_h_column_name(c) for c in columnas_sql_meta]
    columnas_sql = [c for c in columnas_sql if c]

    def norm(value):
        return str(value or "").strip().lower()

    sql_by_norm = {norm(c): c for c in columnas_sql}
    excel_by_norm = {norm(c): c for c in columnas_excel}

    columnas_insertables = []

    for col_excel in columnas_excel:
        key = norm(col_excel)

        if key in sql_by_norm:
            col_sql = sql_by_norm[key]
            meta = next((m for m in columnas_sql_meta if norm(_aster_v2_h_column_name(m)) == key), {})

            columnas_insertables.append({
                "excel": col_excel,
                "sql": col_sql,
                "tipo_sql": str(meta.get("tipo_sql") or ""),
                "nullable": str(meta.get("nullable") or ""),
                "max_length": meta.get("max_length") or "",
                "estado": "Coincide / Insertable",
            })

    excel_no_insertables = [
        col for col in columnas_excel
        if norm(col) not in sql_by_norm
    ]

    sql_no_excel = [
        col for col in columnas_sql
        if norm(col) not in excel_by_norm
    ]

    # Revisar si el JSON D-E tiene encabezado del Excel.
    carpeta_entidades = _aster_v2_h_entidades_dir(fecha_yyyymmdd)
    ruta_json = carpeta_entidades / f"validacion_entidades_aster_{fecha_yyyymmdd}.json"

    json_headers = []
    json_header_found = False
    json_header_source = ""

    if ruta_json.exists():
        try:
            data_json = json.loads(ruta_json.read_text(encoding="utf-8", errors="ignore"))

            posibles = [
                ("encabezado_excel", data_json.get("encabezado_excel")),
                ("columnas_excel", data_json.get("columnas_excel")),
                ("excel.columnas_excel", (data_json.get("excel") or {}).get("columnas_excel") if isinstance(data_json.get("excel"), dict) else None),
                ("excel.columnas", (data_json.get("excel") or {}).get("columnas") if isinstance(data_json.get("excel"), dict) else None),
                ("origen_excel.columnas", (data_json.get("origen_excel") or {}).get("columnas") if isinstance(data_json.get("origen_excel"), dict) else None),
                ("origen_excel.columnas_excel", (data_json.get("origen_excel") or {}).get("columnas_excel") if isinstance(data_json.get("origen_excel"), dict) else None),
            ]

            for source, value in posibles:
                if isinstance(value, list) and value:
                    json_headers = [str(x).strip() for x in value if str(x).strip()]
                    json_header_found = True
                    json_header_source = source
                    break
        except Exception:
            json_headers = []

    json_excel_faltantes = []
    json_excel_sobrantes = []

    if json_header_found:
        json_set = {norm(x) for x in json_headers}
        excel_set = {norm(x) for x in columnas_excel}

        json_excel_faltantes = [
            col for col in columnas_excel
            if norm(col) not in json_set
        ]

        json_excel_sobrantes = [
            col for col in json_headers
            if norm(col) not in excel_set
        ]

        json_estado = "coincide" if not json_excel_faltantes and not json_excel_sobrantes else "diferente"
        json_mensaje = (
            "El encabezado del JSON coincide con el Excel normalizado."
            if json_estado == "coincide"
            else "El encabezado del JSON no coincide completamente con el Excel normalizado."
        )
    else:
        json_estado = "sin_encabezado_en_json"
        json_mensaje = (
            "El JSON de validación no contiene encabezado de columnas del Excel. "
            "Esto es esperable si ese JSON fue generado para validación de entidades, no para inserción."
        )

    fecha_destino = _aster_v2_h_count_fecha_destino(
        conexion=conexion,
        fecha_sql=fecha_sql,
        columnas_sql=columnas_sql_meta,
    )

    existe_fecha = bool(fecha_destino.get("existe_fecha_destino"))

    columnas_ok = bool(columnas_insertables)

    estado_preparacion = (
        "bloqueado_fecha_existente"
        if existe_fecha
        else ("correcto" if columnas_ok else "revisar_columnas")
    )

    if existe_fecha:
        mensaje = (
            f"Ya existen {fecha_destino.get('registros_fecha_destino')} registros en destino "
            f"para {fecha_sql}. Si continúa, duplicará la carga. Avise al administrador."
        )
    elif columnas_ok:
        mensaje = "Preparación de inserción ASTER correcta. El encabezado Excel fue comparado contra Aster_Api.dbo.aster_dia_nc."
    else:
        mensaje = "Preparación con observaciones: no se encontraron columnas insertables entre Excel y Aster_Api.dbo.aster_dia_nc."

    comparacion_columnas = {
        "metodo": "encabezado_excel_vs_aster_dia_nc",
        "descripcion": "Encabezado del Excel normalizado comparado contra columnas de Aster_Api.dbo.aster_dia_nc.",
        "tabla_sql_comparada": f"{sql_info['database']}.{sql_info['schema']}.{sql_info['tabla']}",
        "columnas_insertables": columnas_insertables,
        "total_columnas_insertables": len(columnas_insertables),
        "excel_no_insertables": excel_no_insertables,
        "total_excel_no_insertables": len(excel_no_insertables),
        "sql_no_excel": sql_no_excel,
        "total_sql_no_excel": len(sql_no_excel),
        "columnas_ok": columnas_ok,
    }

    json_headers_check = {
        "ruta_json": str(ruta_json),
        "json_existe": ruta_json.exists(),
        "json_tiene_encabezado": json_header_found,
        "json_header_source": json_header_source,
        "estado": json_estado,
        "mensaje": json_mensaje,
        "total_columnas_json": len(json_headers),
        "total_columnas_excel": len(columnas_excel),
        "faltantes_en_json": json_excel_faltantes,
        "sobrantes_en_json": json_excel_sobrantes,
    }

    resultado = {
        "success": True,
        "ok": not existe_fecha and columnas_ok,
        "modo": "insercion_preparar",
        "estado_preparacion": estado_preparacion,
        "bloqueado_por_fecha": existe_fecha,
        "requiere_admin": existe_fecha,
        "mensaje": mensaje,
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "tabla_destino": f"{sql_info['database']}.{sql_info['schema']}.{sql_info['tabla']}",
        "ruta_normalizado": str(ruta_normalizado),
        "archivo_normalizado": ruta_normalizado.name,
        "excel": excel,
        "sql": {
            "servidor": sql_info.get("servidor", ""),
            "database": sql_info["database"],
            "schema": sql_info["schema"],
            "tabla": sql_info["tabla"],
            "total_columnas_sql": sql_info["total_columnas_sql"],
        },
        "fecha_destino": fecha_destino,
        "comparacion_columnas": comparacion_columnas,
        "json_headers_check": json_headers_check,
        "kpis": {
            "registros_excel": excel.get("total_registros_excel", 0),
            "columnas_excel": len(columnas_excel),
            "columnas_sql": len(columnas_sql),
            "columnas_insertables": len(columnas_insertables),
            "excel_no_insertables": len(excel_no_insertables),
            "sql_no_excel": len(sql_no_excel),
            "registros_destino_fecha": fecha_destino.get("registros_fecha_destino") or 0,
        },
    }

    cache_path = _aster_v2_h_prepare_cache_path(fecha_yyyymmdd)
    payload = dict(resultado)
    payload["encabezado_excel"] = columnas_excel
    payload["encabezado_sql"] = columnas_sql
    payload["cache_generado_en"] = datetime.now().isoformat(timespec="seconds")
    payload["ruta_cache_preparacion"] = str(cache_path)

    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    resultado["ruta_cache_preparacion"] = str(cache_path)

    return resultado


# === ASTER_V2_FASE_H2_EJECUTAR_INSERCION_BEGIN ===

def _aster_v2_h_resultado_insercion_path(fecha_yyyymmdd: str) -> Path:
    return _aster_v2_h_entidades_dir(fecha_yyyymmdd) / f"resultado_insercion_aster_{fecha_yyyymmdd}.json"


def _aster_v2_h_read_prepare_cache(fecha_yyyymmdd: str) -> dict[str, Any] | None:
    import json

    ruta = _aster_v2_h_prepare_cache_path(fecha_yyyymmdd)

    if not ruta.exists():
        return None

    try:
        data = json.loads(ruta.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def _aster_v2_h_sql_quote(name: str) -> str:
    return "[" + str(name).replace("]", "]]") + "]"


def _aster_v2_h_python_value(value):
    import pandas as pd

    if pd.isna(value):
        return None

    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime()
        except Exception:
            return value

    return value


def _aster_v2_h_build_insert_dataframe(ruta_excel: Path, columnas_insertables: list[dict[str, Any]]):
    import pandas as pd

    if not ruta_excel.exists():
        raise FileNotFoundError(f"No existe archivo normalizado: {ruta_excel}")

    df = pd.read_excel(ruta_excel, dtype=object)

    faltantes = []

    for item in columnas_insertables:
        col_excel = str(item.get("excel") or "").strip()
        if col_excel and col_excel not in df.columns:
            faltantes.append(col_excel)

    if faltantes:
        raise RuntimeError(
            "No se puede insertar. Faltan columnas del Excel normalizado: "
            + ", ".join(faltantes[:20])
        )

    data = {}

    for item in columnas_insertables:
        col_excel = str(item.get("excel") or "").strip()
        col_sql = str(item.get("sql") or "").strip()

        if not col_excel or not col_sql:
            continue

        data[col_sql] = df[col_excel]

    df_insert = pd.DataFrame(data)

    # Normalización ligera para pyodbc.
    for col in df_insert.columns:
        df_insert[col] = df_insert[col].map(_aster_v2_h_python_value)

    return df_insert


def _aster_v2_h_insert_dataframe_sql(
    conexion: str,
    df_insert,
    database: str,
    schema: str,
    tabla: str,
    tamano_lote: int = 1000,
) -> int:
    import pyodbc

    if df_insert.empty:
        return 0

    cfg = _sql_remoto_destino() if str(conexion).lower() == "remoto" else _sql_local_destino()
    cadena = _conn_str_sqlserver_aster_v2(cfg)

    columnas = list(df_insert.columns)

    columnas_sql = ", ".join(_aster_v2_h_sql_quote(c) for c in columnas)
    placeholders = ", ".join(["?"] * len(columnas))

    sql_insert = f"""
    INSERT INTO [{database}].[{schema}].[{tabla}] ({columnas_sql})
    VALUES ({placeholders})
    """

    total = 0

    with pyodbc.connect(cadena, timeout=30) as conn:
        cur = conn.cursor()
        cur.fast_executemany = True

        for inicio in range(0, len(df_insert), tamano_lote):
            bloque = df_insert.iloc[inicio: inicio + tamano_lote]
            valores = [
                tuple(_aster_v2_h_python_value(v) for v in row)
                for row in bloque.itertuples(index=False, name=None)
            ]

            if not valores:
                continue

            cur.executemany(sql_insert, valores)
            total += len(valores)

        conn.commit()

    return total


def _accion_aster_insercion_ejecutar_v2(fecha: str, conexion: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    H2 v2:
    Inserta el Excel normalizado en Aster_Api.dbo.aster_dia_nc.

    Seguridad:
    - Requiere cache de H1.
    - Recuenta destino por fecha antes de insertar.
    - Si ya existen registros para la fecha, bloquea para evitar duplicación.
    """
    import json
    from datetime import datetime

    payload = payload or {}

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    cache = _aster_v2_h_read_prepare_cache(fecha_yyyymmdd)

    if not cache:
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_ejecutar",
            "mensaje": "No existe preparación H1. Ejecute primero H → Preparar inserción.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
            "ruta_cache_preparacion": str(_aster_v2_h_prepare_cache_path(fecha_yyyymmdd)),
        }

    ruta_normalizado = _aster_v2_h_normalizado_path(fecha_yyyymmdd)

    if not ruta_normalizado:
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_ejecutar",
            "mensaje": "No se encontró archivo ASTER normalizado. Ejecute primero la Fase C.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
        }

    sql_info = _aster_v2_h_sql_columns_from_db(conexion)
    fecha_destino_antes = _aster_v2_h_count_fecha_destino(
        conexion=conexion,
        fecha_sql=fecha_sql,
        columnas_sql=sql_info["columnas_sql"],
    )

    registros_antes = int(fecha_destino_antes.get("registros_fecha_destino") or 0)

    if registros_antes > 0:
        resultado = {
            "success": False,
            "ok": False,
            "modo": "insercion_ejecutar",
            "estado_insercion": "bloqueado_fecha_existente",
            "bloqueado_por_fecha": True,
            "requiere_admin": True,
            "mensaje": (
                f"Inserción bloqueada: ya existen {registros_antes} registros en "
                f"{sql_info['database']}.{sql_info['schema']}.{sql_info['tabla']} para {fecha_sql}. "
                "Si continúa, duplicará la carga. Avise al administrador."
            ),
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
            "tabla_destino": f"{sql_info['database']}.{sql_info['schema']}.{sql_info['tabla']}",
            "ruta_normalizado": str(ruta_normalizado),
            "fecha_destino_antes": fecha_destino_antes,
        }

        ruta_resultado = _aster_v2_h_resultado_insercion_path(fecha_yyyymmdd)
        resultado["ruta_resultado_insercion"] = str(ruta_resultado)
        ruta_resultado.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        return resultado

    comp = cache.get("comparacion_columnas") or {}
    columnas_insertables = comp.get("columnas_insertables") or []

    if not columnas_insertables:
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_ejecutar",
            "estado_insercion": "sin_columnas_insertables",
            "mensaje": "No hay columnas insertables en la preparación H1. Revise H → Preparar inserción.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
        }

    df_insert = _aster_v2_h_build_insert_dataframe(
        ruta_excel=ruta_normalizado,
        columnas_insertables=columnas_insertables,
    )

    total_leidos = int(len(df_insert))

    if total_leidos <= 0:
        return {
            "success": False,
            "ok": False,
            "modo": "insercion_ejecutar",
            "estado_insercion": "excel_sin_registros",
            "mensaje": "El archivo normalizado no tiene registros para insertar.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "conexion": conexion,
            "ruta_normalizado": str(ruta_normalizado),
        }

    total_insertados = _aster_v2_h_insert_dataframe_sql(
        conexion=conexion,
        df_insert=df_insert,
        database=sql_info["database"],
        schema=sql_info["schema"],
        tabla=sql_info["tabla"],
        tamano_lote=1000,
    )

    fecha_destino_despues = _aster_v2_h_count_fecha_destino(
        conexion=conexion,
        fecha_sql=fecha_sql,
        columnas_sql=sql_info["columnas_sql"],
    )

    registros_despues = int(fecha_destino_despues.get("registros_fecha_destino") or 0)
    incremento_fecha = registros_despues - registros_antes

    estado = "correcto" if total_insertados == total_leidos else "revisar_cuadre"

    resultado = {
        "success": estado == "correcto",
        "ok": estado == "correcto",
        "modo": "insercion_ejecutar",
        "estado_insercion": estado,
        "mensaje": (
            "Inserción ASTER ejecutada correctamente."
            if estado == "correcto"
            else "Inserción ejecutada con diferencia entre registros leídos e insertados."
        ),
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "tabla_destino": f"{sql_info['database']}.{sql_info['schema']}.{sql_info['tabla']}",
        "ruta_normalizado": str(ruta_normalizado),
        "archivo_normalizado": ruta_normalizado.name,
        "total_leidos": total_leidos,
        "total_insertados": int(total_insertados),
        "incremento_fecha_destino": int(incremento_fecha),
        "columnas_insertadas": list(df_insert.columns),
        "total_columnas_insertadas": len(df_insert.columns),
        "fecha_destino_antes": fecha_destino_antes,
        "fecha_destino_despues": fecha_destino_despues,
        "ruta_cache_preparacion": str(_aster_v2_h_prepare_cache_path(fecha_yyyymmdd)),
    }

    ruta_resultado = _aster_v2_h_resultado_insercion_path(fecha_yyyymmdd)
    resultado["ruta_resultado_insercion"] = str(ruta_resultado)
    resultado["generado_en"] = datetime.now().isoformat(timespec="seconds")

    ruta_resultado.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return resultado

# === ASTER_V2_FASE_H2_EJECUTAR_INSERCION_END ===


# === ASTER_V2_FASE_I_REPORTE_FINAL_BEGIN ===

def _aster_v2_i_base_directa(fecha_yyyymmdd: str) -> Path:
    if "_aster_v2_h_base_directa" in globals():
        return _aster_v2_h_base_directa(fecha_yyyymmdd)

    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_i_reporte_dir(fecha_yyyymmdd: str) -> Path:
    carpeta = _aster_v2_i_base_directa(fecha_yyyymmdd) / "Reporte"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_i_find_one(carpeta: Path, patrones: list[str]) -> Path | None:
    candidatos = []

    if carpeta.exists():
        for patron in patrones:
            candidatos.extend(list(carpeta.glob(patron)))

    candidatos = sorted(set(candidatos), key=lambda p: p.stat().st_mtime, reverse=True)

    return candidatos[0] if candidatos else None


def _aster_v2_i_read_json(path: Path | None) -> dict:
    import json

    if not path or not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _aster_v2_i_excel_count(path: Path | None) -> dict:
    import openpyxl

    if not path or not path.exists():
        return {
            "existe": False,
            "ruta": str(path or ""),
            "archivo": path.name if path else "",
            "registros": 0,
            "columnas": 0,
            "hoja": "",
        }

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    result = {
        "existe": True,
        "ruta": str(path),
        "archivo": path.name,
        "registros": max(int(ws.max_row or 1) - 1, 0),
        "columnas": int(ws.max_column or 0),
        "hoja": ws.title,
    }

    wb.close()
    return result


def _aster_v2_i_archivo_row(tipo: str, path: Path | None) -> dict:
    existe = bool(path and path.exists())

    return {
        "Tipo": tipo,
        "Archivo": path.name if path else "",
        "Existe": "Sí" if existe else "No",
        "Ruta": str(path or ""),
        "Tamaño_bytes": path.stat().st_size if existe else 0,
    }


def _accion_aster_reporte_final_v2(fecha: str, conexion: str) -> dict:
    """
    Fase I / Cierre:
    Genera reporte final ASTER en Excel.

    No inserta ni modifica bases de datos.
    """
    import pandas as pd
    import json
    from datetime import datetime

    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    base = _aster_v2_i_base_directa(fecha_yyyymmdd)
    carpeta_original = base / "Archivo_Original"
    carpeta_normalizado = base / "Normalizado"
    carpeta_entidades = base / "Entidades"
    carpeta_reporte = _aster_v2_i_reporte_dir(fecha_yyyymmdd)

    archivo_original = _aster_v2_i_find_one(
        carpeta_original,
        [f"*{fecha_yyyymmdd}*.xlsx", "*.xlsx"],
    )

    archivo_normalizado = _aster_v2_i_find_one(
        carpeta_normalizado,
        [f"*{fecha_yyyymmdd}*normalizado*.xlsx", "*normalizado*.xlsx", "*.xlsx"],
    )

    archivo_entidades = carpeta_entidades / f"entidades_aster_{fecha_yyyymmdd}.xlsx"
    archivo_excluidas = carpeta_entidades / f"exclu_entidades_aster_{fecha_yyyymmdd}.xlsx"
    json_validacion = carpeta_entidades / f"validacion_entidades_aster_{fecha_yyyymmdd}.json"
    json_preparacion_h = carpeta_entidades / f"preparacion_insercion_aster_{fecha_yyyymmdd}.json"
    json_resultado_h = carpeta_entidades / f"resultado_insercion_aster_{fecha_yyyymmdd}.json"

    validacion = _aster_v2_i_read_json(json_validacion)
    prep_h = _aster_v2_i_read_json(json_preparacion_h)
    res_h = _aster_v2_i_read_json(json_resultado_h)

    # Ejecutar validación G en memoria para que el reporte refleje estado actual.
    try:
        conciliacion = _accion_aster_conciliacion_validar_v2(fecha, conexion)
    except Exception as exc:
        conciliacion = {
            "success": False,
            "estado_validacion": "error",
            "mensaje": str(exc),
            "resumen": {},
            "kpis": {},
            "errores": [{"tipo": "error_conciliacion", "mensaje": str(exc)}],
        }

    original_info = _aster_v2_i_excel_count(archivo_original)
    normalizado_info = _aster_v2_i_excel_count(archivo_normalizado)
    entidades_info = _aster_v2_i_excel_count(archivo_entidades)
    excluidas_info = _aster_v2_i_excel_count(archivo_excluidas)

    archivos = [
        _aster_v2_i_archivo_row("Archivo original", archivo_original),
        _aster_v2_i_archivo_row("Archivo normalizado", archivo_normalizado),
        _aster_v2_i_archivo_row("Entidades clasificadas", archivo_entidades),
        _aster_v2_i_archivo_row("Entidades excluidas", archivo_excluidas),
        _aster_v2_i_archivo_row("Cache validación D-E", json_validacion),
        _aster_v2_i_archivo_row("Cache preparación H", json_preparacion_h),
        _aster_v2_i_archivo_row("Resultado inserción H", json_resultado_h),
    ]

    fases = []

    def add_fase(fase, estado, mensaje, ruta=""):
        fases.append({
            "Fase": fase,
            "Estado": estado,
            "Mensaje": mensaje,
            "Ruta": ruta,
        })

    add_fase(
        "A/B - Archivo ASTER",
        "correcto" if archivo_original and archivo_original.exists() else "revisar",
        "Archivo original localizado." if archivo_original and archivo_original.exists() else "No se encontró archivo original.",
        str(archivo_original or ""),
    )

    add_fase(
        "C - Normalización",
        "correcto" if archivo_normalizado and archivo_normalizado.exists() else "revisar",
        "Archivo normalizado localizado." if archivo_normalizado and archivo_normalizado.exists() else "No se encontró archivo normalizado.",
        str(archivo_normalizado or ""),
    )

    add_fase(
        "D-E - Validación entidades",
        "correcto" if json_validacion.exists() else "revisar",
        "Cache de validación localizado." if json_validacion.exists() else "No se encontró cache de validación.",
        str(json_validacion),
    )

    add_fase(
        "F - Clasificación entidades",
        "correcto" if archivo_entidades.exists() and archivo_excluidas.exists() else "revisar",
        "Archivos de entidades localizados." if archivo_entidades.exists() and archivo_excluidas.exists() else "Faltan archivos de entidades.",
        str(carpeta_entidades),
    )

    add_fase(
        "G - Conciliación",
        conciliacion.get("estado_validacion") or ("correcto" if conciliacion.get("success") else "revisar"),
        conciliacion.get("mensaje") or "",
        str(carpeta_entidades),
    )

    estado_h = (
        res_h.get("estado_insercion")
        or prep_h.get("estado_preparacion")
        or "sin_ejecutar"
    )

    mensaje_h = (
        res_h.get("mensaje")
        or prep_h.get("mensaje")
        or "No se encontró resultado de inserción H."
    )

    add_fase(
        "H - Inserción",
        estado_h,
        mensaje_h,
        str(json_resultado_h if json_resultado_h.exists() else json_preparacion_h),
    )

    observaciones = []

    for item in fases:
        estado = str(item.get("Estado", "")).lower()

        if estado not in {"correcto", "ok"}:
            observaciones.append({
                "Tipo": "fase_revisar",
                "Detalle": item.get("Fase", ""),
                "Mensaje": item.get("Mensaje", ""),
            })

    for err in conciliacion.get("errores") or []:
        observaciones.append({
            "Tipo": err.get("tipo", "observacion_conciliacion"),
            "Detalle": err.get("mensaje", ""),
            "Mensaje": json.dumps(err, ensure_ascii=False, default=str),
        })

    if res_h.get("bloqueado_por_fecha") or prep_h.get("bloqueado_por_fecha"):
        observaciones.append({
            "Tipo": "bloqueo_fecha",
            "Detalle": "Ya existen datos para la fecha de proceso.",
            "Mensaje": res_h.get("mensaje") or prep_h.get("mensaje") or "",
        })

    total_insertados = int(res_h.get("total_insertados") or 0)
    total_leidos = int(res_h.get("total_leidos") or 0)

    estado_general = "correcto"

    if observaciones:
        estado_general = "revisar"

    if res_h and not res_h.get("ok"):
        estado_general = "revisar"

    resumen = {
        "Fecha_proceso": fecha_yyyymmdd,
        "Fecha_sql": fecha_sql,
        "Conexion": conexion,
        "Estado_general": estado_general,
        "Archivo_original": original_info.get("archivo", ""),
        "Registros_original": original_info.get("registros", 0),
        "Archivo_normalizado": normalizado_info.get("archivo", ""),
        "Registros_normalizado": normalizado_info.get("registros", 0),
        "Entidades_clasificadas": entidades_info.get("registros", 0),
        "Entidades_excluidas": excluidas_info.get("registros", 0),
        "Estado_G": conciliacion.get("estado_validacion", ""),
        "Estado_H": estado_h,
        "Total_leidos_H": total_leidos,
        "Total_insertados_H": total_insertados,
        "Resultado_insercion": str(json_resultado_h if json_resultado_h.exists() else ""),
        "Carpeta_reporte": str(carpeta_reporte),
    }

    ruta_reporte = carpeta_reporte / f"reporte_final_aster_{fecha_yyyymmdd}.xlsx"

    df_resumen = pd.DataFrame([{"Concepto": k, "Valor": v} for k, v in resumen.items()])
    df_fases = pd.DataFrame(fases)
    df_archivos = pd.DataFrame(archivos)
    df_observaciones = pd.DataFrame(observaciones or [{"Tipo": "sin_observaciones", "Detalle": "Sin observaciones críticas.", "Mensaje": ""}])

    with pd.ExcelWriter(ruta_reporte, engine="openpyxl") as writer:
        df_resumen.to_excel(writer, index=False, sheet_name="Resumen")
        df_fases.to_excel(writer, index=False, sheet_name="Fases")
        df_archivos.to_excel(writer, index=False, sheet_name="Archivos")
        df_observaciones.to_excel(writer, index=False, sheet_name="Observaciones")

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 60)

    resultado_json = carpeta_reporte / f"reporte_final_aster_{fecha_yyyymmdd}.json"

    resultado = {
        "success": True,
        "ok": True,
        "modo": "reporte_final_aster",
        "mensaje": "Reporte final ASTER generado correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "estado_general": estado_general,
        "resumen": resumen,
        "fases": fases,
        "archivos": archivos + [_aster_v2_i_archivo_row("Reporte final Excel", ruta_reporte)],
        "observaciones": observaciones,
        "ruta_reporte_excel": str(ruta_reporte),
        "ruta_reporte_json": str(resultado_json),
        "carpeta_reporte": str(carpeta_reporte),
    }

    resultado_json.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return resultado

# === ASTER_V2_FASE_I_REPORTE_FINAL_END ===


# === ASTER_V2_FASE_B_CARPETAS_BEGIN ===

def _aster_v2_b_fecha_from_args(args, kwargs):
    for key in ["fecha", "fecha_proceso", "fecha_yyyymmdd"]:
        value = kwargs.get(key)
        if value:
            return _fecha_yyyymmdd(str(value))

    for value in args:
        text = str(value or "")
        if text and any(ch.isdigit() for ch in text):
            try:
                return _fecha_yyyymmdd(text)
            except Exception:
                pass

    return ""


def _aster_v2_b_base_directa(fecha_yyyymmdd):
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if not str(base):
        raise RuntimeError("No se pudo determinar la carpeta base ASTER.")

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_b_ensure_carpetas(fecha_yyyymmdd):
    base = _aster_v2_b_base_directa(fecha_yyyymmdd)

    nombres = [
        "Archivo_Original",
        "Normalizado",
        "Gestion",
        "Entidades",
        "Reportes",
    ]

    carpetas = []

    for nombre in nombres:
        ruta = base / nombre
        existia = ruta.exists()
        ruta.mkdir(parents=True, exist_ok=True)

        carpetas.append({
            "carpeta": nombre,
            "ruta": str(ruta),
            "estado": "Existente" if existia else "Creada",
        })

    return {
        "ruta_base_aster": str(base),
        "carpetas": carpetas,
        "carpetas_nombres": nombres,
    }


def _accion_aster_buscar_archivo_v2(*args, **kwargs):
    """
    Wrapper Fase B:
    ejecuta la lógica existente y asegura carpetas estándar:
    Archivo_Original, Normalizado, Gestion, Entidades y Reportes.
    """
    resultado = _accion_aster_buscar_archivo_v2_legacy_carpetas(*args, **kwargs)

    fecha_yyyymmdd = ""

    if isinstance(resultado, dict):
        fecha_yyyymmdd = (
            resultado.get("fecha_yyyymmdd")
            or resultado.get("fecha_proceso")
            or resultado.get("fecha")
            or ""
        )

    if not fecha_yyyymmdd:
        fecha_yyyymmdd = _aster_v2_b_fecha_from_args(args, kwargs)

    fecha_yyyymmdd = _fecha_yyyymmdd(str(fecha_yyyymmdd))

    info = _aster_v2_b_ensure_carpetas(fecha_yyyymmdd)

    if isinstance(resultado, dict):
        resultado["fecha_yyyymmdd"] = fecha_yyyymmdd
        resultado["fecha_proceso"] = fecha_yyyymmdd
        resultado["ruta_base_aster"] = info["ruta_base_aster"]
        resultado["carpetas_proceso"] = info["carpetas"]
        resultado["carpetas_creadas"] = info["carpetas"]
        resultado["carpetas_nombres"] = info["carpetas_nombres"]

        # Para visual compacto de Fase B.
        if "archivo" not in resultado:
            archivo = (
                resultado.get("nombre_archivo")
                or resultado.get("archivo_after")
                or resultado.get("archivo_aster")
                or resultado.get("nombre")
                or ""
            )
            resultado["archivo"] = archivo

    return resultado

# === ASTER_V2_FASE_B_CARPETAS_END ===


# === ASTER_V2_FASE_C_COLUMNAS_MODIFICADAS_BEGIN ===

def _aster_v2_c_visual_fecha_from_args(args, kwargs, resultado=None):
    resultado = resultado or {}

    for key in ["fecha_yyyymmdd", "fecha_proceso", "fecha"]:
        value = resultado.get(key)
        if value:
            return _fecha_yyyymmdd(str(value))

    for key in ["fecha", "fecha_proceso", "fecha_yyyymmdd"]:
        value = kwargs.get(key)
        if value:
            return _fecha_yyyymmdd(str(value))

    for value in args:
        text = str(value or "")
        nums = "".join(ch for ch in text if ch.isdigit())

        if len(nums) >= 8:
            return _fecha_yyyymmdd(nums[:8])

    return ""


def _aster_v2_c_visual_base(fecha_yyyymmdd):
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_c_visual_find_original(fecha_yyyymmdd, resultado=None):
    resultado = resultado or {}

    for key in ["ruta_archivo", "ruta_origen", "archivo_origen", "ruta_after", "ruta_original"]:
        value = resultado.get(key)

        if value:
            p = Path(str(value))

            if p.exists():
                return p

    carpeta = _aster_v2_c_visual_base(fecha_yyyymmdd) / "Archivo_Original"

    candidatos = []

    if carpeta.exists():
        for patron in [f"*{fecha_yyyymmdd}*.xlsx", f"After{fecha_yyyymmdd}.xlsx", "*.xlsx"]:
            candidatos.extend(list(carpeta.glob(patron)))

    candidatos = sorted(set(candidatos), key=lambda p: p.stat().st_mtime, reverse=True)

    return candidatos[0] if candidatos else None


def _aster_v2_c_visual_find_normalizado(fecha_yyyymmdd, resultado=None):
    resultado = resultado or {}

    for key in ["ruta_normalizado", "ruta_normalizada", "ruta_normalizado_xlsx"]:
        value = resultado.get(key)

        if value:
            p = Path(str(value))

            if p.exists():
                return p

    carpeta = _aster_v2_c_visual_base(fecha_yyyymmdd) / "Normalizado"

    candidatos = []

    if carpeta.exists():
        for patron in [
            f"*{fecha_yyyymmdd}*normalizado*.xlsx",
            f"*{fecha_yyyymmdd}*Normalizado*.xlsx",
            "*normalizado*.xlsx",
            "*Normalizado*.xlsx",
            "*.xlsx",
        ]:
            candidatos.extend(list(carpeta.glob(patron)))

    candidatos = sorted(set(candidatos), key=lambda p: p.stat().st_mtime, reverse=True)

    return candidatos[0] if candidatos else None


def _aster_v2_c_visual_headers(path):
    import openpyxl

    if not path or not Path(path).exists():
        return []

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    headers = []

    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        headers.append("" if cell.value is None else str(cell.value).strip())

    wb.close()

    return headers


def _aster_v2_c_visual_count_excel(path):
    import openpyxl

    if not path or not Path(path).exists():
        return {
            "total_columnas": 0,
            "total_registros": 0,
            "hoja": "",
        }

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    info = {
        "total_columnas": int(ws.max_column or 0),
        "total_registros": max(int(ws.max_row or 1) - 1, 0),
        "hoja": ws.title,
    }

    wb.close()

    return info


def _aster_v2_c_visual_columnas_modificadas(original_path, normalizado_path):
    headers_original = _aster_v2_c_visual_headers(original_path)
    headers_normalizado = _aster_v2_c_visual_headers(normalizado_path)

    total = max(len(headers_original), len(headers_normalizado))
    modificadas = []
    detalle = []
    sin_cambio = 0

    for i in range(total):
        original = headers_original[i] if i < len(headers_original) else ""
        normalizado = headers_normalizado[i] if i < len(headers_normalizado) else ""

        cambio = original != normalizado
        estado = "Modificada" if cambio else "Sin cambio"

        row = {
            "nro": i + 1,
            "posicion": i + 1,
            "original": original,
            "normalizado": normalizado,
            "estado": estado,
            "modificada": cambio,
        }

        detalle.append(row)

        if cambio:
            modificadas.append(row)
        else:
            sin_cambio += 1

    return {
        "columnas_modificadas": len(modificadas),
        "columnas_sin_cambio": sin_cambio,
        "detalle_columnas_modificadas": modificadas,
        "detalle_columnas_normalizacion": detalle,
    }

def _accion_aster_normalizar_encabezados_v2(*args, **kwargs):
    """
    Wrapper visual Fase C:
    mantiene la lógica actual y agrega:
    - columnas_modificadas
    - detalle_columnas_normalizacion
    - carpeta_normalizado_correcta
    - archivo_normalizado
    """
    resultado = _accion_aster_normalizar_encabezados_v2_visual_source(*args, **kwargs)

    if not isinstance(resultado, dict):
        return resultado

    fecha_yyyymmdd = _aster_v2_c_visual_fecha_from_args(args, kwargs, resultado)

    original_path = _aster_v2_c_visual_find_original(fecha_yyyymmdd, resultado)
    normalizado_path = _aster_v2_c_visual_find_normalizado(fecha_yyyymmdd, resultado)

    conteo = _aster_v2_c_visual_count_excel(normalizado_path)
    cambios = _aster_v2_c_visual_columnas_modificadas(original_path, normalizado_path)

    resultado["fecha_yyyymmdd"] = fecha_yyyymmdd
    resultado["fecha_proceso"] = fecha_yyyymmdd
    resultado["archivo_normalizado"] = normalizado_path.name if normalizado_path else ""
    resultado["ruta_normalizado"] = str(normalizado_path or resultado.get("ruta_normalizado") or "")
    resultado["carpeta_normalizado_correcta"] = str(Path(normalizado_path).parent) if normalizado_path else ""
    resultado["total_columnas"] = conteo.get("total_columnas", resultado.get("total_columnas", 0))
    resultado["total_registros"] = conteo.get("total_registros", resultado.get("total_registros", 0))

    resultado["columnas_modificadas"] = cambios["columnas_modificadas"]
    resultado["columnas_normalizadas_modificadas"] = cambios["columnas_modificadas"]
    resultado["columnas_sin_cambio"] = cambios["columnas_sin_cambio"]
    resultado["detalle_columnas_modificadas"] = cambios["detalle_columnas_modificadas"]
    resultado["detalle_columnas_normalizacion"] = cambios["detalle_columnas_normalizacion"]

    return resultado

# === ASTER_V2_FASE_C_COLUMNAS_MODIFICADAS_END ===


# === ASTER_V2_FASE_I_GENERAR_GESTION_BEGIN ===

def _aster_v2_i_fecha_yyyymmdd_from_sql(fecha_sql: str) -> str:
    txt = str(fecha_sql or "").strip()
    if "-" in txt:
        return txt.replace("-", "")[:8]
    return _fecha_yyyymmdd(txt)


def _aster_v2_i_base_directa_gestion(fecha_yyyymmdd: str) -> Path:
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_i_gestion_dir(fecha_yyyymmdd: str) -> Path:
    carpeta = _aster_v2_i_base_directa_gestion(fecha_yyyymmdd) / "Gestion"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_i_find_aster_nota_gestion_sql() -> Path | None:
    from pathlib import Path

    try:
        root = Path(__file__).resolve().parents[2]
    except Exception:
        root = Path.cwd()

    preferidos = [
        root / "app" / "sql" / "aster" / "gestion" / "Aster_Nota_Gestion.txt",
        root / "app" / "sql" / "aster" / "gestion" / "export_gestion_aster.sql",
        root / "app" / "sql" / "Aster_Nota_Gestion.txt",
        root / "app" / "sql" / "Aster_Nota_Gestion.sql",
    ]

    for path in preferidos:
        if path.exists():
            return path

    app_sql = root / "app" / "sql"

    nombres_preferidos = {
        "aster_nota_gestion.txt",
        "aster_nota_gestion.sql",
        "export_gestion_aster.sql",
    }

    if app_sql.exists():
        encontrados = [
            p for p in app_sql.rglob("*")
            if p.is_file() and p.name.lower() in nombres_preferidos
        ]

        if encontrados:
            encontrados.sort(
                key=lambda p: (
                    0 if "aster" in [x.lower() for x in p.parts] and "gestion" in [x.lower() for x in p.parts] else 1,
                    0 if p.name.lower() == "aster_nota_gestion.txt" else 1,
                    -p.stat().st_mtime,
                )
            )
            return encontrados[0]

    return None

def _aster_v2_i_prepare_sql_gestion(sql: str, fecha_sql: str, fecha_yyyymmdd: str) -> str:
    import re
    from datetime import datetime, timedelta

    sql = str(sql or "")

    fecha_sql = str(fecha_sql or "").strip()
    fecha_yyyymmdd = str(fecha_yyyymmdd or "").strip()

    # 1) Reemplazos explícitos si el script usa placeholders.
    replacements = {
        "{{fecha_sql}}": fecha_sql,
        "{fecha_sql}": fecha_sql,
        "@FECHA_SQL@": fecha_sql,
        "@fecha_sql@": fecha_sql,
        ":fecha_sql": "'" + fecha_sql.replace("'", "''") + "'",
        "{{fecha_yyyymmdd}}": fecha_yyyymmdd,
        "{fecha_yyyymmdd}": fecha_yyyymmdd,
        "@FECHA_YYYYMMDD@": fecha_yyyymmdd,
        "@fecha_yyyymmdd@": fecha_yyyymmdd,
        ":fecha_yyyymmdd": "'" + fecha_yyyymmdd.replace("'", "''") + "'",
    }

    for key, value in replacements.items():
        sql = sql.replace(key, value)

    # 2) Si el script corregido trae fecha hardcodeada, reemplazarla por la fecha del proceso.
    fecha_lit = "'" + fecha_sql.replace("'", "''") + "'"

    sql = re.sub(
        r"DECLARE\s+@Fecha\s+DATE\s*=\s*'[^']*'\s*;",
        f"DECLARE @Fecha DATE = {fecha_lit};",
        sql,
        flags=re.IGNORECASE,
    )

    # 3) Quitar GO y USE. La conexión ya apunta a Aster_Api.
    lines = []

    for line in sql.splitlines():
        stripped = line.strip()

        if stripped.upper() == "GO":
            continue

        if re.match(r"^USE\s+\[?Aster_Api\]?", stripped, flags=re.IGNORECASE):
            continue

        lines.append(line)

    sql = "\n".join(lines).strip()

    # 4) Si algún script antiguo tiene ?:
    #    se reemplaza secuencialmente fecha_inicio, fecha_fin, fecha_inicio, fecha_fin.
    if "?" in sql:
        dt_inicio = datetime.strptime(fecha_sql, "%Y-%m-%d")
        fecha_fin = (dt_inicio + timedelta(days=1)).strftime("%Y-%m-%d")

        valores = [
            "'" + fecha_sql.replace("'", "''") + "'",
            "'" + fecha_fin.replace("'", "''") + "'",
        ]

        contador = 0

        def repl(_):
            nonlocal contador
            value = valores[contador % 2]
            contador += 1
            return value

        sql = re.sub(r"\?", repl, sql)

    return sql

def _aster_v2_i_norm_col(value: str) -> str:
    import re
    import unicodedata

    txt = str(value or "").strip().lower()
    txt = "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )
    txt = re.sub(r"[^a-z0-9]+", "", txt)
    return txt

def _aster_v2_i_find_col(df, opciones: list[str]) -> str | None:
    mapa = {_aster_v2_i_norm_col(c): c for c in df.columns}

    for opcion in opciones:
        key = _aster_v2_i_norm_col(opcion)
        if key in mapa:
            return mapa[key]

    for col in df.columns:
        n = _aster_v2_i_norm_col(col)
        if all(_aster_v2_i_norm_col(x) in n for x in opciones[:1]):
            return col

    return None


def _aster_v2_i_limpiar_gestion_df(df):
    import pandas as pd
    import re
    import unicodedata

    df = df.copy()

    col_desc = _aster_v2_i_find_col(
        df,
        [
            "Descripcion Codigo De Gestion",
            "Descripción Codigo de gestión",
            "Descripcion Codigo de gestion",
            "Descripcion_Codigo_De_Gestion",
            "descripcion_codigo_gestion",
        ],
    )

    col_fecha = _aster_v2_i_find_col(
        df,
        [
            "Fecha_Compromiso",
            "Fecha Compromiso",
            "fecha_compromiso",
        ],
    )

    def normalizar_texto(value):
        txt = "" if pd.isna(value) else str(value)
        txt = txt.strip()
        txt = "".join(
            c for c in unicodedata.normalize("NFD", txt)
            if unicodedata.category(c) != "Mn"
        )
        txt = re.sub(r"\s+", " ", txt)
        return txt.lower()

    resumen = {
        "columna_descripcion": col_desc or "",
        "columna_fecha_compromiso": col_fecha or "",
        "total_registros": int(len(df)),
        "regla_fecha_compromiso": 'Solo conserva fecha si Descripcion Codigo De Gestion inicia con "Acuerdo de"',
        "acuerdos_inicio_total": 0,
        "acuerdos_inicio_con_fecha": 0,
        "acuerdos_inicio_sin_fecha": 0,
        "no_acuerdos_fecha_vaciada": 0,
        "nulls_reemplazados": 0,
    }

    nulls_antes = int(df.isna().sum().sum())

    if col_desc and col_fecha:
        desc_norm = df[col_desc].map(normalizar_texto)

        # Regla corregida:
        # Solo los registros cuya descripción INICIA con "Acuerdo de" conservan Fecha_Compromiso.
        mask_acuerdo_inicio = desc_norm.str.startswith("acuerdo de", na=False)

        fecha_txt = df[col_fecha].astype(str).fillna("").str.strip()
        fecha_vacia = fecha_txt.str.lower().isin({"", "nan", "nat", "none", "null"})

        resumen["acuerdos_inicio_total"] = int(mask_acuerdo_inicio.sum())
        resumen["acuerdos_inicio_con_fecha"] = int((mask_acuerdo_inicio & ~fecha_vacia).sum())
        resumen["acuerdos_inicio_sin_fecha"] = int((mask_acuerdo_inicio & fecha_vacia).sum())

        no_acuerdo_con_fecha = (~mask_acuerdo_inicio) & (~fecha_vacia)
        resumen["no_acuerdos_fecha_vaciada"] = int(no_acuerdo_con_fecha.sum())

        # Si NO inicia con "Acuerdo de", Fecha_Compromiso debe quedar vacía.
        df.loc[~mask_acuerdo_inicio, col_fecha] = ""

    # Reemplazar NULL/NaN/NaT/None por vacío.
    df = df.where(pd.notnull(df), "")

    for col in df.columns:
        df[col] = df[col].map(
            lambda x: "" if str(x).strip().lower() in {"null", "none", "nan", "nat"} else x
        )

    resumen["nulls_reemplazados"] = nulls_antes

    return df, resumen

def _aster_v2_i_exportar_gestion_aster(fecha_sql: str, conexion: str = "local") -> dict:
    import pandas as pd
    import pyodbc
    import json
    from datetime import datetime

    fecha_yyyymmdd = _aster_v2_i_fecha_yyyymmdd_from_sql(fecha_sql)

    sql_path = _aster_v2_i_find_aster_nota_gestion_sql()

    if not sql_path:
        return {
            "ok": False,
            "success": False,
            "modo": "gestion_aster_export",
            "mensaje": "No se encontró Aster_Nota_Gestion.txt dentro de app/sql ni en rutas alternativas.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
        }

    sql_raw = sql_path.read_text(encoding="utf-8", errors="ignore")
    sql = _aster_v2_i_prepare_sql_gestion(sql_raw, fecha_sql, fecha_yyyymmdd)

    if not sql.strip():
        return {
            "ok": False,
            "success": False,
            "modo": "gestion_aster_export",
            "mensaje": f"El script SQL está vacío o no pudo prepararse: {sql_path}",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
            "sql_usado": str(sql_path),
        }

    cfg = _sql_remoto_destino() if str(conexion).lower() == "remoto" else _sql_local_destino()

    cfg = dict(cfg)
    cfg["database"] = "Aster_Api"
    cfg["bd"] = "Aster_Api"

    cadena = _conn_str_sqlserver_aster_v2(cfg)

    with pyodbc.connect(cadena, timeout=120) as conn:
        cur = conn.cursor()
        cur.execute(sql)

        # Soporta SET/DECLARE/UPDATE/CTE antes del SELECT final.
        while cur.description is None:
            if not cur.nextset():
                raise RuntimeError(
                    "Aster_Nota_Gestion.txt se ejecutó, pero no devolvió un SELECT final."
                )

        columnas = [item[0] for item in cur.description]
        filas = cur.fetchall()

    df = pd.DataFrame.from_records(filas, columns=columnas)

    total_sql = int(len(df))

    df_limpio, resumen_limpieza = _aster_v2_i_limpiar_gestion_df(df)

    carpeta_gestion = _aster_v2_i_gestion_dir(fecha_yyyymmdd)
    ruta_excel = carpeta_gestion / f"{fecha_yyyymmdd}_Gestion_aster.xlsx"
    ruta_json = carpeta_gestion / f"{fecha_yyyymmdd}_Gestion_aster.json"
    ruta_sql_preparado = carpeta_gestion / f"{fecha_yyyymmdd}_Aster_Nota_Gestion_preparado.sql"

    ruta_sql_preparado.write_text(sql, encoding="utf-8")

    with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:
        df_limpio.to_excel(writer, index=False, sheet_name="Gestion_ASTER")

        resumen_df = pd.DataFrame(
            [{"Concepto": k, "Valor": v} for k, v in resumen_limpieza.items()]
        )
        resumen_df.to_excel(writer, index=False, sheet_name="Resumen")

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                letra = col[0].column_letter
                max_len = 0
                for cell in col:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[letra].width = min(max(max_len + 2, 12), 55)

    resultado = {
        "ok": True,
        "success": True,
        "modo": "gestion_aster_export",
        "mensaje": "Gestión ASTER exportada correctamente.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "base": "Aster_Api",
        "sql_usado": str(sql_path),
        "sql_preparado": str(ruta_sql_preparado),
        "carpeta_gestion": str(carpeta_gestion),
        "archivo_gestion": ruta_excel.name,
        "ruta_gestion_excel": str(ruta_excel),
        "ruta_gestion_json": str(ruta_json),
        "total_registros_sql": total_sql,
        "total_registros_exportados": int(len(df_limpio)),
        "resumen_limpieza": resumen_limpieza,
        "generado_en": datetime.now().isoformat(timespec="seconds"),
    }

    ruta_json.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return resultado

def _ejecutar_fase_i_local_sqlserver_v2(fecha_sql: str) -> dict:
    """
    Ejecuta únicamente usuarios y comentarios/gestiones base.
    La exportación del Excel Gestión ASTER queda separada en el botón:
    Generar Gestión ASTER.
    """
    resultado = _ejecutar_fase_i_local_sqlserver_v2_sin_gestion(fecha_sql)

    if isinstance(resultado, dict):
        resultado["gestion_generada"] = False
        resultado["gestion_aster"] = {
            "ok": None,
            "mensaje": "Gestión ASTER no se genera en este botón. Use Generar Gestión ASTER.",
        }

        mensaje = str(resultado.get("mensaje") or "").strip()

        if "Gestión ASTER pendiente" not in mensaje:
            resultado["mensaje"] = (
                mensaje
                + " Gestión ASTER pendiente: use el botón Generar Gestión ASTER."
            ).strip()

    return resultado

# === ASTER_V2_FASE_I_GENERAR_GESTION_END ===


# === ASTER_V2_FASE_I_BOTON_GENERAR_GESTION_ROBUSTO_BEGIN ===

def _accion_aster_fase_i_generar_gestion_v2(fecha, conexion="local"):
    """
    Genera exclusivamente el archivo Gestión ASTER.
    No inserta usuarios.
    No inserta comentarios.
    """
    from datetime import datetime

    fecha_yyyymmdd = _fecha_yyyymmdd(str(fecha))
    fecha_sql = _fecha_sql(fecha_yyyymmdd)

    if "_aster_v2_i_exportar_gestion_aster" not in globals():
        return {
            "ok": False,
            "success": False,
            "modo": "gestion_aster_export",
            "mensaje": "No existe la función _aster_v2_i_exportar_gestion_aster. Revise los patches de Gestión ASTER.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
        }

    resultado = _aster_v2_i_exportar_gestion_aster(fecha_sql, conexion=conexion)

    if not isinstance(resultado, dict):
        resultado = {
            "ok": False,
            "success": False,
            "modo": "gestion_aster_export",
            "mensaje": "La exportación de Gestión ASTER no devolvió un resultado válido.",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "fecha_sql": fecha_sql,
        }

    resumen = resultado.get("resumen_limpieza") or {}

    kpis = {
        "total_registros_sql": int(resultado.get("total_registros_sql") or 0),
        "total_registros_exportados": int(resultado.get("total_registros_exportados") or 0),
        "acuerdos_inicio_total": int(resumen.get("acuerdos_inicio_total") or resumen.get("acuerdos_total") or 0),
        "acuerdos_inicio_con_fecha": int(resumen.get("acuerdos_inicio_con_fecha") or resumen.get("acuerdos_con_fecha") or 0),
        "acuerdos_inicio_sin_fecha": int(resumen.get("acuerdos_inicio_sin_fecha") or resumen.get("acuerdos_sin_fecha") or 0),
        "fechas_compromiso_vaciadas": int(resumen.get("no_acuerdos_fecha_vaciada") or 0),
        "nulls_reemplazados": int(resumen.get("nulls_reemplazados") or 0),
    }

    resultado["kpis"] = kpis
    resultado["fecha_yyyymmdd"] = fecha_yyyymmdd
    resultado["fecha_sql"] = fecha_sql
    resultado["accion_independiente"] = True
    resultado["generado_en"] = datetime.now().isoformat(timespec="seconds")

    return resultado


def _aster_v2_extraer_accion_fecha_conexion(args, kwargs):
    accion = kwargs.get("accion")
    fecha = kwargs.get("fecha") or kwargs.get("fecha_proceso") or kwargs.get("fecha_yyyymmdd")
    conexion = kwargs.get("conexion") or "local"

    for arg in args:
        if isinstance(arg, dict):
            accion = accion or arg.get("accion")
            fecha = fecha or arg.get("fecha") or arg.get("fecha_proceso") or arg.get("fecha_yyyymmdd")
            conexion = arg.get("conexion") or conexion

    if not accion and len(args) >= 1 and isinstance(args[0], str):
        accion = args[0]

    if not fecha and len(args) >= 2:
        fecha = args[1]

    if len(args) >= 3 and args[2]:
        conexion = args[2]

    if not fecha:
        fecha = datetime.now().strftime("%Y%m%d")

    return str(accion or ""), str(fecha), str(conexion or "local")


def _aster_v2_result_generico_accion(nombre, accion, fecha, conexion, resultado):
    ok = bool(resultado.get("ok") or resultado.get("success"))

    comunes = {
        "accion": accion,
        "fecha": fecha,
        "fecha_proceso": _fecha_yyyymmdd(str(fecha)),
        "conexion": conexion,
    }

    if "_safe_result" in globals():
        try:
            return _safe_result(comunes, nombre, resultado)
        except Exception:
            pass

    return {
        "ok": ok,
        "success": ok,
        "estado": "correcto" if ok else "error",
        "mensaje": resultado.get("mensaje", ""),
        "accion": accion,
        "fecha_proceso": comunes["fecha_proceso"],
        "conexion": conexion,
        "resultado": resultado,
    }

# === ASTER_V2_FASE_I_BOTON_GENERAR_GESTION_ROBUSTO_END ===

def ejecutar_accion_aster_v2(*args, **kwargs):
    accion, fecha, conexion = _aster_v2_extraer_accion_fecha_conexion(args, kwargs)

    if accion in {"aster.fase.i.gestion", "aster.gestion.generar", "aster.generar.gestion.aster"}:
        resultado = _accion_aster_fase_i_generar_gestion_v2(fecha, conexion)
        return _aster_v2_result_generico_accion(
            "Generar Gestión ASTER",
            accion,
            fecha,
            conexion,
            resultado,
        )

    return _ejecutar_accion_aster_v2_before_gestion_btn(*args, **kwargs)

def _ejecutar_accion_aster_v2_before_gestion_btn(
    accion: str,
    fecha_proceso: str,
    conexion: str = "local",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    accion = str(accion or "").strip()
    conexion = "remoto" if str(conexion).lower() == "remoto" else "local"
    fecha = _fecha_yyyymmdd(fecha_proceso)
    fecha_sql = _fecha_sql(fecha_proceso)
    payload = payload or {}

    comunes = {
        "fecha_proceso": fecha,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "data_root": get_data_root(),
        "accion": accion,
    }

    try:
        if accion == "aster.total.actual":
            resultado = _accion_aster_total_actual_v2(fecha, conexion)
            return _safe_result(comunes, "Captura del total diario ASTER", resultado)

        if accion == "aster.buscar.archivo":
            resultado = _accion_aster_buscar_archivo_v2(fecha, conexion)
            return _safe_result(comunes, "Ubicación y copia del archivo ASTER", resultado)

        if accion == "aster.normalizar.encabezados":
            resultado = _accion_aster_normalizar_encabezados_v2(fecha, conexion)
            return _safe_result(comunes, "Normalización del Excel ASTER", resultado)

        if accion == "aster.entidades.excel":
            resultado = _accion_aster_entidades_excel_v2(fecha, conexion)
            return _safe_result(comunes, "Validación de entidades del Excel ASTER", resultado)

        if accion == "aster.consulta.sql":
            resultado = _accion_aster_consulta_sql_v2(fecha, conexion)
            return _safe_result(comunes, "Conexión y consulta SQL ASTER", resultado)

        if accion == "aster.depuracion.preparar" or accion == "aster.depuracion":
            resultado = _accion_aster_depuracion_preparar_v2(fecha, conexion)
            return _safe_result(comunes, "Depuración y clasificación ASTER", resultado)

        if accion == "aster.depuracion.excluir":
            resultado = _accion_aster_depuracion_excluir_v2(fecha, conexion, payload)
            return _safe_result(comunes, "Aplicar exclusiones ASTER", resultado)

        if accion == "aster.clasificacion.guardar":
            resultado = _accion_aster_clasificacion_guardar_v2(fecha, conexion, payload)
            return _safe_result(comunes, "Guardar clasificación ASTER", resultado)

        if accion in {"aster.validacion.entidades", "aster.preparar.depuracion.validar"}:
            resultado = _accion_aster_validacion_entidades_de_v2(fecha, conexion)
            return _safe_result(comunes, "Preparar Depuración y Validación de Entidades ASTER", resultado)

        if accion in {"aster.conciliacion.validar", "aster.conciliacion", "aster.validacion.final"}:
            resultado = _accion_aster_conciliacion_validar_v2(fecha, conexion)
            return _safe_result(comunes, "Conciliación y validación ASTER", resultado)

        if accion in {"aster.reporte.final", "aster.cierre.reporte", "aster.fase.i.reporte"}:
            resultado = _accion_aster_reporte_final_v2(fecha, conexion)
            return _safe_result(comunes, "Cierre / Reporte final ASTER", resultado)

        if accion in {"aster.insercion.ejecutar", "aster.insertar.datos.ejecutar", "aster.fase.h.ejecutar"}:
            resultado = _accion_aster_insercion_ejecutar_v2(fecha, conexion, payload)
            return _safe_result(comunes, "Ejecutar inserción ASTER", resultado)

        if accion in {"aster.insercion.preparar", "aster.preparar.insercion", "aster.fase.h.preparar"}:
            resultado = _accion_aster_insercion_preparar_v2(fecha, conexion)
            return _safe_result(comunes, "Preparar inserción ASTER", resultado)

        if accion == "aster.fase.i.probar":
            if conexion == "local":
                resultado = _probar_fase_i_local_sqlserver_v2()
            else:
                resultado = probar_conexiones_fase_i_aster(
                    conexion=conexion,
                    sql_local=_sql_local_destino(),
                    sql_remoto=_sql_remoto_destino(),
                    base=ASTER_FASE_I_BASE,
                    schema=ASTER_FASE_I_SCHEMA,
                    tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
                    tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
                    db_usuarios=ASTER_MYSQL_DB_USUARIOS,
                    db_gestion=ASTER_MYSQL_DB_GESTION,
                )

            return _safe_result(comunes, "Prueba conexiones Fase I", resultado)

        if accion == "aster.fase.i.preparar":
            if conexion == "local":
                resultado = _preparar_fase_i_local_sqlserver_v2(fecha_sql)
            else:
                resultado = preparar_fase_i_aster(
                    data_dir=get_data_root(),
                    fecha_raw=fecha,
                    fecha_default=fecha,
                    conexion=conexion,
                    sql_local=_sql_local_destino(),
                    sql_remoto=_sql_remoto_destino(),
                    base=ASTER_FASE_I_BASE,
                    schema=ASTER_FASE_I_SCHEMA,
                    tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
                    tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
                    db_usuarios=ASTER_MYSQL_DB_USUARIOS,
                    db_gestion=ASTER_MYSQL_DB_GESTION,
                )

            return _safe_result(comunes, "Preparar Fase I", resultado)

        if accion == "aster.fase.i.ejecutar":
            if conexion == "local":
                resultado = _ejecutar_fase_i_local_sqlserver_v2(fecha_sql)
            else:
                resultado = ejecutar_fase_i_aster(
                    data_dir=get_data_root(),
                    fecha_raw=fecha,
                    fecha_default=fecha,
                    conexion=conexion,
                    sql_local=_sql_local_destino(),
                    sql_remoto=_sql_remoto_destino(),
                    base=ASTER_FASE_I_BASE,
                    schema=ASTER_FASE_I_SCHEMA,
                    tabla_usuarios=ASTER_FASE_I_TABLA_USUARIOS,
                    tabla_comentarios=ASTER_FASE_I_TABLA_COMENTARIOS,
                    db_usuarios=ASTER_MYSQL_DB_USUARIOS,
                    db_gestion=ASTER_MYSQL_DB_GESTION,
                )

            return _safe_result(comunes, "Ejecutar Fase I completa", resultado)

        return {
            **comunes,
            "ok": False,
            "estado": "pendiente",
            "titulo": "Acción no migrada",
            "mensaje": f"La acción {accion} todavía no está migrada en ASTER v2.",
            "resultado": {},
        }

    except Exception as exc:
        return _error_result(comunes, f"Error ejecutando {accion}", exc)
