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



def _normalizar_columnas_gestion(df: Any, origen: str) -> Any:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    if origen.upper() == "ORION" and "NroCliente_Contrato" in df.columns:
        df = df.rename(columns={"NroCliente_Contrato": "Cliente Nro."})

    if "Cliente Nro." not in df.columns:
        raise ValueError(
            f"El archivo {origen} no tiene la columna requerida Cliente Nro. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    df["Cliente Nro."] = df["Cliente Nro."].astype(str).str.strip()

    return df


def _comparar_encabezados_gestion(cols_aster: list[str], cols_orion: list[str]) -> dict[str, Any]:
    set_aster = set(cols_aster)
    set_orion = set(cols_orion)

    faltan_en_orion = [col for col in cols_aster if col not in set_orion]
    sobran_en_orion = [col for col in cols_orion if col not in set_aster]
    mismo_orden = cols_aster == cols_orion
    mismo_set = not faltan_en_orion and not sobran_en_orion

    return {
        "ok": mismo_set,
        "mismo_orden": mismo_orden,
        "total_columnas_aster": len(cols_aster),
        "total_columnas_orion": len(cols_orion),
        "columnas_aster": cols_aster,
        "columnas_orion": cols_orion,
        "faltan_en_orion": faltan_en_orion,
        "sobran_en_orion": sobran_en_orion,
    }


def unir_archivos_gestion(data_dir: str | Path, fecha_raw: str) -> dict[str, Any]:
    """
    Fase B - Unión de archivos ASTER + ORION.

    Genera:
    - 01_union/YYYYMMDD_Gestion_union.xlsx
    - Reportes/YYYYMMDD_reporte_union.xlsx
    """
    try:
        import pandas as pd
    except Exception as exc:
        return {
            "ok": False,
            "error": f"No se pudo importar pandas: {exc}",
        }

    rutas = resolver_rutas(data_dir, fecha_raw)
    fecha = rutas["fecha"]

    ruta_aster = Path(rutas["aster"])
    ruta_orion = Path(rutas["orion"])

    errores = []

    if not ruta_aster.exists():
        errores.append(f"No existe archivo ASTER: {ruta_aster}")

    if not ruta_orion.exists():
        errores.append(f"No existe archivo ORION: {ruta_orion}")

    if errores:
        return {
            "ok": False,
            "fecha": fecha,
            "error": " | ".join(errores),
            "ruta_aster": str(ruta_aster),
            "ruta_orion": str(ruta_orion),
        }

    try:
        df_aster_raw = pd.read_excel(ruta_aster)
        df_orion_raw = pd.read_excel(ruta_orion)

        df_aster = _normalizar_columnas_gestion(df_aster_raw, "ASTER")
        df_orion = _normalizar_columnas_gestion(df_orion_raw, "ORION")

        encabezados = _comparar_encabezados_gestion(
            list(df_aster.columns),
            list(df_orion.columns),
        )

        if not encabezados["ok"]:
            return {
                "ok": False,
                "fecha": fecha,
                "error": "Los encabezados de ASTER y ORION no son compatibles.",
                "encabezados": encabezados,
                "ruta_aster": str(ruta_aster),
                "ruta_orion": str(ruta_orion),
                "total_aster": len(df_aster),
                "total_orion": len(df_orion),
            }

        if not encabezados["mismo_orden"]:
            df_orion = df_orion[list(df_aster.columns)]

        total_aster = len(df_aster)
        total_orion = len(df_orion)

        df_union = pd.concat([df_aster, df_orion], ignore_index=True)
        total_union = len(df_union)

        carpeta_union = Path(rutas["subcarpetas"]["01_union"])
        carpeta_reportes = Path(rutas["subcarpetas"]["Reportes"])
        carpeta_union.mkdir(parents=True, exist_ok=True)
        carpeta_reportes.mkdir(parents=True, exist_ok=True)

        ruta_union = carpeta_union / f"{fecha}_Gestion_union.xlsx"
        ruta_reporte = carpeta_reportes / f"{fecha}_reporte_union.xlsx"

        df_union.to_excel(ruta_union, index=False)

        resumen = pd.DataFrame(
            [
                {"concepto": "Total ASTER", "valor": total_aster},
                {"concepto": "Total ORION", "valor": total_orion},
                {"concepto": "Total después de unión", "valor": total_union},
                {"concepto": "Columnas ASTER", "valor": encabezados["total_columnas_aster"]},
                {"concepto": "Columnas ORION", "valor": encabezados["total_columnas_orion"]},
                {"concepto": "Encabezados compatibles", "valor": "SI"},
                {"concepto": "Mismo orden de columnas", "valor": "SI" if encabezados["mismo_orden"] else "NO - ORION fue reordenado"},
                {"concepto": "Archivo unión", "valor": str(ruta_union)},
            ]
        )

        columnas = pd.DataFrame(
            {
                "orden": list(range(1, len(df_aster.columns) + 1)),
                "columna_final": list(df_aster.columns),
            }
        )

        with pd.ExcelWriter(ruta_reporte) as writer:
            resumen.to_excel(writer, sheet_name="Resumen", index=False)
            columnas.to_excel(writer, sheet_name="Columnas", index=False)

        return {
            "ok": True,
            "fecha": fecha,
            "ruta_aster": str(ruta_aster),
            "ruta_orion": str(ruta_orion),
            "ruta_union": str(ruta_union),
            "ruta_reporte": str(ruta_reporte),
            "archivo_union": ruta_union.name,
            "archivo_reporte": ruta_reporte.name,
            "total_aster": total_aster,
            "total_orion": total_orion,
            "total_union": total_union,
            "encabezados": encabezados,
            "columnas": list(df_aster.columns),
        }
    except Exception as exc:
        return {
            "ok": False,
            "fecha": fecha,
            "error": str(exc),
            "ruta_aster": str(ruta_aster),
            "ruta_orion": str(ruta_orion),
        }
