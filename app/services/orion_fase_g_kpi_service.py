from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _normalizar_fecha_sql(fecha_raw: str) -> str:
    raw = str(fecha_raw or "").strip().replace("/", "-")

    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw

    return raw


def _fecha_anterior_no_domingo(fecha_sql: str) -> str:
    base = datetime.strptime(_normalizar_fecha_sql(fecha_sql), "%Y-%m-%d").date()
    ref = base - timedelta(days=1)

    while ref.weekday() == 6:
        ref = ref - timedelta(days=1)

    return ref.strftime("%Y-%m-%d")


def _cfg_get(cfg: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in cfg and cfg.get(key) not in (None, ""):
            return str(cfg.get(key)).strip()

    return default


def _seleccionar_driver() -> str:
    try:
        import pyodbc

        drivers = list(pyodbc.drivers())

        preferidos = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server",
        ]

        for item in preferidos:
            if item in drivers:
                return item

        if drivers:
            for item in drivers:
                if "SQL Server" in item:
                    return item

    except Exception:
        pass

    return "ODBC Driver 18 for SQL Server"


def _conn_str_kpi(cfg: dict[str, Any], database_default: str = "Orion") -> str:
    direct = _cfg_get(cfg, "conn_str", "connection_string", "sqlalchemy_url", default="")

    if direct and "DRIVER=" in direct.upper():
        return direct

    driver = _cfg_get(
        cfg,
        "driver",
        "DRIVER",
        "odbc_driver",
        "ODBC_DRIVER",
        default=_seleccionar_driver(),
    )

    server = _cfg_get(
        cfg,
        "server",
        "servidor",
        "SERVER",
        "host",
        "hostname",
        default="localhost\\SQL2025DEV",
    )

    database = _cfg_get(
        cfg,
        "database",
        "bd",
        "db",
        "DATABASE",
        default=database_default,
    )

    user = _cfg_get(
        cfg,
        "user",
        "usuario",
        "username",
        "uid",
        "UID",
        default="",
    )

    password = _cfg_get(
        cfg,
        "password",
        "clave",
        "pwd",
        "PWD",
        default="",
    )

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        "TrustServerCertificate=yes",
        "Encrypt=no",
        "Connection Timeout=10",
    ]

    if user:
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")
    else:
        parts.append("Trusted_Connection=yes")

    return ";".join(parts) + ";"


def _qident(value: str) -> str:
    return str(value).replace("]", "]]")


def _count_fecha(cur, database: str, tabla: str, columna: str, fecha_sql: str) -> int:
    database_q = _qident(database)
    tabla_q = _qident(tabla)
    columna_q = _qident(columna)

    sql = f"""
    SELECT COUNT(1)
    FROM [{database_q}].[dbo].[{tabla_q}]
    WHERE CAST([{columna_q}] AS DATE) = ?
    """

    row = cur.execute(sql, fecha_sql).fetchone()

    return int(row[0] or 0) if row else 0


def construir_kpi_pies_fase_g(cfg: dict[str, Any], fecha_proceso: str) -> dict[str, Any]:
    """
    KPI visual Fase G.

    Devuelve conteos ORION para:
    - fecha anterior hábil simple: fecha proceso - 1 día, evitando domingo.
    - fecha actual: fecha proceso.

    Tablas:
    - Orion.dbo.Causales  / FechayHora
    - Orion.dbo.Lote      / Fecha
    - Orion.dbo.Discador  / FechayHora
    """
    fecha_actual = _normalizar_fecha_sql(fecha_proceso)
    fecha_anterior = _fecha_anterior_no_domingo(fecha_actual)

    database = _cfg_get(
        cfg,
        "database",
        "bd",
        "db",
        "DATABASE",
        default="Orion",
    )

    tablas = [
        {
            "key": "causales",
            "label": "Causales",
            "tabla": "Causales",
            "columna": "FechayHora",
        },
        {
            "key": "lote",
            "label": "Lotes",
            "tabla": "Lote",
            "columna": "Fecha",
        },
        {
            "key": "discador",
            "label": "Discador",
            "tabla": "Discador",
            "columna": "FechayHora",
        },
    ]

    data = {
        "ok": True,
        "database": database,
        "fecha_actual": fecha_actual,
        "fecha_anterior": fecha_anterior,
        "anterior": [],
        "actual": [],
        "total_anterior": 0,
        "total_actual": 0,
    }

    try:
        import pyodbc

        conn_str = _conn_str_kpi(cfg, database_default=database)

        with pyodbc.connect(conn_str, timeout=10) as conn:
            cur = conn.cursor()

            for item in tablas:
                anterior = _count_fecha(
                    cur,
                    database,
                    item["tabla"],
                    item["columna"],
                    fecha_anterior,
                )

                actual = _count_fecha(
                    cur,
                    database,
                    item["tabla"],
                    item["columna"],
                    fecha_actual,
                )

                data["anterior"].append(
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "tabla": item["tabla"],
                        "columna": item["columna"],
                        "valor": anterior,
                    }
                )

                data["actual"].append(
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "tabla": item["tabla"],
                        "columna": item["columna"],
                        "valor": actual,
                    }
                )

        data["total_anterior"] = sum(int(x["valor"] or 0) for x in data["anterior"])
        data["total_actual"] = sum(int(x["valor"] or 0) for x in data["actual"])

        return data

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "database": database,
            "fecha_actual": fecha_actual,
            "fecha_anterior": fecha_anterior,
            "anterior": [],
            "actual": [],
            "total_anterior": 0,
            "total_actual": 0,
        }
