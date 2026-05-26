from __future__ import annotations

from pathlib import Path
from datetime import datetime
import os
import re
from typing import Any

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover
    load_workbook = None


RESUMEN_SQL = """
SELECT
    (SELECT COUNT(*) FROM Aster_Api.dbo.aster_dia_nc WHERE CAST(Fecha_Hora AS DATE) = ?) AS Total_Aster_dia_nc,
    (SELECT COUNT(*) FROM Aster_Api.dbo.comentarios WHERE CAST(fecha AS DATE) = ?) AS Total_Aster_comentarios,
    (SELECT COUNT(*) FROM Aster_Api.dbo.usuarios) AS Total_Aster_Usuarios,
    (SELECT COUNT(*) FROM Orion.dbo.Causales WHERE CAST(FechayHora AS DATE) = ?) AS Total_Orion_Causales,
    (SELECT COUNT(*) FROM Orion.dbo.Lote WHERE CAST(Fecha AS DATE) = ?) AS Total_Orion_Lote,
    (SELECT COUNT(*) FROM Orion.dbo.Discador WHERE CAST(FechayHora AS DATE) = ?) AS Total_Orion_Discador;
"""


FASES = [
    ("A", "Preparar archivos"),
    ("B", "Unir archivos"),
    ("C", "Verificar calidad"),
    ("D", "Ajuste No contestan"),
    ("E", "Limpiar nota"),
    ("F", "Compromiso"),
    ("G", "Generar archivo final"),
    ("H", "Archivos generados"),
    ("I", "Cargar información"),
]


def normalizar_fecha_yyyymmdd(fecha_raw: str) -> str:
    limpia = re.sub(r"\D", "", str(fecha_raw or ""))

    if len(limpia) >= 8:
        return limpia[:8]

    raise ValueError(f"Fecha inválida: {fecha_raw}")


def fecha_iso(fecha_raw: str) -> str:
    fecha = normalizar_fecha_yyyymmdd(fecha_raw)
    return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"


def fecha_mes(fecha_raw: str) -> str:
    return normalizar_fecha_yyyymmdd(fecha_raw)[:6]


def resolver_rutas(data_dir: str | Path, fecha_raw: str) -> dict[str, Any]:
    fecha = normalizar_fecha_yyyymmdd(fecha_raw)
    base = Path(data_dir) / fecha

    ruta_orion = base / "Orion" / "Salidas" / f"{fecha}_Gestion_orion.xlsx"
    ruta_aster = base / "Aster" / f"aster_{fecha}" / "Gestion" / f"{fecha}_Gestion_aster.xlsx"

    carpeta_consolidado = base / "Consolidado" / "Gestion"

    subcarpetas = {
        "base": carpeta_consolidado,
        "00_resumen_sql": carpeta_consolidado / "00_resumen_sql",
        "01_union": carpeta_consolidado / "01_union",
        "02_verificaciones": carpeta_consolidado / "02_verificaciones",
        "03_ajustes": carpeta_consolidado / "03_ajustes",
        "04_compromiso": carpeta_consolidado / "04_compromiso",
        "05_final": carpeta_consolidado / "05_final",
        "06_carga": carpeta_consolidado / "06_carga",
        "Reportes": carpeta_consolidado / "Reportes",
        "Logs": carpeta_consolidado / "Logs",
    }

    return {
        "fecha": fecha,
        "fecha_iso": fecha_iso(fecha),
        "mes_gestion": fecha_mes(fecha),
        "base": base,
        "orion": ruta_orion,
        "aster": ruta_aster,
        "consolidado": carpeta_consolidado,
        "subcarpetas": subcarpetas,
    }


def crear_estructura_consolidado(data_dir: str | Path, fecha_raw: str) -> dict[str, Any]:
    rutas = resolver_rutas(data_dir, fecha_raw)

    creadas = []

    for nombre, ruta in rutas["subcarpetas"].items():
        ruta.mkdir(parents=True, exist_ok=True)
        creadas.append(
            {
                "carpeta": nombre,
                "ruta": str(ruta),
                "existe": ruta.exists(),
            }
        )

    return {
        "ok": True,
        "fecha": rutas["fecha"],
        "consolidado": str(rutas["consolidado"]),
        "carpetas": creadas,
    }


