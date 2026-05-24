"""
Rutas centralizadas para Gestión Diaria ORION / ASTER.

Estructura objetivo:

data\\YYYYMMDD
├── Orion
│   ├── Reporte_Imagen
│   ├── Causales
│   ├── Discador
│   ├── Lotes
│   ├── Consolidados
│   ├── Salidas
│   └── Logs
└── Aster
    └── aster_YYYYMMDD
        ├── Archivo_Original
        ├── Normalizado
        ├── Entidades
        ├── Gestion
        ├── Reportes
        └── Logs
"""

from __future__ import annotations

import os
import re
from datetime import datetime


ORION_SUBCARPETAS = [
    "Reporte_Imagen",
    "Causales",
    "Discador",
    "Lotes",
    "Consolidados",
    "Salidas",
    "Logs",
]

ASTER_SUBCARPETAS = [
    "Archivo_Original",
    "Normalizado",
    "Entidades",
    "Gestion",
    "Reportes",
    "Logs",
]


def normalizar_fecha_yyyymmdd(fecha: str) -> str:
    """
    Convierte una fecha a formato YYYYMMDD.

    Acepta:
    - YYYYMMDD
    - YYYYMM_DD
    - YYYY-MM-DD
    - YYYY/MM/DD

    Ejemplo:
    20260506, 202605_06, 2026-05-06 -> 20260506
    """
    texto = str(fecha or "").strip()

    if not texto:
        raise ValueError("Fecha vacía.")

    if re.fullmatch(r"\d{6}_\d{2}", texto):
        yyyymmdd = texto.replace("_", "")
    else:
        yyyymmdd = re.sub(r"\D", "", texto)

    if not re.fullmatch(r"\d{8}", yyyymmdd):
        raise ValueError(
            f"Fecha inválida: {fecha}. Use YYYYMMDD, YYYYMM_DD o YYYY-MM-DD."
        )

    datetime.strptime(yyyymmdd, "%Y%m%d")

    return yyyymmdd


def normalizar_fecha_orion_legacy(fecha: str) -> str:
    """
    Convierte una fecha al formato histórico ORION YYYYMM_DD.

    Se mantiene porque algunas funciones de red ORION calculan año, mes y día
    desde este formato.
    """
    yyyymmdd = normalizar_fecha_yyyymmdd(fecha)

    return f"{yyyymmdd[:6]}_{yyyymmdd[6:]}"


def ruta_dia(data_dir: str, fecha: str) -> str:
    """
    Carpeta diaria raíz.

    Ejemplo:
    data\\20260506
    """
    yyyymmdd = normalizar_fecha_yyyymmdd(fecha)

    return os.path.join(data_dir, yyyymmdd)


def ruta_orion(data_dir: str, fecha: str) -> str:
    """
    Carpeta raíz ORION del día.

    Ejemplo:
    data\\20260506\\Orion
    """
    return os.path.join(ruta_dia(data_dir, fecha), "Orion")


def ruta_orion_subcarpeta(data_dir: str, fecha: str, subcarpeta: str) -> str:
    """
    Subcarpeta ORION del día.
    """
    return os.path.join(ruta_orion(data_dir, fecha), subcarpeta)


def ruta_aster_base(data_dir: str, fecha: str) -> str:
    """
    Carpeta raíz ASTER del día.

    Ejemplo:
    data\\20260506\\Aster\\aster_20260506
    """
    yyyymmdd = normalizar_fecha_yyyymmdd(fecha)

    return os.path.join(
        ruta_dia(data_dir, yyyymmdd),
        "Aster",
        f"aster_{yyyymmdd}",
    )


def ruta_aster_subcarpeta(data_dir: str, fecha: str, subcarpeta: str) -> str:
    """
    Subcarpeta ASTER del día.
    """
    return os.path.join(ruta_aster_base(data_dir, fecha), subcarpeta)


def crear_estructura_orion(data_dir: str, fecha: str) -> dict[str, str]:
    """
    Crea estructura ORION diaria.
    """
    rutas = {
        "dia": ruta_dia(data_dir, fecha),
        "Orion": ruta_orion(data_dir, fecha),
    }

    for subcarpeta in ORION_SUBCARPETAS:
        rutas[subcarpeta] = ruta_orion_subcarpeta(data_dir, fecha, subcarpeta)

    for ruta in rutas.values():
        os.makedirs(ruta, exist_ok=True)

    return rutas


def crear_estructura_aster(data_dir: str, fecha: str) -> dict[str, str]:
    """
    Crea estructura ASTER diaria.
    """
    rutas = {
        "dia": ruta_dia(data_dir, fecha),
        "Aster": ruta_aster_base(data_dir, fecha),
    }

    for subcarpeta in ASTER_SUBCARPETAS:
        rutas[subcarpeta] = ruta_aster_subcarpeta(data_dir, fecha, subcarpeta)

    for ruta in rutas.values():
        os.makedirs(ruta, exist_ok=True)

    return rutas