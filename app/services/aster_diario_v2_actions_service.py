from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.services.orion_aster_config_service import (
    get_data_root,
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


def _insert_comentarios_local_v2(cur, fecha_sql: str) -> dict[str, Any]:
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

    origen_fecha_total = _count_fecha_crossdb_v2(cur, source_db, schema, tabla, source_fecha, fecha_sql)
    destino_antes_fecha = _count_fecha_crossdb_v2(cur, dest_db, schema, tabla, dest_fecha, fecha_sql)

    if destino_antes_fecha > 0:
        return {
            "ok": False,
            "bloqueado": True,
            "error": f"Ya existen {destino_antes_fecha} comentarios en destino para {fecha_sql}.",
            "origen_fecha_total": origen_fecha_total,
            "destino_antes_fecha": destino_antes_fecha,
            "columna_fecha_origen": source_fecha,
            "columna_fecha_destino": dest_fecha,
        }

    if origen_fecha_total <= 0:
        return {
            "ok": False,
            "bloqueado": True,
            "error": f"No hay comentarios origen para {fecha_sql}. No se insertó nada.",
            "origen_fecha_total": origen_fecha_total,
            "destino_antes_fecha": destino_antes_fecha,
            "columna_fecha_origen": source_fecha,
            "columna_fecha_destino": dest_fecha,
        }

    source_cols = _table_columns_sqlserver_v2(cur, source_db, schema, tabla)
    dest_cols = _table_columns_sqlserver_v2(cur, dest_db, schema, tabla)
    pares = _common_insert_columns_v2(source_cols, dest_cols)

    if not pares:
        return {"ok": False, "error": "No hay columnas comunes para insertar comentarios."}

    dest_columns = ", ".join(f"[{_qident(dest)}]" for _, dest in pares)
    source_columns = ", ".join(f"s.[{_qident(src)}]" for src, _ in pares)

    sdb = _qident(source_db)
    ddb = _qident(dest_db)
    sc = _qident(schema)
    tb = _qident(tabla)
    sfecha = _qident(source_fecha)

    sql = f"""
    INSERT INTO [{ddb}].[{sc}].[{tb}] ({dest_columns})
    SELECT {source_columns}
    FROM [{sdb}].[{sc}].[{tb}] s
    WHERE TRY_CAST(s.[{sfecha}] AS DATE) = ?
    """

    destino_antes_total = _count_table_crossdb_v2(cur, dest_db, schema, tabla)
    cur.execute(sql, fecha_sql)
    destino_despues_total = _count_table_crossdb_v2(cur, dest_db, schema, tabla)
    destino_despues_fecha = _count_fecha_crossdb_v2(cur, dest_db, schema, tabla, dest_fecha, fecha_sql)

    insertados = max(0, destino_despues_total - destino_antes_total)

    return {
        "ok": True,
        "origen_fecha_total": origen_fecha_total,
        "destino_antes_fecha": destino_antes_fecha,
        "destino_despues_fecha": destino_despues_fecha,
        "destino_antes_total": destino_antes_total,
        "destino_despues_total": destino_despues_total,
        "comentarios_insertados": insertados,
        "columnas_insertadas": len(pares),
        "columna_fecha_origen": source_fecha,
        "columna_fecha_destino": dest_fecha,
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


def _preparar_fase_i_local_sqlserver_v2(fecha_sql: str) -> dict[str, Any]:
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    try:
        import pyodbc

        cadena = _conn_str_sqlserver_aster_v2(destino_cfg)

        with pyodbc.connect(cadena, timeout=10) as conn:
            cur = conn.cursor()

            source_db = origen_cfg.get("database", "gestioncomercial_dev")
            dest_db = destino_cfg.get("database", "Aster_Api")

            origen_usuarios_total = _count_table_crossdb_v2(cur, source_db, "dbo", "usuarios")
            origen_comentarios_total = _count_table_crossdb_v2(cur, source_db, "dbo", "comentarios")
            destino_usuarios_total = _count_table_crossdb_v2(cur, dest_db, "dbo", "usuarios")
            destino_comentarios_total = _count_table_crossdb_v2(cur, dest_db, "dbo", "comentarios")

            source_fecha = _detect_fecha_column_crossdb_v2(cur, source_db, "dbo", "comentarios")
            dest_fecha = _detect_fecha_column_crossdb_v2(cur, dest_db, "dbo", "comentarios")

            comentarios_origen_fecha = (
                _count_fecha_crossdb_v2(cur, source_db, "dbo", "comentarios", source_fecha, fecha_sql)
                if source_fecha
                else 0
            )

            comentarios_destino_fecha = (
                _count_fecha_crossdb_v2(cur, dest_db, "dbo", "comentarios", dest_fecha, fecha_sql)
                if dest_fecha
                else 0
            )

            ok = bool(source_fecha and dest_fecha)

            return {
                "success": ok,
                "ok": ok,
                "modo": "local_sqlserver_preparacion",
                "mensaje": (
                    "Preparación local correcta. Puede ejecutar Fase I."
                    if ok
                    else "Preparación local con observaciones. Revise columnas de fecha."
                ),
                "fecha_sql": fecha_sql,
                "origen_servidor": origen_cfg.get("server", ""),
                "origen_database": source_db,
                "destino_servidor": destino_cfg.get("server", ""),
                "destino_database": dest_db,
                "usuarios_origen_total": origen_usuarios_total,
                "comentarios_origen_total": origen_comentarios_total,
                "comentarios_origen_fecha": comentarios_origen_fecha,
                "usuarios_destino_antes": destino_usuarios_total,
                "comentarios_destino_antes": destino_comentarios_total,
                "comentarios_destino_fecha": comentarios_destino_fecha,
                "columna_fecha_comentarios_origen": source_fecha,
                "columna_fecha_comentarios_destino": dest_fecha,
            }

    except Exception as exc:
        return {
            "success": False,
            "ok": False,
            "modo": "local_sqlserver_preparacion",
            "mensaje": str(exc),
            "error": str(exc),
        }


def _ejecutar_fase_i_local_sqlserver_v2(fecha_sql: str) -> dict[str, Any]:
    """
    Ejecuta Fase I LOCAL sin tocar MySQL remoto.

    Bloquea si ya hay comentarios en destino para la fecha.
    """
    origen_cfg = _sql_local_origen()
    destino_cfg = _sql_local_destino()

    try:
        import pyodbc

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


def ejecutar_accion_aster_v2(
    accion: str,
    fecha_proceso: str,
    conexion: str = "local",
) -> dict[str, Any]:
    accion = str(accion or "").strip()
    conexion = "remoto" if str(conexion).lower() == "remoto" else "local"
    fecha = _fecha_yyyymmdd(fecha_proceso)
    fecha_sql = _fecha_sql(fecha_proceso)

    comunes = {
        "fecha_proceso": fecha,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "data_root": get_data_root(),
        "accion": accion,
    }

    try:
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
