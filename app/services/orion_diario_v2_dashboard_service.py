from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import os
import re

try:
    import pyodbc
except Exception:
    pyodbc = None


ROOT = Path.cwd()


RED_BASE_PATHS = [
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_orion\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
]


MESES = {
    "01": "enero",
    "02": "febrero",
    "03": "marzo",
    "04": "abril",
    "05": "mayo",
    "06": "junio",
    "07": "julio",
    "08": "agosto",
    "09": "septiembre",
    "10": "octubre",
    "11": "noviembre",
    "12": "diciembre",
}


FASES_ORION = [
    {
        "codigo": "A",
        "nombre": "Crear carpetas",
        "grupo": "Preparación",
        "descripcion": "Crea estructura local y carpetas de proceso diario Orion.",
        "accion": "crear_carpetas",
    },
    {
        "codigo": "B",
        "nombre": "Verificar red",
        "grupo": "Preparación",
        "descripcion": "Verifica disponibilidad de rutas de red, unidad Z y espejo local.",
        "accion": "verificar_red",
    },
    {
        "codigo": "C",
        "nombre": "OCR y Totales",
        "grupo": "OCR",
        "descripcion": "Procesa OCR, extrae totales y valida archivos base.",
        "accion": "ocr_totales",
    },
    {
        "codigo": "D",
        "nombre": "Distribuir archivos",
        "grupo": "Distribución",
        "descripcion": "Distribuye archivos por carpetas de trabajo y tipo de insumo.",
        "accion": "distribuir_archivos",
    },
    {
        "codigo": "E1",
        "nombre": "Procesar Discador",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de discador para carga SQL.",
        "accion": "procesar_discador",
    },
    {
        "codigo": "E2",
        "nombre": "Procesar Causales",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de causales para carga SQL.",
        "accion": "procesar_causales",
    },
    {
        "codigo": "E3",
        "nombre": "Procesar Lotes",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de lotes para carga SQL.",
        "accion": "procesar_lotes",
    },
    {
        "codigo": "F1",
        "nombre": "Carga Causales",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta causales en base Orion.",
        "accion": "carga_causales",
    },
    {
        "codigo": "F2",
        "nombre": "Carga Lotes",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta lotes en base Orion.",
        "accion": "carga_lotes",
    },
    {
        "codigo": "F3",
        "nombre": "Carga Discador",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta discador en base Orion.",
        "accion": "carga_discador",
    },
    {
        "codigo": "G",
        "nombre": "Consolidado Gestión Orion",
        "grupo": "Consolidado",
        "descripcion": "Genera resumen final de Gestión Diaria Orion.",
        "accion": "consolidado_orion",
    },
]


def _leer_env_local() -> None:
    env_path = ROOT / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')

        if key not in os.environ:
            os.environ[key] = value


def _fecha_yyyymmdd(fecha_proceso: str) -> str:
    fecha = str(fecha_proceso or "").strip()

    if re.fullmatch(r"\d{8}", fecha):
        return fecha

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        return fecha.replace("-", "")

    return datetime.now().strftime("%Y%m%d")


def _fecha_sql(fecha_proceso: str) -> str:
    fecha = _fecha_yyyymmdd(fecha_proceso)
    return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"


def _mes_por_fecha(fecha_proceso: str) -> str:
    fecha = _fecha_yyyymmdd(fecha_proceso)
    return MESES.get(fecha[4:6], "")


def _normalizar_mes(mes_gestion: str, fecha_proceso: str) -> str:
    mes = str(mes_gestion or "").strip().lower()

    if mes:
        return mes

    return _mes_por_fecha(fecha_proceso)