def contar_filas_excel(ruta: Path) -> int | None:
    if not ruta.exists() or ruta.suffix.lower() != ".xlsx":
        return None

    if load_workbook is None:
        return None

    try:
        wb = load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active
        total = max(0, int(ws.max_row or 0) - 1)
        wb.close()
        return total
    except Exception:
        return None


def info_archivo(ruta: Path) -> dict[str, Any]:
    existe = ruta.exists()

    info = {
        "nombre": ruta.name,
        "ruta": str(ruta),
        "existe": existe,
        "tipo": ruta.suffix.lower().replace(".", "") if ruta.suffix else "",
        "tamano_kb": "",
        "fecha_creacion": "",
        "fecha_modificacion": "",
        "filas": "",
    }

    if not existe:
        return info

    stat = ruta.stat()

    info["tamano_kb"] = round(stat.st_size / 1024, 2)
    info["fecha_creacion"] = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
    info["fecha_modificacion"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    filas = contar_filas_excel(ruta)

    if filas is not None:
        info["filas"] = filas

    return info


def preparar_proceso(data_dir: str | Path, fecha_raw: str) -> dict[str, Any]:
    rutas = resolver_rutas(data_dir, fecha_raw)
    estructura = crear_estructura_consolidado(data_dir, fecha_raw)

    archivos = [
        {
            "origen": "ORION",
            **info_archivo(rutas["orion"]),
        },
        {
            "origen": "ASTER",
            **info_archivo(rutas["aster"]),
        },
    ]

    ok_archivos = all(item["existe"] for item in archivos)

    return {
        "ok": ok_archivos,
        "fecha": rutas["fecha"],
        "fecha_iso": rutas["fecha_iso"],
        "mes_gestion": rutas["mes_gestion"],
        "conexion_requerida": "LOCAL/REMOTO",
        "carpeta_consolidado": str(rutas["consolidado"]),
        "archivos": archivos,
        "carpetas": estructura["carpetas"],
        "mensaje": (
            "Archivos base localizados correctamente."
            if ok_archivos
            else "Faltan archivos base ORION/ASTER. Revise rutas antes de continuar."
        ),
    }


def _connection_string(conexion: str) -> str:
    """
    Conexión SQL Server para resumen inicial.

    Variables opcionales:
    - GESTION_SQL_DRIVER
    - GESTION_SQL_LOCAL_SERVER
    - GESTION_SQL_REMOTE_SERVER
    - GESTION_SQL_USER
    - GESTION_SQL_PASSWORD

    Si no hay usuario/clave, usa Trusted_Connection=yes.
    """
    conn = str(conexion or "local").lower()
    driver = os.getenv("GESTION_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    local_server = os.getenv("GESTION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV")
    remote_server = os.getenv("GESTION_SQL_REMOTE_SERVER", "VC-EIDER")

    server = remote_server if conn == "remoto" else local_server

    user = os.getenv("GESTION_SQL_USER") or os.getenv("SQLSERVER_USER")
    password = os.getenv("GESTION_SQL_PASSWORD") or os.getenv("SQLSERVER_PASSWORD")

    if user and password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            "DATABASE=Aster_Api;"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        "DATABASE=Aster_Api;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def consultar_resumen_sql(fecha_raw: str, conexion: str) -> dict[str, Any]:
    try:
        import pyodbc
    except Exception as exc:
        return {
            "ok": False,
            "conexion": conexion,
            "fecha": fecha_iso(fecha_raw),
            "error": f"No se pudo importar pyodbc: {exc}",
            "datos": {},
        }

    fecha = fecha_iso(fecha_raw)
    params = [fecha, fecha, fecha, fecha, fecha]

    try:
        with pyodbc.connect(_connection_string(conexion), timeout=15) as conn:
            cursor = conn.cursor()
            row = cursor.execute(RESUMEN_SQL, params).fetchone()

            if row is None:
                datos = {}
            else:
                columns = [col[0] for col in cursor.description]
                datos = dict(zip(columns, row))

        return {
            "ok": True,
            "conexion": str(conexion or "local").lower(),
            "fecha": fecha,
            "datos": datos,
            "error": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "conexion": str(conexion or "local").lower(),
            "fecha": fecha,
            "datos": {},
            "error": str(exc),
        }
