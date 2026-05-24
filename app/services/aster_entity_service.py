"""
Servicio de entidades ASTER.

Responsabilidad:
- Leer el Excel ASTER normalizado.
- Validar que exista la columna Entidad.
- Obtener entidades únicas.
- Contar registros por entidad.
- Devolver resultado estructurado al controlador.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


def analizar_entidades_excel_aster(
    ruta_archivo: str,
) -> dict[str, Any]:
    """
    Analiza entidades únicas desde la columna Entidad del Excel ASTER normalizado.
    """
    ruta_archivo = str(ruta_archivo or "").strip()

    if not ruta_archivo:
        return {
            "success": False,
            "status": "sin_archivo",
            "error": "No hay archivo ASTER normalizado disponible.",
        }

    if not os.path.isfile(ruta_archivo):
        return {
            "success": False,
            "status": "archivo_no_existe",
            "error": "El archivo ASTER no existe en la ruta indicada.",
            "ruta_archivo": ruta_archivo,
        }

    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as exc:
        return {
            "success": False,
            "status": "error_lectura",
            "error": f"Error leyendo archivo ASTER: {exc}",
            "ruta_archivo": ruta_archivo,
        }

    columnas = [str(col) for col in df.columns.tolist()]

    if "Entidad" not in columnas:
        return {
            "success": False,
            "status": "sin_columna_entidad",
            "error": "No se encontró la columna Entidad en el Excel ASTER.",
            "ruta_archivo": ruta_archivo,
            "columnas": columnas,
        }

    serie_entidad = df["Entidad"].fillna("").astype(str).str.strip()
    serie_valida = serie_entidad[serie_entidad != ""]

    conteo_series = serie_valida.value_counts()

    conteo_entidades = [
        (str(entidad), int(cantidad))
        for entidad, cantidad in conteo_series.items()
    ]

    entidades = [
        entidad
        for entidad, _ in conteo_entidades
    ]

    return {
        "success": True,
        "ruta_archivo": ruta_archivo,
        "total_registros": len(df),
        "total_registros_con_entidad": int(len(serie_valida)),
        "total_registros_sin_entidad": int(len(df) - len(serie_valida)),
        "total_entidades": len(conteo_entidades),
        "entidades": entidades,
        "conteo_entidades": conteo_entidades,
        "columnas": columnas,
    }