def _orion_config(conexion: str) -> dict[str, str]:
    _leer_env_local()

    conexion = str(conexion or "local").strip().lower()

    if conexion == "remoto":
        server = os.getenv("ORION_SQL_REMOTE_SERVER", os.getenv("ORION_REMOTE_SERVER", "VC-EIDER"))
        database = os.getenv("ORION_SQL_REMOTE_DATABASE", "Orion")
        username = os.getenv("ORION_SQL_REMOTE_USERNAME", "Admin1")
        password = os.getenv("ORION_SQL_REMOTE_PASSWORD", "")
    else:
        server = os.getenv("ORION_CARGAS_SQL_SERVER", os.getenv("ORION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV"))
        database = os.getenv("ORION_CARGAS_SQL_DATABASE", os.getenv("ORION_SQL_LOCAL_DATABASE", "Orion"))
        username = os.getenv("ORION_CARGAS_SQL_USER", os.getenv("ORION_SQL_LOCAL_USERNAME", "Admin1"))
        password = os.getenv("ORION_CARGAS_SQL_PASSWORD", os.getenv("ORION_SQL_LOCAL_PASSWORD", "1234"))

    return {
        "conexion": conexion,
        "driver": os.getenv("ORION_CARGAS_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
        "server": server,
        "database": database,
        "username": username,
        "password": password,
        "encrypt": os.getenv("ORION_CARGAS_SQL_ENCRYPT", "yes"),
        "trust": os.getenv("ORION_CARGAS_SQL_TRUST_SERVER_CERTIFICATE", "yes"),
    }


def _conn_str(cfg: dict[str, str]) -> str:
    return (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"Encrypt={cfg['encrypt']};"
        f"TrustServerCertificate={cfg['trust']};"
    )


def _rutas_base(rutas_base: list[str] | None = None) -> list[str]:
    if rutas_base:
        limpias = [str(r).strip() for r in rutas_base if str(r).strip()]
        if limpias:
            return limpias

    return list(RED_BASE_PATHS)


def _rutas_red(mes_gestion: str, rutas_base: list[str] | None = None) -> list[dict[str, Any]]:
    bases = _rutas_base(rutas_base)
    nombres = ["Ruta red UNC", "Unidad Z", "Espejo local"]

    salida = []

    for idx, base in enumerate(bases):
        ruta_mes = str(Path(base) / mes_gestion) if not base.startswith("\\\\") else base.rstrip("\\") + "\\" + mes_gestion

        salida.append(
            {
                "id": idx + 1,
                "nombre": nombres[idx] if idx < len(nombres) else f"Ruta {idx + 1}",
                "base": base,
                "ruta_mes": ruta_mes,
                "existe_base": Path(base).exists() if not base.startswith("\\\\") else False,
                "existe_mes": Path(ruta_mes).exists() if not ruta_mes.startswith("\\\\") else False,
            }
        )

    return salida


def _rutas_locales(fecha_proceso: str) -> dict[str, str]:
    fecha = _fecha_yyyymmdd(fecha_proceso)

    base = ROOT / "data" / fecha
    orion = base / "Orion"

    return {
        "data_fecha": str(base),
        "orion": str(orion),
        "consolidados": str(orion / "Consolidados"),
        "logs": str(base / "logs"),
    }


def _servidores_locales(cfg: dict[str, str], rutas_red: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tipo": "SQL Server local Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "usuario": cfg["username"],
            "uso": "Carga Causales / Lotes / Discador",
            "visible_solo_local": True,
        },
        {
            "tipo": "Ruta red principal",
            "servidor": r"\\10.24.90.118",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[0]["base"] if len(rutas_red) > 0 else "",
            "visible_solo_local": True,
        },
        {
            "tipo": "Unidad mapeada",
            "servidor": "Z:",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[1]["base"] if len(rutas_red) > 1 else "",
            "visible_solo_local": True,
        },
        {
            "tipo": "Espejo local desarrollo",
            "servidor": "D:",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[2]["base"] if len(rutas_red) > 2 else "",
            "visible_solo_local": True,
        },
    ]


