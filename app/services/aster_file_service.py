"""
Servicio de archivos ASTER.

Responsabilidad:
- Normalizar fecha de proceso ASTER a YYYYMMDD.
- Buscar estrictamente AfterYYYYMMDD.xlsx.
- Copiar archivo ASTER a Archivo_Original.
- Resolver carpetas base ASTER.
- Buscar archivo normalizado en Normalizado.
"""

from __future__ import annotations

import os
import re
import shutil
from typing import Any

from app.services.daily_paths import (
    crear_estructura_aster,
    ruta_aster_base,
    ruta_aster_subcarpeta,
)


def normalizar_fecha_aster(fecha_raw: str) -> str:
    """
    Convierte una fecha recibida en distintos formatos a YYYYMMDD.

    Acepta:
    - 20260429
    - 2026-04-29
    - 202604_29
    """
    fecha_limpia = re.sub(r"[^0-9]", "", fecha_raw or "")

    if len(fecha_limpia) < 8:
        raise ValueError(
            "La fecha del proceso debe tener al menos 8 dígitos. Ejemplo: 20260429."
        )

    return fecha_limpia[:8]


def obtener_carpeta_proceso_aster(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> str:
    """
    Devuelve carpeta base ASTER:

    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD
    """
    carpeta = ruta_aster_base(data_dir, fecha_yyyymmdd)
    os.makedirs(carpeta, exist_ok=True)

    return carpeta


def buscar_archivo_aster_en_ruta(
    ruta_base: str,
    fecha_yyyymmdd: str,
) -> str | None:
    """
    Busca estrictamente el archivo AfterYYYYMMDD.xlsx.

    Ejemplo válido:
    After20260521.xlsx

    No acepta:
    - After20240521.xlsx
    - archivos que solo coinciden por día y mes
    """
    if not ruta_base or not os.path.isdir(ruta_base):
        return None

    nombre_esperado = f"After{fecha_yyyymmdd}.xlsx"
    nombre_esperado_lower = nombre_esperado.lower()

    for carpeta_actual, _, archivos in os.walk(ruta_base):
        for archivo in archivos:
            if archivo.lower() == nombre_esperado_lower:
                return os.path.join(carpeta_actual, archivo)

    return None


def copiar_archivo_aster(
    data_dir: str,
    fecha_raw: str,
    ruta_base_usuario: str,
    rutas_default: list[str],
) -> dict[str, Any]:
    """
    Busca y copia AfterYYYYMMDD.xlsx a:

    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Archivo_Original
    """
    fecha_yyyymmdd = normalizar_fecha_aster(fecha_raw)

    rutas_busqueda: list[str] = []

    if ruta_base_usuario:
        rutas_busqueda.append(ruta_base_usuario)

    rutas_busqueda.extend(rutas_default)

    ruta_origen: str | None = None

    for ruta_base in rutas_busqueda:
        ruta_encontrada = buscar_archivo_aster_en_ruta(
            ruta_base,
            fecha_yyyymmdd,
        )

        if ruta_encontrada:
            ruta_origen = ruta_encontrada
            break

    if not ruta_origen:
        return {
            "success": False,
            "status": "no_encontrado",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "rutas_busqueda": rutas_busqueda,
        }

    rutas_aster = crear_estructura_aster(data_dir, fecha_yyyymmdd)
    carpeta_destino = rutas_aster["Archivo_Original"]

    nombre_archivo = os.path.basename(ruta_origen)
    ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

    shutil.copy2(ruta_origen, ruta_destino)

    return {
        "success": True,
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "ruta_origen": ruta_origen,
        "ruta_destino": ruta_destino,
        "nombre_archivo": nombre_archivo,
        "rutas_busqueda": rutas_busqueda,
    }


def buscar_archivo_normalizado_aster_en_disco(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> str:
    """
    Busca archivo normalizado ASTER en:

    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Normalizado
    """
    carpeta_normalizado = ruta_aster_subcarpeta(
        data_dir,
        fecha_yyyymmdd,
        "Normalizado",
    )

    if not os.path.isdir(carpeta_normalizado):
        return ""

    candidatos: list[dict[str, Any]] = []

    for archivo in os.listdir(carpeta_normalizado):
        nombre = archivo.lower()

        if not nombre.endswith(".xlsx"):
            continue

        if "normalizado" not in nombre:
            continue

        ruta = os.path.join(carpeta_normalizado, archivo)

        candidatos.append(
            {
                "ruta": ruta,
                "modificado": os.path.getmtime(ruta),
            }
        )

    if not candidatos:
        return ""

    candidatos.sort(
        key=lambda item: item["modificado"],
        reverse=True,
    )

    return str(candidatos[0]["ruta"])