def _safe_count(cfg: dict[str, str], tabla: str, fecha_sql: str) -> dict[str, Any]:
    if pyodbc is None:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": "pyodbc no disponible",
            "columna_fecha": "",
        }

    candidatos_fecha = [
        "fecha",
        "Fecha",
        "Fecha_Hora",
        "fecha_proceso",
        "FechaProceso",
        "created_at",
    ]

    try:
        with pyodbc.connect(_conn_str(cfg), timeout=8) as conn:
            cur = conn.cursor()

            exists = cur.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA='dbo'
                  AND LOWER(TABLE_NAME)=LOWER(?)
                """,
                tabla,
            ).fetchval()

            if not exists:
                return {
                    "tabla": tabla,
                    "total": 0,
                    "estado": "no_existe",
                    "detalle": "Tabla no encontrada",
                    "columna_fecha": "",
                }

            columnas = [
                r.COLUMN_NAME
                for r in cur.execute(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA='dbo'
                      AND LOWER(TABLE_NAME)=LOWER(?)
                    ORDER BY ORDINAL_POSITION
                    """,
                    tabla,
                ).fetchall()
            ]

            columna_fecha = ""

            for candidato in candidatos_fecha:
                for col in columnas:
                    if col.lower() == candidato.lower():
                        columna_fecha = col
                        break

                if columna_fecha:
                    break

            if columna_fecha:
                total = cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM dbo.[{tabla}]
                    WHERE TRY_CAST([{columna_fecha}] AS DATE)=?
                    """,
                    fecha_sql,
                ).fetchval()

                return {
                    "tabla": tabla,
                    "total": int(total or 0),
                    "estado": "ok",
                    "detalle": f"Filtrado por {columna_fecha}",
                    "columna_fecha": columna_fecha,
                }

            total = cur.execute(f"SELECT COUNT(*) FROM dbo.[{tabla}]").fetchval()

            return {
                "tabla": tabla,
                "total": int(total or 0),
                "estado": "ok",
                "detalle": "Sin columna fecha; total general",
                "columna_fecha": "",
            }

    except Exception as exc:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": str(exc),
            "columna_fecha": "",
        }


def construir_contexto_orion_v2(
    fecha_proceso: str,
    mes_gestion: str,
    conexion: str,
    rutas_base: list[str] | None = None,
) -> dict[str, Any]:
    fecha_proceso = _fecha_yyyymmdd(fecha_proceso)
    mes_gestion = _normalizar_mes(mes_gestion, fecha_proceso)

    cfg = _orion_config(conexion)
    rutas_red = _rutas_red(mes_gestion, rutas_base)
    rutas_locales = _rutas_locales(fecha_proceso)

    return {
        "modulo": "orion",
        "titulo": "Gestión Diaria Orion",
        "fecha_proceso": fecha_proceso,
        "fecha_sql": _fecha_sql(fecha_proceso),
        "mes_gestion": mes_gestion,
        "conexion": cfg["conexion"],
        "rutas_red": rutas_red,
        "rutas_locales": rutas_locales,
        "servidores_locales": _servidores_locales(cfg, rutas_red) if cfg["conexion"] == "local" else [],
        "fases": [
            {
                **fase,
                "estado": "pendiente",
                "badge": "Pendiente",
            }
            for fase in FASES_ORION
        ],
    }


def construir_estadisticas_orion_v2(
    fecha_proceso: str,
    mes_gestion: str,
    conexion: str,
    rutas_base: list[str] | None = None,
) -> dict[str, Any]:
    contexto = construir_contexto_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
        rutas_base=rutas_base,
    )

    cfg = _orion_config(conexion)
    fecha_sql = contexto["fecha_sql"]

    conteos = {
        "causales": _safe_count(cfg, "causales", fecha_sql),
        "lote": _safe_count(cfg, "lote", fecha_sql),
        "discador": _safe_count(cfg, "discador", fecha_sql),
    }

    conexiones = [
        {
            "proceso": "Carga Causales",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.causales",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["causales"]["estado"],
            "total": conteos["causales"]["total"],
            "detalle": conteos["causales"]["detalle"],
        },
        {
            "proceso": "Carga Lotes",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.lote",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["lote"]["estado"],
            "total": conteos["lote"]["total"],
            "detalle": conteos["lote"]["detalle"],
        },
        {
            "proceso": "Carga Discador",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.discador",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["discador"]["estado"],
            "total": conteos["discador"]["total"],
            "detalle": conteos["discador"]["detalle"],
        },
    ]

    total_cargado = sum(int(item.get("total") or 0) for item in conteos.values())

    contexto.update(
        {
            "metricas": [
                {
                    "titulo": "Causales",
                    "valor": conteos["causales"]["total"],
                    "detalle": conteos["causales"]["detalle"],
                },
                {
                    "titulo": "Lotes",
                    "valor": conteos["lote"]["total"],
                    "detalle": conteos["lote"]["detalle"],
                },
                {
                    "titulo": "Discador",
                    "valor": conteos["discador"]["total"],
                    "detalle": conteos["discador"]["detalle"],
                },
                {
                    "titulo": "Total Orion",
                    "valor": total_cargado,
                    "detalle": "Suma de tablas principales Orion",
                },
            ],
            "conexiones": conexiones,
            "estadisticas_ejecutadas": True,
        }
    )

    return contexto
